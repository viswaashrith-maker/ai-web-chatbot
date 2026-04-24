from flask import Flask, render_template, request, redirect
app = Flask(__name__)
chat_history = []

def get_response(user_input):
    responses = {
        'hi': 'Hello',
        'hello': 'Hello',
        'how are you': 'i am fine what about you',
        'what is your name': 'i am Ashrith bot',
        'i am fine': 'how can i help you',
        'bye': 'Goodbye'
    }

    for key in responses:
        if key in user_input:
            return responses[key]

    return "sorry i dont understand"

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