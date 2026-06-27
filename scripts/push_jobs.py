import os, json, base64, urllib.request
from datetime import datetime, timezone

token = os.environ.get('GITHUB_TOKEN', '')
repo = os.environ.get('GITHUB_REPOSITORY', 'berlinkitchen123-blip/career-ops')
path = 'docs/data/jobs.json'

if not token:
    print('No GITHUB_TOKEN'); exit(0)
if not os.path.exists(path):
    print('No jobs.json'); exit(0)

with open(path, 'rb') as f:
    raw = f.read()

data = json.loads(raw)
print(f"jobs.json: {data.get('stats', {}).get('total', 0)} jobs, updated {data.get('lastUpdated','?')[:16]}")

content_b64 = base64.b64encode(raw).decode()

def api(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method,
        headers={'Authorization': f'token {token}', 'Content-Type': 'application/json', 'Accept': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read())

# Get current SHA
try:
    current = api('GET', f'https://api.github.com/repos/{repo}/contents/{path}')
    sha = current['sha']
    print(f'Remote SHA: {sha[:8]}')
except Exception as e:
    print(f'Get SHA error: {e}'); exit(1)

# Push update
msg = f'Jobs: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}'
body = json.dumps({'message': msg, 'content': content_b64, 'sha': sha}).encode()
try:
    result = api('PUT', f'https://api.github.com/repos/{repo}/contents/{path}', body)
    print(f'Pushed! Commit: {result["commit"]["sha"][:8]}')
except Exception as e:
    print(f'Push error: {e}')
