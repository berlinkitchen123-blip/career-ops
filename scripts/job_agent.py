import os, json, re, time, asyncio, requests
from datetime import datetime, timezone
from pathlib import Path

PROFILE = {
    "name": "Harshkumar Patel", "first_name": "Harshkumar", "last_name": "Patel",
    "email": os.environ.get("LINKEDIN_EMAIL", "patelharsh513@gmail.com"),
    "phone": "+4915560938054", "location": "Berlin, Germany",
    "linkedin": "https://www.linkedin.com/in/patelharsh513",
    "portfolio": "https://berlinkitchen123-blip.github.io",
    "summary": "Operations Manager + AI App Builder. Built 22 live tools (React/Firebase/Gemini). Bella and Bona GmbH Berlin — QC system credited by Forbes 30 Under 30 CEO. 10yr mechanical engineering: DFMEA SolidWorks additive manufacturing. Managed PayPal GetYourGuide Revolut Personio.",
    "skills": ["AI App Development","React","TypeScript","Firebase","Google Gemini AI","Operations Management","Quality Assurance","HACCP","DFMEA","RCA/CAPA","KPI Management","Logistics Management","SolidWorks","Additive Manufacturing","DFM/DFA"],
}

GEMINI_KEY   = os.environ.get("GEMINI_KEY", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
LI_EMAIL     = os.environ.get("LINKEDIN_EMAIL", "patelharsh513@gmail.com")
LI_PASSWORD  = os.environ.get("LINKEDIN_PASSWORD", "")
MIN_SCORE    = int(os.environ.get("MIN_SCORE", "60"))
LOOP_INTERVAL       = 300
MAX_APPLY_PER_CYCLE = 3
JOBS_FILE    = Path("docs/data/jobs.json")
APPLIED_FILE = Path("docs/data/applied.json")
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] {msg}", flush=True)

def call_gemini(prompt):
    if not GEMINI_KEY: return None
    try:
        import google.genai as genai
        client = genai.Client(api_key=GEMINI_KEY)
        return client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
    except Exception as e:
        log(f"Gemini: {e}")
        return None

def generate_queries():
    log("Generating queries from profile (no keywords)...")
    skills_str = ", ".join(PROFILE["skills"][:8])
    raw = call_gemini(f"10 job search queries for this candidate on LinkedIn/Indeed Germany.\nCANDIDATE: {PROFILE['name']} Berlin. Summary: {PROFILE['summary']}\nSkills: {skills_str}\nTarget: 55k+ EUR ops+AI+engineering hybrid.\nReturn ONLY JSON: [{{'query':'keywords','location':'place'}}] 10 items.")
    if raw:
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            try:
                q = json.loads(m.group())
                log(f"Gemini: {len(q)} queries")
                return [(x['query'],x['location']) for x in q]
            except: pass
    log("Using fallback queries")
    return [("operations manager AI tools","Berlin Germany"),("quality assurance engineer digital","Germany"),("logistics operations manager tech","Berlin"),("product manager internal tools","Germany remote"),("AI developer operations engineer","Berlin"),("technical operations manager","Germany hybrid"),("food technology quality operations","Berlin"),("mechanical engineer AI product","Germany"),("ops tech engineer startup","Berlin remote"),("digital transformation operations","Germany")]

def fetch_jsearch(query, location):
    if not RAPIDAPI_KEY: return []
    try:
        r = requests.get("https://jsearch.p.rapidapi.com/search",
            headers={"x-rapidapi-host":"jsearch.p.rapidapi.com","x-rapidapi-key":RAPIDAPI_KEY},
            params={"query":f"{query} {location}","page":"1","num_pages":"1","date_posted":"today"},timeout=20)
        r.raise_for_status()
        jobs=[]
        for j in r.json().get("data",[]):
            loc="Remote" if j.get("job_is_remote") else ", ".join(filter(None,[j.get("job_city",""),j.get("job_country","")]))
            src=j.get("job_publisher","")
            src="LinkedIn" if "linkedin" in src.lower() else "Indeed" if "indeed" in src.lower() else src or "JSearch"
            jobs.append({"id":str(j["job_id"]),"title":j.get("job_title",""),"company":j.get("employer_name",""),"location":loc,"salary":"","description":(j.get("job_description","") or "")[:2000],"applyUrl":j.get("job_apply_link") or j.get("job_google_link",""),"source":src,"posted":j.get("job_posted_at_datetime_utc",""),"score":None,"analysis":None,"applied":False})
        log(f"  JSearch '{query[:25]}': {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  JSearch: {e}")
        return []

def fetch_remotive():
    try:
        r=requests.get("https://remotive.com/api/remote-jobs?limit=50",timeout=15)
        r.raise_for_status()
        jobs=[]
        for j in r.json().get("jobs",[]):
            desc=re.sub(r'<[^>]+>',' ',j.get("description",""))[:2000]
            jobs.append({"id":f"rm-{j['id']}","title":j.get("title",""),"company":j.get("company_name",""),"location":"Remote","salary":j.get("salary",""),"description":desc,"applyUrl":j.get("url",""),"source":"Remotive","posted":j.get("publication_date",""),"score":None,"analysis":None,"applied":False})
        log(f"  Remotive: {len(jobs)}")
        return jobs
    except Exception as e:
        log(f"  Remotive: {e}")
        return []

def score_job(job):
    skills_str=", ".join(PROFILE["skills"][:8])
    raw=call_gemini(f"Score job. JSON only.\nJOB: {job['title']} at {job['company']} ({job['location']})\nDESC: {job['description'][:400]}\nCANDIDATE: Ops+AI Builder Berlin 22 apps. Skills: {skills_str}\nReturn: {{\"score\":0-100,\"reason\":\"<6 words\"}}")
    if raw:
        m=re.search(r'\{[^}]+\}',raw)
        if m:
            try:
                d=json.loads(m.group())
                return int(d.get("score",0)),d.get("reason","")
            except: pass
    return 0,""

def generate_cv(job):
    return call_gemini(f"ATS CV for this job. Plain text max 500 words.\nJOB: {job['title']} at {job['company']}\nDESC: {job['description'][:600]}\nCANDIDATE: {PROFILE['name']} | {PROFILE['email']} | {PROFILE['phone']} | {PROFILE['location']}\nLinkedIn: {PROFILE['linkedin']}\nSummary: {PROFILE['summary']}\nSkills: {', '.join(PROFILE['skills'])}\nInstructions: Rewrite summary for this role. Inject JD keywords naturally.")

async def apply_linkedin(page, job, cv_text):
    try:
        from playwright.async_api import async_playwright
        await page.goto("https://www.linkedin.com/login",wait_until="domcontentloaded",timeout=15000)
        await page.wait_for_timeout(1500)
        email_f=page.locator("input#username")
        if await email_f.count()>0:
            await email_f.fill(LI_EMAIL)
            await page.locator("input#password").fill(LI_PASSWORD)
            await page.locator("button[type='submit']").click()
            await page.wait_for_timeout(4000)
        await page.goto(job["applyUrl"],wait_until="domcontentloaded",timeout=20000)
        await page.wait_for_timeout(2000)
        easy=page.locator("button.jobs-apply-button, button:has-text('Easy Apply')")
        if await easy.count()==0: return False
        await easy.first.click()
        await page.wait_for_timeout(2000)
        for step in range(8):
            phone_f=page.locator("input[id*='phoneNumber'], input[name*='phone']")
            if await phone_f.count()>0:
                val=await phone_f.first.input_value()
                if not val: await phone_f.first.fill(PROFILE["phone"])
            file_f=page.locator("input[type='file']")
            if await file_f.count()>0 and cv_text:
                cv_path=Path(f"/tmp/cv_{job['id'][:6]}.txt")
                cv_path.write_text(cv_text)
                try: await file_f.first.set_input_files(str(cv_path))
                except: pass
                await page.wait_for_timeout(800)
            submit=page.locator("button:has-text('Submit application')")
            if await submit.count()>0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
                return True
            nxt=page.locator("button:has-text('Next'), button:has-text('Continue'), button:has-text('Review')")
            if await nxt.count()>0:
                await nxt.first.click()
                await page.wait_for_timeout(1500)
            else: break
    except Exception as e: log(f"  LinkedIn apply: {e}")
    return False

async def apply_generic(page, job, cv_text):
    filled=False
    fields={"input[name*='first_name' i], input[id*='firstName' i]":"Harshkumar","input[name*='last_name' i], input[id*='lastName' i]":"Patel","input[name*='full_name' i], input[id*='fullName' i]":PROFILE["name"],"input[type='email']":PROFILE["email"],"input[type='tel'], input[name*='phone' i]":PROFILE["phone"],"input[name*='city' i]":"Berlin","input[name*='location' i]":"Berlin Germany","input[name*='linkedin' i]":PROFILE["linkedin"],"input[name*='portfolio' i], input[name*='website' i]":PROFILE["portfolio"],"textarea[name*='cover' i], textarea[placeholder*='Cover' i]":f"Excited to apply for {job['title']} at {job['company']}. {PROFILE['summary'][:200]}"}
    for sel,val in fields.items():
        f=page.locator(sel)
        if await f.count()>0:
            try: await f.first.fill(val); filled=True
            except: pass
    file_f=page.locator("input[type='file']")
    if await file_f.count()>0 and cv_text:
        cv_path=Path(f"/tmp/cv_{job['id'][:6]}.txt")
        cv_path.write_text(cv_text)
        try: await file_f.first.set_input_files(str(cv_path)); filled=True
        except: pass
    if filled:
        submit=page.locator("button[type='submit'], button:has-text('Apply'), button:has-text('Submit')")
        if await submit.count()>0:
            try: await submit.first.click(); await page.wait_for_timeout(2000); return True
            except: pass
    return False

async def apply_to_job(job, cv_text):
    if not job.get("applyUrl"): return False
    log(f"  Applying: {job['title']} @ {job['company']} ({job['score']}%)")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        context=await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
        page=await context.new_page()
        try:
            await page.goto(job["applyUrl"],wait_until="domcontentloaded",timeout=25000)
            await page.wait_for_timeout(2000)
            url=page.url
            if "linkedin.com" in url and LI_PASSWORD: result=await apply_linkedin(page,job,cv_text)
            else: result=await apply_generic(page,job,cv_text)
            if result: log(f"  APPLIED: {job['title']} @ {job['company']}")
            else: log(f"  Could not auto-apply: {job['applyUrl']}")
            return result
        except Exception as e: log(f"  Apply error: {e}"); return False
        finally: await browser.close()

def load_jobs():
    if JOBS_FILE.exists():
        try: return json.loads(JOBS_FILE.read_text())
        except: pass
    return {"lastUpdated":None,"stats":{},"queries":[],"jobs":[]}

def save_jobs(data): JOBS_FILE.write_text(json.dumps(data,indent=2,ensure_ascii=False))
def load_applied():
    if APPLIED_FILE.exists():
        try: return set(json.loads(APPLIED_FILE.read_text()))
        except: pass
    return set()
def save_applied(s): APPLIED_FILE.write_text(json.dumps(list(s),indent=2))

async def run_cycle(applied_ids):
    log(f"--- Cycle {datetime.now(timezone.utc).strftime('%H:%M UTC')} ---")
    store=load_jobs()
    existing={j["id"]:j for j in store.get("jobs",[])}
    queries=generate_queries()
    new_jobs=[];seen=set()
    for query,location in queries:
        for job in fetch_jsearch(query,location):
            if job["id"] not in seen and job["id"] not in existing:
                seen.add(job["id"]); new_jobs.append(job)
        time.sleep(1)
    for job in fetch_remotive():
        if job["id"] not in seen and job["id"] not in existing:
            seen.add(job["id"]); new_jobs.append(job)
    log(f"New jobs: {len(new_jobs)}")
    applied_this=0
    for job in new_jobs:
        score,reason=score_job(job)
        job["score"]=score; job["analysis"]=reason
        time.sleep(0.3)
        if score>=MIN_SCORE and job["id"] not in applied_ids and applied_this<MAX_APPLY_PER_CYCLE:
            cv=generate_cv(job)
            ok=await apply_to_job(job,cv)
            if ok:
                job["applied"]=True; job["appliedAt"]=datetime.now(timezone.utc).isoformat()
                applied_ids.add(job["id"]); applied_this+=1; save_applied(applied_ids)
            time.sleep(2)
    all_jobs=list(existing.values())+new_jobs
    all_jobs.sort(key=lambda j:(j.get("score") or 0),reverse=True)
    all_jobs=all_jobs[:500]
    stats={"total":len(all_jobs),"new":len(new_jobs),"high_match":len([j for j in all_jobs if (j.get("score") or 0)>=70]),"applied_total":len(applied_ids),"applied_this_cycle":applied_this}
    save_jobs({"lastUpdated":datetime.now(timezone.utc).isoformat(),"agentVersion":"3.0","stats":stats,"queries":[{"query":q,"location":l} for q,l in queries],"jobs":all_jobs})
    log(f"Saved. Stats: {json.dumps(stats)}")
    for j in [x for x in all_jobs if (x.get("score") or 0)>=70][:5]:
        tag="APPLIED" if j.get("applied") else "     "
        log(f"  [{tag}] {j['score']}% - {j['title']} @ {j['company']}")
    return applied_ids

async def main():
    log("="*55)
    log("Job Copilot Agent v3.0 - Continuous Search + Auto-Apply")
    log(f"Gemini:{'OK' if GEMINI_KEY else 'MISSING'} RapidAPI:{'OK' if RAPIDAPI_KEY else 'MISSING'} LinkedIn:{'OK' if LI_PASSWORD else 'MISSING'}")
    log(f"Min score:{MIN_SCORE}% MaxApply/cycle:{MAX_APPLY_PER_CYCLE}")
    log("="*55)
    applied_ids=load_applied()
    log(f"Previously applied: {len(applied_ids)} jobs")
    cycle=0; start=time.time(); max_rt=5.5*3600
    while time.time()-start<max_rt:
        cycle+=1; log(f"=== CYCLE {cycle} ===")
        try: applied_ids=await run_cycle(applied_ids)
        except Exception as e: log(f"Cycle error: {e}")
        remaining=max_rt-(time.time()-start)
        log(f"Sleeping {LOOP_INTERVAL}s | Remaining: {remaining/3600:.1f}h")
        if remaining<LOOP_INTERVAL: break
        time.sleep(LOOP_INTERVAL)
    log("Session complete.")

if __name__=="__main__":
    asyncio.run(main())
