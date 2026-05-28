from flask import Flask, render_template, request, redirect
import requests
import os
import re
from dotenv import load_dotenv
from datetime import datetime

app = Flask(__name__)

chat_history = []

load_dotenv()

API_KEY = os.environ.get("API_KEY", "").strip()


def format_response(text):

    import re
    import html

    pattern = r"```(?:\w+)?\n?(.*?)```"

    def replace_code(match):

        code = match.group(1)

        code = html.escape(code)

        return f'''
        <button class="copy-btn" onclick="copyCode(this)">
        Copy 📋
        </button>

        <pre><code>{code}</code></pre>
        '''

    formatted = re.sub(
        pattern,
        replace_code,
        text,
        flags=re.DOTALL
    )

    code_words = [
        "#include",
        "def ",
        "public class",
        "int main",
        "scanf",
        "printf",
        "console.log",
        "function(",
        "import "
    ]

    if (
        "<pre>" not in formatted
        and any(word in text for word in code_words)
    ):

        escaped = html.escape(text)

        formatted = f'''
        <button class="copy-btn" onclick="copyCode(this)">
        Copy 📋
        </button>

        <pre><code>{escaped}</code></pre>
        '''

    return formatted


def detect_coding_question(user_input):

    coding_keywords = [

        "python",
        "java",
        "javascript",
        "html",
        "css",
        "flask",
        "django",
        "react",
        "api",
        "sql",
        "program",
        "programming",
        "code",
        "coding",
        "bug",
        "error",
        "algorithm",
        "function",
        "compiler",
        "compile",
        "c++",
        "c language",
        "machine learning",
        "ai model",
        "backend",
        "frontend",
        "database"
    ]

    user_input = user_input.lower()

    return any(
        word in user_input
        for word in coding_keywords
    )


def get_response(user_input):

    if not API_KEY:
        return "API key missing on server"

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-web-chatbot-ckj1.onrender.com",
        "X-Title": "Ashrith AI Bot"
    }

    is_coding = detect_coding_question(user_input)

    if is_coding:

        system_prompt = """
        You are Ashrith AI.

        The user is asking a coding/programming question.

        Rules:

        1. Generate correct and executable code when needed.
        2. Check syntax errors before sending.
        3. Check logic errors before sending.
        4. Add required imports or headers.
        5. Return code inside markdown code blocks.
        6. After the code, briefly explain the solution.
        7. Keep explanations simple and clear.
        """

    else:

        system_prompt = """
        You are Ashrith AI.

        The user is asking a general/non-technical question.

        Rules:

        1. Answer naturally like ChatGPT.
        2. Be friendly and conversational.
        3. Do NOT generate programming code unless explicitly asked.
        4. Give direct and human-like answers.
        """

    data = {
        "model": "openai/gpt-3.5-turbo",

        "messages": [

            {
                "role": "system",
                "content": system_prompt
            }

        ]
    }

    for sender, message, *_ in chat_history:

        role = "assistant"

        if sender == "You":
            role = "user"

        clean_message = re.sub(
            r"<.*?>",
            "",
            message
        )

        data["messages"].append({

            "role": role,
            "content": clean_message

        })

    data["messages"].append({

        "role": "user",
        "content": user_input

    })

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data
        )

        result = response.json()

        print(
            "OPENROUTER RESPONSE:",
            result,
            flush=True
        )

        if "choices" in result:

            response_text = result[
                "choices"
            ][0]["message"]["content"]

            return format_response(
                response_text
            )

        return "AI error: " + str(result)

    except Exception as e:

        return "Error: " + str(e)


@app.route("/", methods=["GET", "POST"])
def home():

    global chat_history

    if request.method == "POST":

        user_input = request.form[
            "user_input"
        ]

        response = get_response(
            user_input
        )

        current_time = datetime.now(
        ).strftime("%I:%M %p")

        chat_history.append(

            (
                "You",
                user_input,
                current_time
            )

        )

        chat_history.append(

            (
                "Bot",
                response,
                current_time
            )

        )

    return render_template(

        "index.html",
        chat_history=chat_history

    )


@app.route("/clear")
def clear_chat():

    global chat_history

    chat_history = []

    return redirect("/")


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )