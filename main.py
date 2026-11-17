import os
import re
import base64
import requests
import ollama
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
REPO_NAME = os.environ.get("REPO_NAME")

def sanitize_title(title):
    clean = re.sub(r'[^\w\s-]', '', title).strip().lower()
    return clean.replace(' ', '_')

def generate_approach_markdown(problem_num, problem_title, question_text, user_solution):
    print("\n🤖 Gemma 2 is generating approach.md in-memory...")
    
    prompt = f"""You are an expert software engineer and technical writer documenting a LeetCode solution.

TASK: Generate a highly detailed, clean Markdown file following the EXACT template structure below.
CRITICAL RULES: 
1. Output ONLY the raw Markdown template. DO NOT include conversational text.
2. Use LaTeX for math notation ($ for inline, $$ for block formulas).

# Problem {problem_num}: {problem_title}

## Intuition
[Provide a brief paragraph explaining the core idea or the "aha!" moment behind the algorithm.]

## Approach
[Provide a highly detailed, numbered breakdown of the algorithm. Do not just translate the code to English; explain the underlying logic, how the data structures are used, and why this approach is efficient.]

## Complexity Analysis
* **Time Complexity:** [State complexity, e.g., $O(N)$]
    * [Detailed explanation of why]
* **Space Complexity:** [State complexity, e.g., $O(1)$]
    * [Detailed explanation of why]

INPUT DATA TO ANALYZE:
Problem Context: {question_text}
Code Solution: {user_solution}
"""
    try:
        response = ollama.chat(model='gemma2:2b', messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].strip()
        
        # Guardrail: If the model appends the input data text, cut it out programmatically
        if "INPUT DATA TO ANALYZE" in content:
            content = content.split("INPUT DATA TO ANALYZE")[0].strip()
        elif "Input Data:" in content:
            content = content.split("Input Data:")[0].strip()
            
        return content
        
    except Exception as e:
        print(f"❌ Error talking to Ollama: {e}")
        return None

def upload_to_github_api(repo_path, file_content, commit_message):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    data = {
        "message": commit_message,
        "content": encoded_content
    }
    
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [201, 200]:
        print(f"✅ Successfully uploaded: {repo_path}")
    else:
        print(f"❌ Failed to upload {repo_path}. Response: {response.json()}")

def main():
    if not all([GITHUB_TOKEN, GITHUB_USERNAME, REPO_NAME]):
        print("❌ Error: Missing configuration credentials. Please check your .env file setup.")
        return

    print("=== Secure Zero-Storage LeetCode Pipeline ===")
    
    day = input("Enter Day Number (e.g., 1): ").strip()
    prob_num = input("Enter Problem Number (e.g., 3354): ").strip()
    prob_title = input("Enter Problem Title (e.g., Make Array Elements Equal to Zero): ").strip()
    
    print("\nPaste LeetCode Question Context (Press Enter, then Ctrl+Z and Enter to finish):")
    question_lines = []
    try:
        while True: question_lines.append(input())
    except EOFError: pass
    question_text = "\n".join(question_lines)
    
    print("\nPaste your solution.py Code (Press Enter, then Ctrl+Z and Enter to finish):")
    solution_lines = []
    try:
        while True: solution_lines.append(input())
    except EOFError: pass
    user_solution = "\n".join(solution_lines)

    # FIXED FOLDER PATH: Strictly starts with "Problems/"
    folder_name = f"{day}. {prob_num}_{sanitize_title(prob_title)}"
    remote_approach_path = f"Problems/{folder_name}/approach.md"
    remote_solution_path = f"Problems/{folder_name}/solution.py"

    markdown_content = generate_approach_markdown(prob_num, prob_title, question_text, user_solution)
    if not markdown_content:
        return

    print("\n🚀 Pushing directly to remote origin via cloud API...")
    
    upload_to_github_api(remote_approach_path, markdown_content, "Create approach.md")
    
    solution_msg = f"Day {day}: solved {prob_num} - {prob_title}"
    upload_to_github_api(remote_solution_path, user_solution, solution_msg)
    
    print("\n🎉 Complete!")

if __name__ == "__main__":
    main()