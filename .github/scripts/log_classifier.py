import os, re, subprocess, openai, requests

REPO = os.getenv("GITHUB_REPOSITORY")
PR = os.getenv("GITHUB_REF").split("/")[-1]
TOKEN = os.getenv("GITHUB_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

LOG_REGEX = re.compile(r"(log|logger|LOG|LOGGER|logging|LOGGING)\.(info|warn|warning)\((.*?)\)", re.DOTALL)

prompt_template = """
Classify these logs as USEFUL or NOT USEFUL. Return only NOT USEFUL logs in JSON array format.
Logs:
{logs}
"""

def get_changed_files():
    result = subprocess.run(['git', 'diff', '--name-only', 'origin/main'], capture_output=True, text=True)
    return [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]

def extract_logs(path):
    try:
        code = open(path, encoding='utf-8', errors='ignore').read()
        return LOG_REGEX.findall(code)
    except:
        return []

def classify(logs):
    code_logs = [f"{a}.{b}({c.strip()})" for a, b, c in logs]
    if not code_logs: return []

    prompt = prompt_template.format(logs="\n".join(code_logs))
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    try:
        return eval(resp['choices'][0]['message']['content'].strip())
    except:
        return []

def comment_on_pr(lines):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR}/comments"
    headers = {'Authorization': f'token {TOKEN}'}
    body = "### 🚫 The following logs are NOT USEFUL:\n" + "\n".join(f"- `{l}`" for l in lines)
    requests.post(url, headers=headers, json={"body": body})

def main():
    files = get_changed_files()
    logs = []
    for f in files:
        logs.extend(extract_logs(f))
    not_useful = classify(logs)
    if not_useful:
        comment_on_pr(not_useful)

if __name__ == "__main__":
    main()
