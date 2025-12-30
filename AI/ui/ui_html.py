import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, QUrl, Qt
from groq import Groq
from typing import Optional, Any
import re

API_KEY = "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"

def _print_err(msg: str):
    print(f"[Groq Error] {msg}", file=sys.stderr)

def _get_groq_client() -> Optional[Any]:
    if Groq is None:
        _print_err("Groq library not available.")
        return None
    try:
        return Groq(api_key=API_KEY)
    except Exception as e:
        _print_err(f"Failed to initialize Groq client: {e}")
        return None

def groq_call(instructions: str, query: str = None):
    client = _get_groq_client()
    if client is None:
        return "Groq client not available."
    content = instructions if query is None else f"{instructions}\n\n{query}"
    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-guard-4-12b"
    ]
    for model in models:
        try:
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": content}],
                model=model,
                stream=False,
            )
            text = (chat.choices[0].message.content or "").replace("**", "")
            return text
        except Exception as e:
            e_str = str(e)
            if re.search("Rate limit reached for model", e_str):
                print(f"❌ Rate limit reached for {model}, switching...")
                continue
            print(f"[Groq Error] {e_str}")
            return None
    print("⚠️ All models exhausted. Try again later.")
    return None

def groq_answer(instructions: str, query: Optional[str] = None) -> str:
    return groq_call(instructions, query)

# ------------------ Your LLM Bridge ------------------
class LLMBridge(QObject):
    @pyqtSlot(str, result=str)
    def get_response(self, prompt):
        # Here, call your actual LLM
        # For example, local LLM or API call
        # Example placeholder:
        response = groq_answer(prompt)
        return response

# ------------------ Setup PyQt ------------------
app = QApplication(sys.argv)
view = QWebEngineView()

html_file = os.path.abspath("e:/AI/ui/index.html")
view.load(QUrl.fromLocalFile(html_file))
view.setFixedSize(600, 600)
view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
view.setFocus()

# ------------------ WebChannel ------------------
channel = QWebChannel()
bridge = LLMBridge()
channel.registerObject("bridge", bridge)
view.page().setWebChannel(channel)

view.show()
sys.exit(app.exec())
