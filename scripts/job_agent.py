import os, json, re, time, requests
from datetime import datetime, timezone
from pathlib import Path

PROFILE = {
    "name": "Harshkumar Patel",
    "location": "Berlin, Germany",
    "summary": "Operations Manager + AI App Builder. Built 22 live tools (React/Firebase/Gemini). 10yr engineering. DFMEA, SolidWorks, additive manufacturing. Managed PayPal, GetYourGuide 370 guests, Revolut at Bella and Bona GmbH.",
    "skills": ["AI App Development","React","TypeScript","Firebase","Google Gemini AI","GitHub Actions",
               "Operations Management","Quality Assurance","HACCP","DFMEA","RCA/CAPA","KPI Management",
               "Logistics Management","SolidWorks","Additive Manufacturing","DFM/DFA","Injection Molding","Vacuum Casting"],
    "preferences": {
        "locations": ["Berlin","Germany","remote","hybrid Germany"],
        "salary_min_eur": 55000,
        "open_to": ["operations management","AI tools","product management","quality engineering",
                    "technical operations","logistics technology","food tech","internal tooling"]
    }
}

GEMINI_KEY   = os.environ.get("GEMINI_KEY", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
JOBS_FILE    = Path("docs/data/jobs.json")
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] {msg}", flush=True)


def call_gemini(prompt):
    if not GEMINI_KEY:
        return None
    try:
        import google.genai as genai
        client = genai.Client(api_key=GEMINI_KEY)
        r = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return r.text
    except Exception as e:
        log(f"Gemini error: {e}")
        return None


def generate_queries():
    log("Generating search queries from profile (no hardcoded keywords)...")
    skills_str = ", ".join(PROFILE["skills"][:10])
    prompt = (
        "Job search strategist. Generate 10 search queries for this candidate on LinkedIn/Indeed/Glassdoor Germany.\n\n"
        "CANDIDATE PROFILE:\n"
        "Name: Harshkumar Patel | Location: Berlin, Germany\n"
        "Summary: " + PROFILE["summary"] + "\n"
        "Skills: " + skills_str + "\n"
        "Open to: " + ", ".join(PROFILE["preferences"]["open_to"]) + "\n"
        "Salary target: 55,000+ EUR/year (EU Blue Card)\n\n"
        "Rules:\n"
        "- Specific to this person's unique ops + AI app building + engineering background\n"
        "- Mix: current role, AI/tech skills, engineering, hybrid ops+tech\n"
        "- Cover Berlin/Germany and remote\n"
        "- Target EU Blue Card salary 55k+ EUR\n\n"
        'Return ONLY a JSON array: [{"query":"keywords","location":"city/region"}] - exactly 10 items.'
    )
    raw = call_gemini(prompt)
    if raw:
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            try:
                queries = json.loads(m.group())
                log(f"Generated {len(queries)} smart queries from profile")
                for q in queries:
                    log(f"  '{q['query']}' in '{q['location']}'")
                return [(q['query'], q['location']) for q in queries]
            except Exception as e:
                log(f"Query parse error: {e}")

    log("Using fallback queries")
    return [
        ("operations manager AI tools technology", "Berlin Germany"),
        ("quality assurance engineer digital operations", "Germany"),
        ("logistics manager technology platform", "Berlin"),
        ("product manager internal tools", "Germany remote"),
        ("AI developer operations engineer", "Berlin remote"),
        ("technical operations manager food tech", "Germany hybrid"),
        ("digital transformation operations manager", "Berlin"),
        ("mechanical engineer AI product development", "Germany"),
        ("ops tech engineer startup", "Berlin remote"),
        ("food technology quality operations manager", "Germany"),
    ]


def fetch_jsearch(query, location):
    if not RAPIDAPI_KEY:
        return []
    try:
        r = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={"x-rapidapi-host": "jsearch.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY},
            params={"query": f"{query} {location}", "page": "1", "num_pages": "2", "date_posted": "month"},
            timeout=25
        )
        r.raise_for_status()
        jobs = []
        for j in r.json().get("data", []):
            loc = "Remote" if j.get("job_is_remote") else ", ".join(
                filter(None, [j.get("job_city", ""), j.get("job_country", "")]))
            sal = ""
            if j.get("job_min_salary"):
                sal = f"${int(j['job_min_salary']):,}-${int(j.get('job_max_salary', j['job_min_salary'])):,}/{j.get('job_salary_period', 'yr')}"
            src = j.get("job_publisher", "")
            src = ("LinkedIn" if "linkedin" in src.lower() else
                   "Indeed" if "indeed" in src.lower() else
                   "Glassdoor" if "glassdoor" in src.lower() else
                   src or "JSearch")
            jobs.append({
                "id": str(j["job_id"]),
                "title": j.get("job_title", ""),
                "company": j.get("employer_name", ""),
                "location": loc,
                "salary": sal,
                "description": (j.get("job_description", "") or "")[:2000],
                "applyUrl": j.get("job_apply_link") or j.get("job_google_link", ""),
                "source": src,
                "posted": j.get("job_posted_at_datetime_utc", ""),
                "score": None,
                "analysis": None,
            })
        log(f"  JSearch '{query[:35]}': {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  JSearch error: {e}")
        return []


def fetch_remotive():
    try:
        r = requests.get("https://remotive.com/api/remote-jobs?limit=50", timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs", []):
            desc = re.sub(r'<[^>]+>', ' ', j.get("description", ""))[:2000]
            jobs.append({
                "id": f"rm-{j['id']}",
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": "Remote",
                "salary": j.get("salary", ""),
                "description": desc,
                "applyUrl": j.get("url", ""),
                "source": "Remotive",
                "posted": j.get("publication_date", ""),
                "score": None,
                "analysis": None,
            })
        log(f"  Remotive: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  Remotive error: {e}")
        return []


def score_jobs(jobs):
    if not GEMINI_KEY:
        log("No Gemini key - skipping AI scoring")
        return jobs
    skills_str = ", ".join(PROFILE["skills"][:12])
    profile_str = f"Ops Manager + AI Builder Berlin. 22 live apps built. Skills: {skills_str}"
    for i, job in enumerate(jobs):
        if job.get("score") is not None:
            continue
        try:
            prompt = (
                "Score this job for the candidate. Return ONLY valid JSON.\n\n"
                f"JOB: {job['title']} at {job['company']} ({job['location']})\n"
                f"DESCRIPTION: {job['description'][:600]}\n\n"
                f"CANDIDATE: {profile_str}\n\n"
                'Return: {"score":0-100,"reason":"<8 words>"}'
            )
            raw = call_gemini(prompt)
            if raw:
                m = re.search(r'\{[^}]+\}', raw)
                if m:
                    d = json.loads(m.group())
                    job["score"] = int(d.get("score", 0))
                    job["analysis"] = d.get("reason", "")
            if i > 0 and i % 10 == 0:
                log(f"  Scored {i}/{len(jobs)}...")
            time.sleep(0.4)
        except Exception as e:
            job["score"] = 0
            job["analysis"] = "error"
    return jobs


def main():
    log("=" * 50)
    log(f"Job Copilot Agent v2.1 — {datetime.now(timezone.utc).isoformat()}")
    log(f"Gemini: {'OK' if GEMINI_KEY else 'MISSING'} | RapidAPI: {'OK' if RAPIDAPI_KEY else 'MISSING'}")
    log("=" * 50)

    # Load existing jobs (preserve history)
    existing = {}
    if JOBS_FILE.exists():
        try:
            old = json.loads(JOBS_FILE.read_text())
            for j in old.get("jobs", []):
                existing[j["id"]] = j
            log(f"Loaded {len(existing)} existing jobs from history")
        except Exception as e:
            log(f"Could not load existing: {e}")

    # Step 1: Smart queries from profile
    queries = generate_queries()

    # Step 2: Fetch new jobs
    log(f"Fetching from all platforms ({len(queries)} queries)...")
    new_jobs = []
    seen = set()
    for query, location in queries:
        for job in fetch_jsearch(query, location):
            if job["id"] not in seen and job["id"] not in existing:
                seen.add(job["id"])
                new_jobs.append(job)
        time.sleep(1.5)
    for job in fetch_remotive():
        if job["id"] not in seen and job["id"] not in existing:
            seen.add(job["id"])
            new_jobs.append(job)
    log(f"Found {len(new_jobs)} new jobs")

    # Step 3: Score with Gemini
    if new_jobs:
        log(f"Scoring {len(new_jobs)} jobs with Gemini AI...")
        new_jobs = score_jobs(new_jobs)

    # Merge and save
    all_jobs = list(existing.values()) + new_jobs
    all_jobs.sort(key=lambda j: (j.get("score") or 0), reverse=True)
    all_jobs = all_jobs[:500]

    stats = {
        "total": len(all_jobs),
        "new_this_run": len(new_jobs),
        "high_match": len([j for j in all_jobs if (j.get("score") or 0) >= 70])
    }

    JOBS_FILE.write_text(json.dumps({
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "agentVersion": "2.1",
        "stats": stats,
        "queries": [{"query": q, "location": l} for q, l in queries],
        "jobs": all_jobs,
    }, indent=2, ensure_ascii=False))

    log(f"Saved {len(all_jobs)} jobs. Stats: {json.dumps(stats)}")
    top = [j for j in all_jobs if (j.get("score") or 0) >= 70][:8]
    if top:
        log(f"Top matches (70%+):")
        for j in top:
            log(f"  {j['score']}% — {j['title']} @ {j['company']} [{j['source']}]")
    log("Agent run complete.")


if __name__ == "__main__":
    main()
