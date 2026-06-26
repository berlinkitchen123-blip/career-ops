"""
Job Copilot AI Agent — Autonomous Job Application System
=========================================================
Runs daily. For each matching job:
  1. Fetches jobs from LinkedIn, Indeed, Glassdoor, Remotive
  2. Scores each against your profile using Claude AI
  3. Generates an ATS-optimized tailored CV
  4. Opens the apply page with Playwright
  5. Detects the form type and fills it automatically
  6. Submits the application (with confirmation gate)

Usage:
  python3 agent.py --run          # Full auto-apply run
  python3 agent.py --fetch-only   # Just fetch & score jobs
  python3 agent.py --dry-run      # Fill forms but don't submit
  python3 agent.py --job-url URL  # Apply to a specific URL
"""

import os, sys, json, time, argparse, re
from datetime import datetime
from pathlib import Path
import google.generativeai, requests

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config.json"
LOG_FILE    = Path(__file__).parent / "agent.log"
CV_DIR      = Path(__file__).parent / "generated_cvs"
CV_DIR.mkdir(exist_ok=True)

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

cfg = load_config()

GEMINI_KEY      = cfg.get("gemini_key",    os.getenv("GEMINI_KEY", ""))
RAPIDAPI_KEY    = cfg.get("rapidapi_key",  os.getenv("RAPIDAPI_KEY", "d10acd4e6cmsh86b69547ae79c9fp14c103jsn952c7717e1d0"))
MIN_SCORE       = cfg.get("min_score", 60)
MAX_APPLY       = cfg.get("max_apply_per_run", 5)
AUTO_SUBMIT     = cfg.get("auto_submit", False)  # Safety off by default
SEARCH_QUERIES  = cfg.get("search_queries", [
    "operations manager Berlin",
    "AI tools product manager Germany",
    "quality assurance engineer Berlin",
    "logistics operations manager Germany",
    "technical operations engineer hybrid",
])
LOCATIONS       = cfg.get("locations", ["Berlin, Germany", "Germany", "remote"])

# ── PROFILE ───────────────────────────────────────────────────────────────────
PROFILE = cfg.get("profile", {
    "name": "Harshkumar Patel",
    "email": "patelharsh513@gmail.com",
    "phone": "+4915560938054",
    "location": "Berlin, Germany",
    "linkedin": "https://linkedin.com/in/patelharsh513",
    "portfolio": "https://berlinkitchen123-blip.github.io",
    "summary": "Operations Manager and AI App Builder with 10+ years engineering background. Built 22+ live production tools including a real-time QC system (credited by Forbes 30 Under 30 CEO). Deep background in mechanical engineering, DFMEA, quality assurance. Open to hybrid roles in Berlin or Germany.",
    "skills": [
        "AI App Development", "React", "TypeScript", "Firebase", "Google Gemini AI",
        "Operations Management", "Quality Assurance", "HACCP", "DFMEA", "RCA/CAPA",
        "KPI Management", "Logistics Management", "Process Validation",
        "SolidWorks Expert", "Autodesk Inventor", "Additive Manufacturing",
        "DFM & DFA", "Project Management", "Technical Documentation"
    ],
    "years_experience": 10,
    "education": "Bachelor of Mechanical Engineering, Gujarat Technological University (2016)",
    "languages": ["English (Fluent)", "German (A2)", "Hindi (Native)", "Gujarati (Native)"],
    "work_permit": "Germany - currently on employment visa, targeting EU Blue Card",
})

# ── LOGGING ───────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── JOB FETCHING ──────────────────────────────────────────────────────────────
def fetch_jsearch(query, location):
    """Fetch from JSearch API — covers LinkedIn, Indeed, Glassdoor, ZipRecruiter, and 20+ more."""
    if not RAPIDAPI_KEY:
        log("No RapidAPI key configured", "WARN")
        return []
    url = "https://jsearch.p.rapidapi.com/search"
    params = {"query": f"{query} {location}", "page": "1", "num_pages": "2", "date_posted": "week"}
    headers = {"x-rapidapi-host": "jsearch.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        jobs = []
        for j in data:
            loc = "Remote" if j.get("job_is_remote") else ", ".join(filter(None, [j.get("job_city"), j.get("job_country")]))
            salary = ""
            if j.get("job_min_salary"):
                salary = f"${j['job_min_salary']:,}-${j.get('job_max_salary', j['job_min_salary']):,}/{j.get('job_salary_period','YEAR')}"
            jobs.append({
                "id": j["job_id"],
                "title": j.get("job_title", ""),
                "company": j.get("employer_name", ""),
                "location": loc,
                "salary": salary,
                "description": j.get("job_description", "")[:3000],
                "apply_url": j.get("job_apply_link") or j.get("job_google_link", ""),
                "source": _map_source(j.get("job_publisher", "")),
                "posted": j.get("job_posted_at_datetime_utc", ""),
                "score": None,
            })
        log(f"JSearch: {len(jobs)} jobs for '{query} {location}'")
        return jobs
    except Exception as e:
        log(f"JSearch error: {e}", "ERROR")
        return []

def fetch_remotive():
    """Fetch remote jobs from Remotive — free, no key needed."""
    try:
        r = requests.get("https://remotive.com/api/remote-jobs?limit=30", timeout=10)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs", []):
            jobs.append({
                "id": f"rm-{j['id']}",
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": "Remote",
                "salary": j.get("salary", ""),
                "description": re.sub(r"<[^>]+>", " ", j.get("description", ""))[:3000],
                "apply_url": j.get("url", ""),
                "source": "Remotive",
                "posted": j.get("publication_date", ""),
                "score": None,
            })
        log(f"Remotive: {len(jobs)} jobs")
        return jobs
    except Exception as e:
        log(f"Remotive error: {e}", "ERROR")
        return []

def _map_source(pub):
    p = pub.lower()
    if "linkedin" in p: return "LinkedIn"
    if "indeed"   in p: return "Indeed"
    if "glassdoor"in p: return "Glassdoor"
    if "zip"      in p: return "ZipRecruiter"
    return pub or "JSearch"

def fetch_all_jobs():
    """Fetch from all sources, deduplicate."""
    all_jobs = []
    seen = set()
    # JSearch across all queries/locations
    for query in SEARCH_QUERIES:
        for loc in LOCATIONS:
            for job in fetch_jsearch(query, loc):
                if job["id"] not in seen:
                    seen.add(job["id"])
                    all_jobs.append(job)
            time.sleep(0.5)
    # Remotive
    for job in fetch_remotive():
        if job["id"] not in seen:
            seen.add(job["id"])
            all_jobs.append(job)
    log(f"Total unique jobs fetched: {len(all_jobs)}")
    return all_jobs

# ── AI SCORING & CV GENERATION ────────────────────────────────────────────────
def get_gemini():
    if not GEMINI_KEY:
        raise ValueError("Gemini API key not configured. Run: python3 agent.py --setup")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    return genai.GenerativeModel("gemini-2.0-flash")

def score_job(job):
    """Score job 0-100 against profile using Gemini."""
    try:
        model = get_gemini()
        prompt = f"""Score this job for the candidate. Return ONLY valid JSON.

JOB: {job['title']} at {job['company']}
DESCRIPTION: {job['description'][:1500]}

CANDIDATE:
{json.dumps({k: PROFILE[k] for k in ['name','summary','skills','years_experience','education','languages']}, indent=1)}

Return exactly:
{{"score": <0-100>, "reason": "<one line>", "strengths": ["s1","s2"], "gaps": ["g1"]}}"""

        response = model.generate_content(prompt)
        raw = response.text
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
    except Exception as e:
        log(f"Score error for {job['title']}: {e}", "WARN")
    return {"score": 0, "reason": "scoring failed", "strengths": [], "gaps": []}

def generate_cv(job):
    """Generate ATS-optimized CV tailored to this specific job using Gemini."""
    try:
        model = get_gemini()
    except Exception as e:
        log(f"Gemini init error: {e}", "ERROR")
        return None
    prompt = f"""Generate an ATS-optimized CV tailored for this job. Return ONLY the CV as plain text.

JOB: {job['title']} at {job['company']}
JOB DESCRIPTION:
{job['description'][:2000]}

CANDIDATE PROFILE:
{json.dumps(PROFILE, indent=1)}

REQUIREMENTS:
- Rewrite summary to directly target this role (2-3 sentences)
- List skills ordered by relevance to this job
- Strengthen bullet points with keywords from job description
- Inject exact keywords from JD naturally throughout
- Keep format: Name, Contact, Summary, Skills, Experience, Education
- ATS-friendly: no tables, no graphics, plain text only
- Max 1 page

Start directly with the CV — no preamble."""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log(f"CV generation error: {e}", "ERROR")
        return None

def save_cv_file(cv_text, job):
    """Save CV as .txt file."""
    safe_company = re.sub(r'[^\w]', '_', job['company'])[:30]
    safe_title   = re.sub(r'[^\w]', '_', job['title'])[:30]
    filename = CV_DIR / f"CV_{safe_title}_{safe_company}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filename.write_text(cv_text)
    log(f"CV saved: {filename}")
    return str(filename)

# ── FORM DETECTION & AUTO-FILL ────────────────────────────────────────────────
def detect_form_type(page):
    """Detect which ATS/job board we're on."""
    url = page.url
    if "linkedin.com" in url:       return "linkedin"
    if "indeed.com"  in url:       return "indeed"
    if "greenhouse.io" in url:     return "greenhouse"
    if "lever.co" in url:          return "lever"
    if "workday.com" in url:       return "workday"
    if "ashbyhq.com" in url:       return "ashby"
    if "smartrecruiters.com" in url: return "smartrecruiters"
    return "generic"

async def fill_linkedin_easy_apply(page, job, cv_path):
    """Fill LinkedIn Easy Apply form."""
    from playwright.async_api import expect
    try:
        # Click Easy Apply button
        easy_btn = page.locator("button:has-text('Easy Apply'), .jobs-apply-button")
        if await easy_btn.count() > 0:
            await easy_btn.first.click()
            await page.wait_for_timeout(2000)

        # Fill each step
        for step in range(10):  # Max 10 steps
            # Phone number
            phone_field = page.locator("input[id*='phoneNumber'], input[name*='phone']")
            if await phone_field.count() > 0:
                await phone_field.first.fill(PROFILE["phone"])

            # Email
            email_field = page.locator("input[type='email']")
            if await email_field.count() > 0:
                val = await email_field.first.input_value()
                if not val:
                    await email_field.first.fill(PROFILE["email"])

            # City/location fields
            for sel in ["input[id*='city']", "input[id*='location']", "input[placeholder*='City']"]:
                field = page.locator(sel)
                if await field.count() > 0:
                    val = await field.first.input_value()
                    if not val:
                        await field.first.fill("Berlin")

            # Upload CV/Resume
            file_input = page.locator("input[type='file']")
            if await file_input.count() > 0 and cv_path:
                await file_input.first.set_input_files(cv_path)
                await page.wait_for_timeout(1500)

            # Years of experience dropdowns
            exp_sel = page.locator("select[id*='experience'], select[id*='years']")
            if await exp_sel.count() > 0:
                await exp_sel.first.select_option(label="10+") if True else None

            # Yes/No radio buttons for common questions
            for text in ["Do you have", "Are you authorized", "Are you legally"]:
                yes_radio = page.locator(f"label:has-text('{text}') ~ * input[value*='Yes'], label:has-text('Yes')")
                if await yes_radio.count() > 0:
                    await yes_radio.first.check()

            # Next button
            next_btn = page.locator("button:has-text('Next'), button:has-text('Continue'), button[aria-label='Continue to next step']")
            review_btn = page.locator("button:has-text('Review'), button:has-text('Submit application')")

            if await review_btn.count() > 0:
                log(f"LinkedIn Easy Apply: reached Review/Submit for {job['title']}")
                return True  # Ready to submit

            if await next_btn.count() > 0:
                await next_btn.first.click()
                await page.wait_for_timeout(1500)
            else:
                break

    except Exception as e:
        log(f"LinkedIn fill error: {e}", "WARN")
    return False

async def fill_greenhouse(page, job, cv_path):
    """Fill Greenhouse ATS form."""
    try:
        # Name
        first = page.locator("input#first_name, input[name='job_application[first_name]']")
        last  = page.locator("input#last_name, input[name='job_application[last_name]']")
        if await first.count() > 0:
            await first.first.fill("Harshkumar")
        if await last.count() > 0:
            await last.first.fill("Patel")

        # Email
        email = page.locator("input#email, input[name='job_application[email]']")
        if await email.count() > 0:
            await email.first.fill(PROFILE["email"])

        # Phone
        phone = page.locator("input#phone, input[name='job_application[phone]']")
        if await phone.count() > 0:
            await phone.first.fill(PROFILE["phone"])

        # LinkedIn
        linkedin_field = page.locator("input[name*='linkedin'], input[placeholder*='LinkedIn']")
        if await linkedin_field.count() > 0:
            await linkedin_field.first.fill(PROFILE["linkedin"])

        # Resume upload
        resume_input = page.locator("input[type='file'][name*='resume'], input[type='file']")
        if await resume_input.count() > 0 and cv_path:
            await resume_input.first.set_input_files(cv_path)

        # Location
        loc_field = page.locator("input[name*='location'], input[placeholder*='Location']")
        if await loc_field.count() > 0:
            await loc_field.first.fill("Berlin, Germany")

        log(f"Greenhouse: form filled for {job['title']}")
        return True

    except Exception as e:
        log(f"Greenhouse fill error: {e}", "WARN")
        return False

async def fill_generic_form(page, job, cv_path):
    """Generic form filler — works on most application forms."""
    try:
        field_map = {
            # Name fields
            "input[name*='first_name' i], input[id*='firstName' i], input[placeholder*='First name' i]": "Harshkumar",
            "input[name*='last_name' i], input[id*='lastName' i], input[placeholder*='Last name' i]": "Patel",
            "input[name*='full_name' i], input[id*='fullName' i], input[placeholder*='Full name' i]": PROFILE["name"],
            # Contact
            "input[type='email'], input[name*='email' i]": PROFILE["email"],
            "input[type='tel'], input[name*='phone' i]": PROFILE["phone"],
            # Location
            "input[name*='city' i], input[placeholder*='City' i]": "Berlin",
            "input[name*='country' i], input[placeholder*='Country' i]": "Germany",
            "input[name*='location' i], input[placeholder*='Location' i]": "Berlin, Germany",
            # Links
            "input[name*='linkedin' i], input[placeholder*='LinkedIn' i]": PROFILE["linkedin"],
            "input[name*='portfolio' i], input[name*='website' i], input[placeholder*='Portfolio' i]": PROFILE["portfolio"],
            # Cover letter / message
            "textarea[name*='cover' i], textarea[placeholder*='Cover' i], textarea[name*='message' i]": f"I am excited to apply for the {job['title']} position at {job['company']}. With 10+ years in engineering and operations, plus hands-on AI app development (22 live production tools), I bring a unique combination of technical execution and operational expertise. Please see my attached CV for details.",
        }

        for selector, value in field_map.items():
            field = page.locator(selector)
            if await field.count() > 0:
                try:
                    await field.first.fill(value)
                    await page.wait_for_timeout(200)
                except Exception:
                    pass

        # File upload for resume
        file_inputs = page.locator("input[type='file']")
        if await file_inputs.count() > 0 and cv_path:
            await file_inputs.first.set_input_files(cv_path)
            await page.wait_for_timeout(1000)

        log(f"Generic form filled for {job['title']}")
        return True

    except Exception as e:
        log(f"Generic fill error: {e}", "WARN")
        return False

# ── MAIN AGENT FLOW ───────────────────────────────────────────────────────────
async def run_agent(dry_run=False, single_url=None):
    """Main autonomous agent loop."""
    from playwright.async_api import async_playwright

    log("=" * 60)
    log(f"Job Copilot Agent starting — {'DRY RUN' if dry_run else 'LIVE'}")
    log("=" * 60)

    # 1. Fetch all jobs
    if single_url:
        jobs = [{"id": "manual", "title": "Manual", "company": "Unknown", "location": "",
                 "salary": "", "description": "", "apply_url": single_url, "source": "Manual",
                 "posted": "", "score": None}]
    else:
        jobs = fetch_all_jobs()
        if not jobs:
            log("No jobs fetched. Check your API keys.", "WARN")
            return

    # 2. Score each job
    log(f"Scoring {len(jobs)} jobs against your profile...")
    scored = []
    for job in jobs:
        result = score_job(job)
        job["score"] = result.get("score", 0)
        job["score_reason"] = result.get("reason", "")
        job["strengths"] = result.get("strengths", [])
        job["gaps"] = result.get("gaps", [])
        if job["score"] >= MIN_SCORE:
            scored.append(job)
            log(f"  ✅ {job['score']}% — {job['title']} @ {job['company']}")
        else:
            log(f"  ❌ {job['score']}% — {job['title']} @ {job['company']} (below {MIN_SCORE}% threshold)")

    scored.sort(key=lambda j: j["score"], reverse=True)
    to_apply = scored[:MAX_APPLY]
    log(f"\n{len(scored)} jobs above threshold. Applying to top {len(to_apply)}.")

    if not to_apply:
        log("No jobs met the minimum score threshold.")
        return

    # 3. Apply to each job
    applied = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)  # Visible so you can watch
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        for i, job in enumerate(to_apply):
            log(f"\n[{i+1}/{len(to_apply)}] Applying: {job['title']} @ {job['company']} ({job['score']}%)")

            # Generate tailored CV
            log("  Generating tailored CV...")
            cv_text = generate_cv(job)
            cv_path = save_cv_file(cv_text, job) if cv_text else None

            # Open the apply URL
            if not job.get("apply_url"):
                log("  No apply URL found, skipping.", "WARN")
                continue

            page = await context.new_page()
            try:
                log(f"  Opening: {job['apply_url']}")
                await page.goto(job["apply_url"], wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Detect form type and fill
                form_type = detect_form_type(page)
                log(f"  Form type: {form_type}")

                filled = False
                if form_type == "linkedin":
                    filled = await fill_linkedin_easy_apply(page, job, cv_path)
                elif form_type == "greenhouse":
                    filled = await fill_greenhouse(page, job, cv_path)
                else:
                    filled = await fill_generic_form(page, job, cv_path)

                if filled and not dry_run:
                    if AUTO_SUBMIT:
                        # Find and click submit button
                        submit = page.locator("button:has-text('Submit'), input[type='submit'], button[type='submit']:has-text('Apply')")
                        if await submit.count() > 0:
                            await submit.first.click()
                            await page.wait_for_timeout(3000)
                            log(f"  ✅ SUBMITTED: {job['title']} @ {job['company']}")
                            applied.append(job)
                        else:
                            log("  ⚠️ Submit button not found — review the page", "WARN")
                    else:
                        log("  ⏸️ Form filled — auto_submit is OFF. Review and click Submit manually.")
                        input(f"  Press ENTER after you've reviewed and submitted the application for {job['title']}...")
                        applied.append(job)
                elif dry_run:
                    log("  🔍 DRY RUN — form filled but not submitted")
                    await page.wait_for_timeout(3000)

            except Exception as e:
                log(f"  Error applying to {job['title']}: {e}", "ERROR")
            finally:
                await page.wait_for_timeout(2000)
                if not AUTO_SUBMIT:
                    pass  # Keep page open for manual review
                else:
                    await page.close()

            time.sleep(2)  # Polite delay between applications

        log("\n" + "=" * 60)
        log(f"Agent complete. Applied to {len(applied)}/{len(to_apply)} jobs.")
        for job in applied:
            log(f"  ✅ {job['title']} @ {job['company']} ({job['score']}%)")

        await context.close()
        await browser.close()

# ── SETUP & CLI ───────────────────────────────────────────────────────────────
def setup():
    """Interactive setup for first-time configuration."""
    print("\n🚀 Job Copilot Agent Setup")
    print("=" * 40)
    cfg = load_config()
    cfg["gemini_key"] = input("Gemini API key (get free at aistudio.google.com): ").strip() or cfg.get("gemini_key", "")
    cfg["rapidapi_key"]  = input(f"RapidAPI key [{RAPIDAPI_KEY[:10]}...]: ").strip() or RAPIDAPI_KEY
    cfg["min_score"]     = int(input("Minimum match score to apply (0-100) [60]: ").strip() or 60)
    cfg["max_apply_per_run"] = int(input("Max applications per run [5]: ").strip() or 5)
    auto = input("Auto-submit without confirmation? (y/N) [N]: ").strip().lower()
    cfg["auto_submit"] = auto == "y"
    cfg["profile"] = PROFILE
    save_config(cfg)
    print("\n✅ Config saved to config.json")
    print("Run: python3 agent.py --run")

def print_status():
    """Print current agent status."""
    print(f"\n📊 Job Copilot Agent Status")
    print(f"  Gemini key:    {'✅ set' if GEMINI_KEY else '❌ missing (get free at aistudio.google.com)'}")
    print(f"  RapidAPI key:  {'✅ set' if RAPIDAPI_KEY else '❌ missing'}")
    print(f"  Min score:     {MIN_SCORE}%")
    print(f"  Max apply/run: {MAX_APPLY}")
    print(f"  Auto submit:   {'⚠️ ON' if AUTO_SUBMIT else '🔒 OFF (manual confirm)'}")
    print(f"  Search queries: {len(SEARCH_QUERIES)}")
    print(f"  Log: {LOG_FILE}")
    print(f"  CVs: {CV_DIR}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Copilot AI Agent")
    parser.add_argument("--run",        action="store_true", help="Run full auto-apply agent")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch and score jobs only")
    parser.add_argument("--dry-run",    action="store_true", help="Fill forms but don't submit")
    parser.add_argument("--job-url",    type=str,            help="Apply to a specific job URL")
    parser.add_argument("--setup",      action="store_true", help="Configure the agent")
    parser.add_argument("--status",     action="store_true", help="Show current status")
    args = parser.parse_args()

    if args.setup:
        setup()
    elif args.status:
        print_status()
    elif args.fetch_only:
        jobs = fetch_all_jobs()
        print(f"\n📋 Top 10 jobs by relevance:")
        for j in sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)[:10]:
            print(f"  {j.get('score','?')}% — {j['title']} @ {j['company']} [{j['source']}]")
    elif args.run or args.dry_run or args.job_url:
        import asyncio
        asyncio.run(run_agent(dry_run=args.dry_run, single_url=args.job_url))
    else:
        parser.print_help()
        print_status()
