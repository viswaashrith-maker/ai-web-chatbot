from flask import Flask, render_template, request, redirect
import requests

app = Flask(__name__)

chat_history = []

API_KEY = "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"


def get_response(user_input):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    print(result)  # this shows real API response in PyCharm terminal

    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        return "AI error: " + str(result)


@app.route("/", methods=["GET", "POST"])
def home():
    global chat_history

    if request.method == "POST":
        user_input = request.form["user_input"].lower()
        response = get_response(user_input)

        chat_history.append(("You", user_input))
        chat_history.append(("Bot", response))

    return render_template("index.html", chat_history=chat_history)


@app.route("/clear")
def clear_chat():
    global chat_history
    chat_history = []
    return redirect("/")
import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)