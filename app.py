from flask import Flask, render_template, request, redirect, jsonify
import fitz
import uuid
import requests
import os
import re
import json
from dotenv import load_dotenv
from datetime import datetime
from rag import get_context_string, add_document, get_collection_count

app = Flask(__name__)

load_dotenv()

API_KEY = os.environ.get("API_KEY", "").strip()

# File-backed chat history
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_HISTORY_FILE = os.path.join(APP_DIR, "chat_history.json")

def load_chat_history():
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []
    return []

def save_chat_history():
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save chat history:", e)

# initialize chat history from disk
chat_history = load_chat_history()
# currently loaded session id (None if composing a fresh chat)
current_session_id = None

# Sessions storage (multiple saved chats)
SESSIONS_FILE = os.path.join(APP_DIR, "sessions.json")

def load_sessions():
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []
    return []

def save_sessions(sessions):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save sessions:", e)

def save_current_as_session():
    try:
        if not chat_history:
            return
        sessions = load_sessions()
        session_id = str(uuid.uuid4())
        # avoid creating a duplicate session if messages match an existing one
        for s in sessions:
            if s.get("messages") == chat_history:
                # move matching session to the top so it appears first in sidebar
                matching = s
                sessions.remove(s)
                sessions.insert(0, matching)
                save_sessions(sessions)
                return matching.get("id")
        # pick first user message as title or fallback to timestamp
        title = None
        for item in chat_history:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] == "You":
                title = item[1][:50]
                break
        if not title:
            title = "Chat " + datetime.now().strftime("%Y-%m-%d %I:%M %p")

        sessions.insert(0, {
            "id": session_id,
            "title": title,
            "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "messages": chat_history.copy()
        })

        save_sessions(sessions)
        return session_id
    except Exception as e:
        print("Failed to save current session:", e)


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

    context = get_context_string(user_input, k=3)
    print("RAG CONTEXT:", context)

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-web-chatbot-ckj1.onrender.com",
        "X-Title": "Ashrith AI Bot"
    }

    if context:
        system_prompt = f"""
        You are Ashrith AI.

        The user may be asking a question about an uploaded document.
        Use the uploaded document context only if it is directly relevant to the user's question.
        If the question is about chat history, personal preferences, or general knowledge,
        answer from chat history or normal knowledge instead.

        {context}

        Rules:

        1. Prefer document context only when it helps answer the current question.
        2. If the document is irrelevant, ignore it and answer from chat/general knowledge.
        3. Keep answers concise and accurate.
        4. Do not mention programming unless the user asks about programming.
        5. Do not suggest coding help.
        """

    elif detect_coding_question(user_input):

        system_prompt = f"""
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

        system_prompt = f"""
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
def extract_pdf_text(pdf_path):

    text = ""

    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text()

    return text

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

        # persist chat history to disk
        try:
            save_chat_history()
        except Exception:
            pass

    return render_template(

        "index.html",
        chat_history=chat_history,
        sessions=load_sessions()

    )

@app.route("/upload", methods=["POST"])
def upload_pdf():

    try:

        uploaded_file = request.files["document"]

        if uploaded_file.filename == "":
            return redirect("/")

        file_path = os.path.join(
            "uploads",
            uploaded_file.filename
        )

        uploaded_file.save(file_path)

        text = extract_pdf_text(file_path)

        add_document(
            str(uuid.uuid4()),
            text,
            metadata={
                "filename": uploaded_file.filename
            }
        )

        current_time = datetime.now().strftime("%I:%M %p")

        chat_history.append(
            (
                "Bot",
                f"✅ PDF uploaded successfully: {uploaded_file.filename}",
                current_time
            )
        )

        # persist upload notification
        try:
            save_chat_history()
        except Exception:
            pass

        return redirect("/")

    except Exception as e:

        current_time = datetime.now().strftime("%I:%M %p")

        chat_history.append(
            (
                "Bot",
                f"❌ Upload failed: {str(e)}",
                current_time
            )
        )

        # persist failure message
        try:
            save_chat_history()
        except Exception:
            pass

        return redirect("/")
    
@app.route("/clear")
def clear_chat():

    global chat_history

    chat_history = []

    # persist cleared state
    try:
        save_chat_history()
    except Exception:
        pass

    return redirect("/")


@app.route("/new-chat")
def new_chat():
    """Save current chat as a session and start a new chat."""
    global chat_history
    global current_session_id
    try:
        # if the current chat was loaded from an existing session, don't save it again
        if current_session_id is None:
            save_current_as_session()
    except Exception:
        pass

    chat_history = []
    current_session_id = None

    # persist cleared state for new chat
    try:
        save_chat_history()
    except Exception:
        pass

    return redirect("/")


@app.route("/load/<session_id>")
def load_session(session_id):
    """Load a saved session into the current chat view."""
    global chat_history
    sessions = load_sessions()
    for s in sessions:
        if s.get("id") == session_id:
            chat_history = s.get("messages", []).copy()
            # mark this session as the currently loaded one
            global current_session_id
            current_session_id = session_id
            try:
                save_chat_history()
            except Exception:
                pass
            break
    return redirect("/")


@app.route("/delete-session/<session_id>", methods=["POST"])
def delete_session(session_id):
    global chat_history
    global current_session_id

    sessions = load_sessions()
    sessions = [s for s in sessions if s.get("id") != session_id]
    save_sessions(sessions)

    if current_session_id == session_id:
        chat_history = []
        current_session_id = None
        try:
            save_chat_history()
        except Exception:
            pass

    return redirect("/")


@app.route("/add-document", methods=["POST"])
def add_doc():
    """Add a document to the knowledge base."""
    try:
        data = request.get_json()
        doc_id = data.get("doc_id", "")
        content = data.get("content", "")
        
        if not doc_id or not content:
            return jsonify({"error": "Missing doc_id or content"}), 400
        
        add_document(doc_id, content, metadata={"source": "web"})
        return jsonify({"success": True, "message": "Document added"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/kb-stats")
def kb_stats():
    """Get knowledge base statistics."""
    try:
        count = get_collection_count()
        return jsonify({
            "documents_count": count,
            "rag_enabled": True
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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