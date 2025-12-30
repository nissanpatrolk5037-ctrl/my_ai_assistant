import customtkinter as ctk
from datetime import datetime
import threading
import time
import math
from task_automation import groq_answer as groq


# =========================
# GLOBAL THEME
# =========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0f1115"
PANEL = "#171a21"
PANEL_DEEP = "#12141a"
GLASS = "#1d2028"

BORDER_SOFT = "#2a2e39"
BORDER_GLOW = "#4f5bff"

TEXT_MAIN = "#e6e8ee"
TEXT_MUTED = "#9aa0ad"
ACCENT = "#5b6cff"


# =========================
# MAIN APP
# =========================

class AestheticApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Core")
        self.geometry("980x620")
        self.configure(fg_color=BG)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._build_left_panel()
        self._build_right_panel()
        self._build_input()

        threading.Thread(target=self._clock_loop, daemon=True).start()
        threading.Thread(target=self._time_glow_loop, daemon=True).start()
        threading.Thread(target=self._button_breathing_loop, daemon=True).start()

    # =========================
    # LEFT PANEL
    # =========================

    def _build_left_panel(self):
        self.left = ctk.CTkFrame(
            self,
            corner_radius=30,
            fg_color=PANEL,
            border_width=1,
            border_color=BORDER_SOFT
        )
        self.left.grid(row=0, column=0, padx=22, pady=22, sticky="nsew")
        self.left.grid_rowconfigure(1, weight=1)

        # Time Card
        self.time_card = ctk.CTkFrame(
            self.left,
            corner_radius=24,
            height=120,
            fg_color=GLASS,
            border_width=1,
            border_color=BORDER_SOFT
        )
        self.time_card.pack(fill="x", padx=16, pady=(16, 12))

        self.time_label = ctk.CTkLabel(
            self.time_card,
            text="--:--:--",
            font=("Segoe UI Variable", 30, "bold"),
            text_color=TEXT_MAIN
        )
        self.time_label.pack(pady=26)

        # Editable Intelligence Pad
        self.left_textbox = ctk.CTkTextbox(
            self.left,
            corner_radius=22,
            font=("Segoe UI", 14),
            wrap="word",
            fg_color=PANEL_DEEP,
            border_width=1,
            border_color=BORDER_SOFT
        )
        self.left_textbox.pack(fill="both", expand=True, padx=16, pady=(8, 10))

        # Summarize Button
        self.summarize_button = ctk.CTkButton(
            self.left,
            text="Summarize",
            height=48,
            corner_radius=24,
            fg_color=PANEL_DEEP,
            hover_color=GLASS,
            border_width=1,
            border_color=BORDER_SOFT,
            font=("Segoe UI Variable", 16, "bold"),
            command=self.summarize_text
        )
        self.summarize_button.pack(fill="x", padx=16, pady=(6, 16))

    # =========================
    # RIGHT PANEL
    # =========================

    def _build_right_panel(self):
        self.right = ctk.CTkFrame(
            self,
            corner_radius=30,
            fg_color=PANEL,
            border_width=1,
            border_color=BORDER_SOFT
        )
        self.right.grid(row=0, column=1, padx=22, pady=22, sticky="nsew")

        self.output_box = ctk.CTkTextbox(
            self.right,
            corner_radius=24,
            font=("Consolas", 15),
            wrap="word",
            fg_color=PANEL_DEEP,
            border_width=1,
            border_color=BORDER_SOFT
        )
        self.output_box.pack(fill="both", expand=True, padx=18, pady=18)
        self.output_box.insert("end", "AI Core online.\n\n")
        self.output_box.configure(state="disabled")

    # =========================
    # INPUT BAR
    # =========================

    def _build_input(self):
        self.input_box = ctk.CTkEntry(
            self,
            placeholder_text="Type a command…",
            height=44,
            corner_radius=22,
            font=("Segoe UI Variable", 16),
            fg_color=PANEL,
            border_width=1,
            border_color=BORDER_SOFT,
            placeholder_text_color=TEXT_MUTED
        )
        self.input_box.grid(
            row=1, column=0, columnspan=2,
            padx=22, pady=(0, 22), sticky="ew"
        )
        self.input_box.bind("<Return>", self.on_enter)

    # =========================
    # ANIMATIONS
    # =========================

    def _clock_loop(self):
        while self.winfo_exists():
            now = datetime.now().strftime("%I:%M:%S %p")
            self.time_label.configure(text=f"⏱ {now}")
            time.sleep(1)

    def _time_glow_loop(self):
        t = 0.0
        while self.winfo_exists():
            glow = int(160 + 40 * math.sin(t))
            color = f"#{glow:02x}{glow:02x}{glow+10:02x}"
            self.time_label.configure(text_color=color)
            t += 0.06
            time.sleep(0.06)

    def _button_breathing_loop(self):
        t = 0.0
        while self.winfo_exists():
            val = int(28 + 8 * math.sin(t))
            color = f"#{val:02x}{val:02x}{val+6:02x}"
            self.summarize_button.configure(fg_color=color)
            t += 0.04
            time.sleep(0.05)

    # =========================
    # INTERACTION
    # =========================

    def on_enter(self, event=None):
        text = self.input_box.get().strip()
        if not text:
            return
        self.input_box.delete(0, "end")
        threading.Thread(target=self._handle_ai_response, args=(text,), daemon=True).start()

    def _handle_ai_response(self, text):
        self._append_text(f"> {text}\n", fast=True)
        response = groq("", text)
        self._append_text(f"\n\n\n{response}\n\n\n")

    def _append_text(self, message, fast=False):
        self.output_box.configure(state="normal")
        delay = 0.002 if fast else 0.01

        for char in message:
            self.output_box.insert("end", char)
            self.output_box.see("end")
            time.sleep(delay if char not in ".!?" else delay * 4)

        self.output_box.configure(state="disabled")

    def summarize_text(self):
        content = self.left_textbox.get("1.0", "end").strip()
        if not content:
            return

        def task():
            result = f"{groq("Summarize the following text clearly and concisely:", content)}"
            self.left_textbox.delete("1.0", "end")
            self.left_textbox.insert("1.0", result)

        threading.Thread(target=task, daemon=True).start()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = AestheticApp()
    app.mainloop()
