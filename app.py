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

    return result["choices"][0]["message"]["content"]


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


if __name__ == "__main__":
    app.run(debug=True)