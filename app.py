from flask import Flask, render_template, request, redirect
import requests
import os

app = Flask(__name__)

chat_history = []

API_KEY = os.environ.get("API_KEY", "").strip()


def get_response(user_input):
    if not API_KEY:
        return "API key missing on server"

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-web-chatbot-ckj1.onrender.com",
        "X-Title": "Ashrith AI Bot"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    print("API KEY EXISTS:", bool(API_KEY), flush=True)
    print("API KEY START:", API_KEY[:6], flush=True)
    print("OPENROUTER RESPONSE:", result, flush=True)

    if "choices" in result:
        return result["choices"][0]["message"]["content"]

    return "AI error: " + str(result)


@app.route("/", methods=["GET", "POST"])
def home():
    global chat_history

    if request.method == "POST":
        user_input = request.form["user_input"]
        response = get_response(user_input)

        chat_history.append(("You", user_input))
        chat_history.append(("Bot", response))

    return render_template("index.html", chat_history=chat_history)


@app.route("/clear")
def clear_chat():
    global chat_history
    chat_history = []
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)