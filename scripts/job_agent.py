"""
Job Copilot Agent v4.0 Ã¢ÂÂ 5 Platforms + Berlin-First + Continuous Loop
=======================================================================
Platforms: LinkedIn, Xing, Stepstone, Indeed, Generic
Priority: Berlin, Germany first Ã¢ÂÂ always
"""

import os, json, re, time, asyncio, requests
from datetime import datetime, timezone
from pathlib import Path

PROFILE = {
    "name": "Harshkumar Patel", "first_name": "Harshkumar", "last_name": "Patel",
    "email": os.environ.get("LINKEDIN_EMAIL", "patelharsh513@gmail.com"),
    "phone": "+4915560938054", "location": "Berlin, Germany",
    "linkedin": "https://www.linkedin.com/in/patelharsh513",
    "portfolio": "https://berlinkitchen123-blip.github.io",
    "summary": "Operations Manager + AI App Builder. Built 22 live production tools (React/Firebase/Gemini). Bella and Bona GmbH Berlin Ã¢ÂÂ QC system credited by Forbes 30 Under 30 CEO. 10yr mechanical engineering: DFMEA SolidWorks additive manufacturing. Managed PayPal GetYourGuide Revolut Personio. EU Blue Card applicant.",
    "skills": ["AI App Development","React","TypeScript","Firebase","Google Gemini AI","Operations Management","Quality Assurance","HACCP","DFMEA","RCA/CAPA","KPI Management","Logistics Management","SolidWorks","Additive Manufacturing","DFM/DFA","Process Validation","Project Management"],
    "cover_letter_short": "I am excited to apply for this position in Berlin. With 10+ years in engineering and operations plus 22 production AI tools built independently, I bring a unique combination of technical execution and operational leadership.",
}

GEMINI_KEY   = os.environ.get("GEMINI_KEY", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
LI_EMAIL     = os.environ.get("LINKEDIN_EMAIL", "patelharsh513@gmail.com")
LI_PASSWORD  = os.environ.get("LINKEDIN_PASSWORD", "")
XING_EMAIL   = os.environ.get("XING_EMAIL", "patelharsh513@gmail.com")
XING_PASSWORD = os.environ.get("XING_PASSWORD", "")
STEPSTONE_EMAIL = os.environ.get("STEPSTONE_EMAIL", "patelharsh513@gmail.com")
STEPSTONE_PASSWORD = os.environ.get("STEPSTONE_PASSWORD", "")
MIN_SCORE    = int(os.environ.get("MIN_SCORE", "60"))
LOOP_INTERVAL = 999999
MAX_APPLY_PER_CYCLE = 0   # Apply to 5 per cycle across all platforms

JOBS_FILE    = Path("docs/data/jobs.json")
APPLIED_FILE = Path("docs/data/applied.json")
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Berlin/Germany location bonus in scoring
BERLIN_BONUS = 10

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] {msg}", flush=True)

def call_gemini(prompt):
    if not GEMINI_KEY: return None
    for attempt in range(2):
        try:
            import google.genai as genai
            client = genai.Client(api_key=GEMINI_KEY)
            return client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
        except Exception as e:
            log(f"Gemini attempt {attempt+1}: {e}")
            time.sleep(3)
    return None

# Ã¢ÂÂÃ¢ÂÂ QUERY GENERATION Ã¢ÂÂ BERLIN FIRST Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def generate_queries():
    log("Generating Berlin-first search queries from profile...")
    skills = ", ".join(PROFILE["skills"][:8])
    prompt = (
        "Generate 15 job search queries for this candidate. IMPORTANT: Berlin Germany jobs FIRST.\n\n"
        f"CANDIDATE: {PROFILE['name']} | Location: {PROFILE['location']}\n"
        f"Summary: {PROFILE['summary']}\nSkills: {skills}\n"
        "Target salary: 55,000+ EUR | Work auth: Germany employment visa (EU Blue Card target)\n\n"
        "Rules:\n"
        "- First 8 queries: Berlin or Berlin Germany location\n"
        "- Next 4 queries: Germany (other cities or remote)\n"
        "- Last 3 queries: Remote Europe\n"
        "- Specific to this person's ops+AI+engineering background\n"
        "- Include German job titles too (e.g. Betriebsleiter, Qualitatsmanager)\n"
        "- Mix: operations, AI tools, quality, logistics tech, product management\n\n"
        'Return ONLY JSON: [{"query":"keywords","location":"city/region"}] - 15 items.'
    )
    raw = call_gemini(prompt)
    if raw:
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            try:
                queries = json.loads(m.group())
                log(f"Gemini: {len(queries)} queries (Berlin-first)")
                for q in queries[:5]:
                    log(f"  '{q['query']}' in '{q['location']}'")
                return [(q['query'], q['location']) for q in queries]
            except Exception as e:
                log(f"Query parse error: {e}")

    log("Using fallback Berlin-first queries")
    return [
        # Berlin first
        ("operations manager AI tools", "Berlin"),
        ("quality assurance engineer digital Berlin", "Berlin Germany"),
        ("logistics operations manager", "Berlin Germany"),
        ("AI developer operations engineer", "Berlin"),
        ("technical operations manager", "Berlin"),
        ("Betriebsleiter Qualitatsmanagement", "Berlin"),
        ("product manager internal tools", "Berlin Germany"),
        ("food technology operations quality", "Berlin"),
        # Germany
        ("operations manager technology platform", "Germany"),
        ("quality engineer HACCP manufacturing", "Germany"),
        ("AI tools product manager", "Germany remote"),
        ("digital transformation operations", "Munich Hamburg Germany"),
        # Remote
        ("operations manager remote", "Germany Europe remote"),
        ("mechanical engineer AI product", "remote Germany"),
        ("AI app developer operations", "remote Europe"),
    ]

# Ã¢ÂÂÃ¢ÂÂ FETCHING Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def fetch_jsearch(query, location):
    if not RAPIDAPI_KEY: return []
    try:
        r = requests.get("https://jsearch.p.rapidapi.com/search",
            headers={"x-rapidapi-host":"jsearch.p.rapidapi.com","x-rapidapi-key":RAPIDAPI_KEY},
            params={"query":f"{query} {location}","page":"1","num_pages":"1"},timeout=20)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("data", []):
            loc = "Remote" if j.get("job_is_remote") else ", ".join(filter(None,[j.get("job_city",""),j.get("job_country","")]))
            src = j.get("job_publisher","")
            src = "LinkedIn" if "linkedin" in src.lower() else "Indeed" if "indeed" in src.lower() else "Glassdoor" if "glassdoor" in src.lower() else src or "JSearch"
            jobs.append({"id":str(j["job_id"]),"title":j.get("job_title",""),"company":j.get("employer_name",""),
                "location":loc,"salary":"","description":(j.get("job_description","") or "")[:2000],
                "applyUrl":j.get("job_apply_link") or j.get("job_google_link",""),
                "source":src,"posted":j.get("job_posted_at_datetime_utc",""),"score":None,"analysis":None,"applied":False})
        log(f"  JSearch '{query[:25]}' {location}: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  JSearch: {e}")
        return []

def fetch_remotive():
    try:
        r = requests.get("https://remotive.com/api/remote-jobs?limit=50", timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs",[]):
            desc = re.sub(r'<[^>]+>',' ', j.get("description",""))[:2000]
            jobs.append({"id":f"rm-{j['id']}","title":j.get("title",""),"company":j.get("company_name",""),
                "location":"Remote","salary":j.get("salary",""),"description":desc,
                "applyUrl":j.get("url",""),"source":"Remotive","posted":j.get("publication_date",""),
                "score":None,"analysis":None,"applied":False})
        log(f"  Remotive: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  Remotive: {e}")
        return []

def fetch_xing_jobs(query="operations manager", location="Berlin"):
    """Fetch from Xing via their public search."""
    try:
        url = f"https://www.xing.com/jobs/search?keywords={requests.utils.quote(query)}&location={requests.utils.quote(location)}&radius=30"
        headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36","Accept-Language":"de-DE,de;q=0.9,en;q=0.8"}
        r = requests.get(url, headers=headers, timeout=15)
        # Extract job links from Xing search (basic scrape)
        jobs = []
        matches = re.findall(r'"slug":"([^"]+)","id":(\d+),"title":"([^"]+)","company":{"name":"([^"]+)"', r.text)
        for slug, job_id, title, company in matches[:10]:
            jobs.append({"id":f"xing-{job_id}","title":title,"company":company,
                "location":location,"salary":"","description":f"{title} at {company} in {location}",
                "applyUrl":f"https://www.xing.com/jobs/{slug}-{job_id}",
                "source":"Xing","posted":datetime.now(timezone.utc).isoformat(),"score":None,"analysis":None,"applied":False})
        if jobs: log(f"  Xing '{query}' {location}: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  Xing fetch: {e}")
        return []

def fetch_stepstone_jobs(query="operations manager", location="Berlin"):
    """Fetch from Stepstone via their API."""
    try:
        url = f"https://www.stepstone.de/5/ergebnisliste.html?ke={requests.utils.quote(query)}&ws={requests.utils.quote(location)}&radius=30&fd=1"
        headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36","Accept-Language":"de-DE,de;q=0.9"}
        r = requests.get(url, headers=headers, timeout=15)
        jobs = []
        # Extract job data from Stepstone page
        matches = re.findall(r'"jobId":(\d+),"title":"([^"]+)","company":"([^"]+)"', r.text)
        if not matches:
            # Try alternative pattern
            matches = re.findall(r'data-at="job-item-title"[^>]*>([^<]+)<', r.text)
        for m in matches[:10]:
            if len(m) == 3:
                job_id, title, company = m
                jobs.append({"id":f"ss-{job_id}","title":title,"company":company,
                    "location":location,"salary":"","description":f"{title} at {company} in {location}",
                    "applyUrl":f"https://www.stepstone.de/stellenangebote--{title.replace(' ','-')}-{job_id}.html",
                    "source":"Stepstone","posted":datetime.now(timezone.utc).isoformat(),"score":None,"analysis":None,"applied":False})
        if jobs: log(f"  Stepstone '{query}' {location}: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  Stepstone fetch: {e}")
        return []

# Ã¢ÂÂÃ¢ÂÂ SCORING Ã¢ÂÂ BERLIN BONUS Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def score_job(job):
    skills_str = ", ".join(PROFILE["skills"][:8])
    prompt = (
        "Score job for candidate. Return ONLY JSON.\n"
        f"JOB: {job['title']} at {job['company']} ({job['location']})\n"
        f"DESC: {job['description'][:400]}\n"
        f"CANDIDATE: Ops Manager + AI Builder Berlin. 22 live apps. EU Blue Card applicant. Skills: {skills_str}\n"
        'Return: {"score":0-100,"reason":"<6 words>"}'
    )
    raw = call_gemini(prompt)
    if raw:
        m = re.search(r'\{[^}]+\}', raw)
        if m:
            try:
                d = json.loads(m.group())
                score = int(d.get("score", 0))
                # Berlin/Germany bonus
                loc = (job.get("location") or "").lower()
                if "berlin" in loc:
                    score = min(100, score + BERLIN_BONUS)
                elif "germany" in loc or "deutschland" in loc:
                    score = min(100, score + 5)
                return score, d.get("reason","")
            except Exception:
                pass
    # Fallback: keyword-based score
    score = 30
    loc = (job.get("location") or "").lower()
    if "berlin" in loc: score += BERLIN_BONUS
    elif "germany" in loc: score += 5
    title_lower = job.get("title","").lower()
    for kw in ["operations","quality","logistics","manager","engineer","AI","product"]:
        if kw.lower() in title_lower: score += 5
    return min(score, 100), "keyword match"

def generate_cv(job):
    return call_gemini(
        f"ATS CV for this job. Plain text, no tables, max 500 words.\n"
        f"JOB: {job['title']} at {job['company']} ({job['location']})\n"
        f"DESC: {job['description'][:600]}\n\n"
        f"CANDIDATE: {PROFILE['name']} | {PROFILE['email']} | {PROFILE['phone']} | {PROFILE['location']}\n"
        f"LinkedIn: {PROFILE['linkedin']} | Portfolio: {PROFILE['portfolio']}\n"
        f"Summary: {PROFILE['summary']}\nSkills: {', '.join(PROFILE['skills'])}\n\n"
        "Instructions: Rewrite summary for this role. If Berlin job, emphasize Berlin presence. "
        "Inject exact JD keywords. Lead with most relevant skills."
    )

# Ã¢ÂÂÃ¢ÂÂ AUTO-APPLY FLOWS Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
async def fill_basic_fields(page, job, cv_text):
    """Fill common form fields Ã¢ÂÂ works across most ATS."""
    filled = False
    field_map = {
        "input[name*='first_name' i], input[id*='firstName' i], input[placeholder*='Vorname' i]": PROFILE["first_name"],
        "input[name*='last_name' i], input[id*='lastName' i], input[placeholder*='Nachname' i]": PROFILE["last_name"],
        "input[name*='full_name' i], input[id*='fullName' i], input[placeholder*='Full name' i]": PROFILE["name"],
        "input[type='email'], input[name*='email' i], input[placeholder*='E-Mail' i]": PROFILE["email"],
        "input[type='tel'], input[name*='phone' i], input[placeholder*='Telefon' i]": PROFILE["phone"],
        "input[name*='city' i], input[placeholder*='Stadt' i], input[placeholder*='City' i]": "Berlin",
        "input[name*='country' i], input[placeholder*='Land' i]": "Germany",
        "input[name*='location' i], input[placeholder*='Location' i]": "Berlin, Germany",
        "input[name*='linkedin' i], input[placeholder*='LinkedIn' i]": PROFILE["linkedin"],
        "input[name*='portfolio' i], input[name*='website' i]": PROFILE["portfolio"],
        "textarea[name*='cover' i], textarea[placeholder*='Motivationsschreiben' i], textarea[placeholder*='Cover' i]": (
            f"Sehr geehrte Damen und Herren,\n\n"
            f"I am excited to apply for the position of {job['title']} at {job['company']} in Berlin. "
            f"{PROFILE['cover_letter_short']}\n\nMit freundlichen GrÃÂ¼ÃÂen,\n{PROFILE['name']}"
        ),
    }
    for selector, value in field_map.items():
        f = page.locator(selector)
        if await f.count() > 0:
            try:
                await f.first.fill(value)
                await page.wait_for_timeout(200)
                filled = True
            except Exception:
                pass

    # Upload CV
    if cv_text:
        cv_path = Path(f"/tmp/cv_{job['id'][:8]}.txt")
        cv_path.write_text(cv_text, encoding='utf-8')
        file_inputs = page.locator("input[type='file']")
        if await file_inputs.count() > 0:
            try:
                await file_inputs.first.set_input_files(str(cv_path))
                await page.wait_for_timeout(1200)
                filled = True
            except Exception:
                pass

    return filled

async def apply_linkedin(page, job, cv_text):
    """LinkedIn Easy Apply."""
    try:
        # Login
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        email_f = page.locator("input#username")
        if await email_f.count() > 0:
            await email_f.fill(LI_EMAIL)
            await page.locator("input#password").fill(LI_PASSWORD)
            await page.locator("button[type='submit']").click()
            await page.wait_for_timeout(4000)

        await page.goto(job["applyUrl"], wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        easy = page.locator("button.jobs-apply-button, button:has-text('Easy Apply'), button:has-text('Einfach bewerben')")
        if await easy.count() == 0:
            log(f"  No Easy Apply button")
            return False
        await easy.first.click()
        await page.wait_for_timeout(2000)

        for step in range(10):
            await fill_basic_fields(page, job, cv_text)

            # Submit check
            submit = page.locator("button:has-text('Submit application'), button:has-text('Bewerbung abschicken'), button[aria-label='Submit application']")
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
                return True

            # Next step
            nxt = page.locator("button:has-text('Next'), button:has-text('Weiter'), button:has-text('Continue'), button:has-text('Review'), button:has-text('ÃÂberprÃÂ¼fen')")
            if await nxt.count() > 0:
                await nxt.first.click()
                await page.wait_for_timeout(1500)
            else:
                break
    except Exception as e:
        log(f"  LinkedIn: {e}")
    return False

async def apply_xing(page, context, job, cv_text):
    """Xing job application Ã¢ÂÂ Jetzt bewerben."""
    try:
        # Cookies first (Google login), password as fallback
        xing_cookies = os.environ.get("XING_COOKIES", "")
        xing_pw = os.environ.get("XING_PASSWORD", "")
        xing_em = os.environ.get("XING_EMAIL", "patelharsh513@gmail.com")
        if xing_cookies:
            try:
                await context.add_cookies(json.loads(xing_cookies))
                log("  Xing: cookies injected")
            except Exception as ce:
                log(f"  Xing cookie error: {ce}")
        elif xing_pw:
            await page.goto("https://www.xing.com/login", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)
            email_f = page.locator("input[name='email'], input[type='email']")
            pwd_f = page.locator("input[name='password'], input[type='password']")
            if await email_f.count() > 0:
                await email_f.fill(xing_em)
                await pwd_f.fill(xing_pw)
                submit_btn = page.locator("button[type='submit']")
                if await submit_btn.count() > 0:
                    await submit_btn.first.click()
                    await page.wait_for_timeout(4000)
                    log("  Xing: logged in with password")

        await page.goto(job["applyUrl"], wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Click Jetzt bewerben / Apply now
        apply_btn = page.locator("button:has-text('Jetzt bewerben'), a:has-text('Jetzt bewerben'), button:has-text('Apply now'), a:has-text('Apply now')")
        if await apply_btn.count() > 0:
            await apply_btn.first.click()
            await page.wait_for_timeout(2000)

        # Fill form
        filled = await fill_basic_fields(page, job, cv_text)

        # Submit
        if filled:
            submit = page.locator("button[type='submit'], button:has-text('Bewerbung senden'), button:has-text('Submit'), button:has-text('Absenden')")
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
                return True
    except Exception as e:
        log(f"  Xing: {e}")
    return False

async def apply_stepstone(page, context, job, cv_text):
    """Stepstone application Ã¢ÂÂ Jetzt bewerben."""
    try:
        await page.goto(job["applyUrl"], wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Click apply button
        apply_btn = page.locator("button:has-text('Jetzt bewerben'), a:has-text('Jetzt bewerben'), button:has-text('Bewerben'), a[data-genesis-element='BTN']")
        if await apply_btn.count() > 0:
            await apply_btn.first.click()
            await page.wait_for_timeout(2000)

        # Stepstone login if needed
        ss_cookies = os.environ.get("STEPSTONE_COOKIES", "")
        if ss_cookies:
            try:
                await context.add_cookies(json.loads(ss_cookies))
                log("  Stepstone: session cookies injected (Google login)")
            except Exception as ce:
                log(f"  Stepstone cookie error: {ce}")

        filled = await fill_basic_fields(page, job, cv_text)

        if filled:
            submit = page.locator("button[type='submit'], button:has-text('Bewerbung abschicken'), button:has-text('Jetzt bewerben'), button:has-text('Submit')")
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
                return True
    except Exception as e:
        log(f"  Stepstone: {e}")
    return False

async def apply_indeed(page, job, cv_text):
    """Indeed / de.indeed.com application."""
    try:
        await page.goto(job["applyUrl"], wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Click apply
        apply_btn = page.locator("button:has-text('Jetzt bewerben'), button:has-text('Apply now'), a:has-text('Apply now'), span:has-text('Apply now')")
        if await apply_btn.count() > 0:
            await apply_btn.first.click()
            await page.wait_for_timeout(2000)

        # Login to Indeed if needed
        email_f = page.locator("input[type='email']")
        if await email_f.count() > 0:
            val = await email_f.first.input_value()
            if not val:
                await email_f.first.fill(LI_EMAIL)
                nxt = page.locator("button:has-text('Continue'), button:has-text('Weiter')")
                if await nxt.count() > 0:
                    await nxt.first.click()
                    await page.wait_for_timeout(2000)

        filled = await fill_basic_fields(page, job, cv_text)

        for step in range(6):
            submit = page.locator("button:has-text('Submit your application'), button:has-text('Bewerbung absenden'), button:has-text('Submit')")
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
                return True
            nxt = page.locator("button:has-text('Continue'), button:has-text('Next'), button:has-text('Weiter')")
            if await nxt.count() > 0:
                await nxt.first.click()
                await page.wait_for_timeout(1500)
            else:
                break
    except Exception as e:
        log(f"  Indeed: {e}")
    return False

async def apply_generic(page, job, cv_text):
    """Generic form filler for company ATS (Greenhouse, Lever, Workday, etc.)."""
    filled = await fill_basic_fields(page, job, cv_text)
    if filled:
        submit = page.locator("button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply'), button:has-text('Send'), button:has-text('Absenden'), button:has-text('Bewerben')")
        if await submit.count() > 0:
            try:
                await submit.first.click()
                await page.wait_for_timeout(2500)
                return True
            except Exception:
                pass
    return filled

async def apply_to_job(job, cv_text):
    """Route to correct apply function based on job source/URL."""
    url = job.get("applyUrl", "")
    if not url:
        log(f"  No URL: {job['title']}")
        return False

    log(f"  Applying [{job['source']}]: {job['title']} @ {job['company']} ({job.get('location')}) Ã¢ÂÂ {job['score']}%")

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
            geolocation={"longitude": 13.404954, "latitude": 52.520008},  # Berlin coordinates
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)
            live_url = page.url

            if "linkedin.com" in live_url:
                result = await apply_linkedin(page, job, cv_text)
            elif "xing.com" in live_url or job["source"] == "Xing":
                result = await apply_xing(page, context, job, cv_text)
            elif "stepstone.de" in live_url or job["source"] == "Stepstone":
                result = await apply_stepstone(page, context, job, cv_text)
            elif "indeed.com" in live_url or job["source"] == "Indeed":
                result = await apply_indeed(page, job, cv_text)
            else:
                result = await apply_generic(page, job, cv_text)

            if result:
                log(f"  Ã¢ÂÂ APPLIED: {job['title']} @ {job['company']}")
            else:
                log(f"  Ã¢ÂÂ Ã¯Â¸Â Form not completed: {url}")
            return result

        except Exception as e:
            log(f"  Error: {e}")
            return False
        finally:
            await browser.close()

# Ã¢ÂÂÃ¢ÂÂ DATA PERSISTENCE Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
def load_jobs():
    if JOBS_FILE.exists():
        try: return json.loads(JOBS_FILE.read_text())
        except Exception: pass
    return {"lastUpdated": None, "stats": {}, "queries": [], "jobs": []}

def save_jobs(data):
    JOBS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def load_applied():
    if APPLIED_FILE.exists():
        try: return set(json.loads(APPLIED_FILE.read_text()))
        except Exception: pass
    return set()

def save_applied(s):
    APPLIED_FILE.write_text(json.dumps(sorted(list(s)), indent=2))

# Ã¢ÂÂÃ¢ÂÂ MAIN CYCLE Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
async def run_cycle(applied_ids, cycle_num):
    log(f"\n=== CYCLE {cycle_num} | {datetime.now(timezone.utc).strftime('%H:%M UTC')} ===")

    store = load_jobs()
    existing = {j["id"]: j for j in store.get("jobs", [])}

    queries = generate_queries()

    # Fetch Ã¢ÂÂ Berlin queries first
    new_jobs = []
    seen = set()
    for query, location in queries:
        for job in fetch_jsearch(query, location):
            if job["id"] not in seen and job["id"] not in existing:
                seen.add(job["id"]); new_jobs.append(job)
        time.sleep(1.5)

    # Also fetch Xing and Stepstone for Berlin specifically
    for j in fetch_xing_jobs("operations manager quality", "Berlin"):
        if j["id"] not in seen and j["id"] not in existing:
            seen.add(j["id"]); new_jobs.append(j)

    for j in fetch_stepstone_jobs("operations manager", "Berlin"):
        if j["id"] not in seen and j["id"] not in existing:
            seen.add(j["id"]); new_jobs.append(j)

    for j in fetch_remotive():
        if j["id"] not in seen and j["id"] not in existing:
            seen.add(j["id"]); new_jobs.append(j)

    log(f"New jobs: {len(new_jobs)}")

    # Score all new jobs
    for job in new_jobs:
        score, reason = score_job(job)
        job["score"] = score
        job["analysis"] = reason
        time.sleep(0.3)

    # Sort: Berlin first, then by score
    def sort_key(j):
        loc = (j.get("location") or "").lower()
        berlin_first = 0 if "berlin" in loc else (1 if "germany" in loc or "deutschland" in loc else 2)
        return (berlin_first, -(j.get("score") or 0))

    new_jobs.sort(key=sort_key)

    # Apply to qualifying jobs
    applied_this = 0
    for job in new_jobs:
        if job["score"] >= MIN_SCORE and job["id"] not in applied_ids and applied_this < MAX_APPLY_PER_CYCLE:
            cv = generate_cv(job)
            success = await apply_to_job(job, cv)
            if success:
                job["applied"] = True
                job["appliedAt"] = datetime.now(timezone.utc).isoformat()
                applied_ids.add(job["id"])
                applied_this += 1
                save_applied(applied_ids)
            time.sleep(3)

    # Merge & save Ã¢ÂÂ Berlin jobs shown first
    all_jobs = list(existing.values()) + new_jobs
    all_jobs.sort(key=sort_key)
    all_jobs = all_jobs[:500]

    stats = {
        "total": len(all_jobs),
        "new_this_cycle": len(new_jobs),
        "berlin_jobs": len([j for j in all_jobs if "berlin" in (j.get("location") or "").lower()]),
        "high_match_70plus": len([j for j in all_jobs if (j.get("score") or 0) >= 70]),
        "applied_total": len(applied_ids),
        "applied_this_cycle": applied_this,
    }

    save_jobs({
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "agentVersion": "4.0",
        "stats": stats,
        "platforms": ["LinkedIn", "Xing", "Stepstone", "Indeed", "Remotive", "JSearch"],
        "queries": [{"query": q, "location": l} for q, l in queries],
        "jobs": all_jobs,
    })

    log(f"Stats: {json.dumps(stats)}")
    top = [j for j in all_jobs if (j.get("score") or 0) >= 65][:8]
    if top:
        log("Top matches:")
        for j in top:
            tag = "APPLIED" if j.get("applied") else "     "
            loc_flag = "Ã°ÂÂÂ©Ã°ÂÂÂª" if "berlin" in (j.get("location") or "").lower() else "Ã°ÂÂÂ"
            log(f"  [{tag}] {loc_flag} {j['score']}% Ã¢ÂÂ {j['title']} @ {j['company']} [{j['source']}]")

    return applied_ids

# Ã¢ÂÂÃ¢ÂÂ ENTRY POINT Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
async def main():
    log("=" * 60)
    log("Job Copilot Agent v4.0 Ã¢ÂÂ 5 Platforms + Berlin-First + Continuous")
    log(f"Platforms: LinkedIn | Xing | Stepstone | Indeed | Remotive")
    log(f"Gemini: {'OK' if GEMINI_KEY else 'MISSING'} | RapidAPI: {'OK' if RAPIDAPI_KEY else 'MISSING'}")
    log(f"LinkedIn: {'OK' if LI_PASSWORD else 'MISSING'} | Xing: {'OK-cookies' if os.environ.get('XING_COOKIES') else ('OK-password' if os.environ.get('XING_PASSWORD') else 'no auth')} | Stepstone: {'OK-cookies' if os.environ.get('STEPSTONE_COOKIES') else 'add STEPSTONE_COOKIES'}")
    log(f"Min score: {MIN_SCORE}% | Max apply/cycle: {MAX_APPLY_PER_CYCLE} | Berlin bonus: +{BERLIN_BONUS}pts")
    log("=" * 60)

    applied_ids = load_applied()
    log(f"Previously applied to {len(applied_ids)} jobs")

    cycle = 0
    start = time.time()
    max_runtime = 360

    while time.time() - start < max_runtime:
        cycle += 1
        try:
            applied_ids = await run_cycle(applied_ids, cycle)
        except Exception as e:
            log(f"Cycle {cycle} error: {e}")

        elapsed = time.time() - start
        remaining = max_runtime - elapsed
        if remaining < LOOP_INTERVAL:
            log("Approaching GitHub Actions timeout Ã¢ÂÂ stopping cleanly")
            break
        log(f"Sleeping {LOOP_INTERVAL}s | Elapsed: {elapsed/3600:.1f}h | Remaining: {remaining/3600:.1f}h")
        time.sleep(LOOP_INTERVAL)

    log("Agent session complete.")

if __name__ == "__main__":
    asyncio.run(main())
