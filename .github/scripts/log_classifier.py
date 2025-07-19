import os, re, subprocess, openai, requests

REPO = os.getenv("GITHUB_REPOSITORY")
PR = os.getenv("GITHUB_REF").split("/")[-1]
TOKEN = os.getenv("GITHUB_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Regex for log detection
LOG_PATTERN = re.compile(r"(log|logger|LOG|LOGGER|logging|LOGGING)\.(info|warn|warning)\((.*?)\)", re.DOTALL)

# Production-grade prompt
prompt_header = """You are a Production-Grade Log Classification Assistant, trained using best practices from Netflix, Google SRE, Uber Observability, and OWASP Security Guidelines.

### MISSION:
Improve log quality and reduce operational noise by:
- Promoting only logs that are useful for debugging, auditing, or compliance
- Demoting all others to DEBUG level to reduce cost and clutter

...

Now classify the following logs using this framework. Also, mention one line reason for each classification.
"""

def get_changed_files():
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD~1'], capture_output=True, text=True)
    return [f for f in result.stdout.strip().split('\n') if f.endswith('.py') and os.path.isfile(f)]

def extract_logs(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    return LOG_PATTERN.findall(code)

def classify_logs(logs):
    log_lines = [f"{a}.{b}({c.strip()})" for a, b, c in logs]
    if not log_lines:
        return []

    logs_to_classify = "\n".join(f"Log: {l}\nOccurrence: 45%" for l in log_lines)
    full_prompt = f"{prompt_header}\n\n{logs_to_classify}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2
        )
        print("🔍 GPT RESPONSE:\n", text)
        text = response['choices'][0]['message']['content']
        not_useful = []
        for line in text.splitlines():
            if "Classification:" in line and "NOT USEFUL" in line:
                idx = text.splitlines().index(line)
                log_line = text.splitlines()[idx - 2].replace("Log: ", "").strip()
                not_useful.append(log_line)
        return not_useful
    except Exception as e:
        print("Error during OpenAI call:", e)
        return []

def comment_on_pr(lines):
    if not lines:
        return
    body = "### 🚫 The following logs are classified as **NOT USEFUL**:\n"
    body += "\n".join(f"- `{l}`" for l in lines)
    url = f"https://api.github.com/repos/{REPO}/issues/{PR}/comments"
    headers = {'Authorization': f'token {TOKEN}'}
    requests.post(url, headers=headers, json={"body": body})

def main():
    files = get_changed_files()
    all_logs = []
    for f in files:
        all_logs.extend(extract_logs(f))

    not_useful = classify_logs(all_logs)
    comment_on_pr(not_useful)

if __name__ == "__main__":
    main()
