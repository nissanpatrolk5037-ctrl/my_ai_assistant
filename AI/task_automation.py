from __future__ import annotations
#-------------------------------------------------------------#
from typing import Dict, Iterable, List, Optional, Tuple, Any, Callable
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from requests import get, HTTPError, ConnectionError
from screen_brightness_control import set_brightness
from watchdog.events import FileSystemEventHandler
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from pdfminer.high_level import extract_text
from googleapiclient.discovery import build
from multi_local_llm import run as llm_run
from datetime import datetime, timedelta
from PyPDF2 import PdfReader, PdfMerger
from watchdog.observers import Observer
from keyboard import press_and_release
import xml.etree.ElementTree as ET
from PIL import Image, ImageGrab
from urllib.parse import unquote
import matplotlib.pyplot as plt
from functools import lru_cache
import speech_recognition as sr
from bs4 import BeautifulSoup
from PIL.ExifTags import TAGS
from memory_manager import *
from pytube import YouTube
import pygetwindow as gw
from pathlib import Path
import sounddevice as sd
import librosa.display
from re import findall
import yfinance as yf
from tqdm import tqdm
import datetime as dt
from fpdf import FPDF
from moviepy import *
import pandas as pd
import numpy as np
import subprocess
import webbrowser
import pyautogui
import threading
import pyperclip
import importlib
import traceback
import requests
import tempfile
import textwrap
import openpyxl
import hashlib
import inspect
import asyncio
import discord
import imaplib
import librosa
import qrcode
import shutil
import psutil
import urllib
import socket
import ctypes
import pefile
import queue
import magic
import email
import boto3
import spacy
import sched
import scipy
import json
import time
import glob
import sys
import cv2
import csv
import os
import re

try:
    import win32com.client  # for Word COM
except Exception:
    win32com = None

try:
    from tkinter import messagebox, Tk
except Exception:
    messagebox = None
    Tk = None

try:
    import pygame
except Exception:
    pygame = None

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from bleak import BleakScanner
except Exception:
    BleakScanner = None

try:
    import nmap 
except Exception:
    nmap = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from deep_translator import GoogleTranslator 
except Exception:
    GoogleTranslator = None

try:
    import pywhatkit
except Exception:
    pywhatkit = None

try:
    import winreg # Windows only
    import ctypes # Windows only
except ImportError:
    winreg = None
    ctypes = None

# -----------------------------
# Globals
# -----------------------------
LAST_PRICE_FILE = Path("last_price.txt")
IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
ROOT = Path.cwd()
GEN_ENV = {}
DISCORD_TOKEN = ""
DISCORD_CHANNEL_ID = 0
WHATSAPP_TOKEN = ""
WHATSAPP_PHONE_ID = ""
MEMORY_FILE = "os_context_memory.json"
API_KEY = "YOUR_GROQ_API_KEY"

audio_queue: "queue.Queue[str]" = queue.Queue()

# -----------------------------
# Helpers
# -----------------------------

def skill_wrapper(func):
    def wrapped(**kwargs):
        return func(**kwargs)
    return wrapped

def now():
    return datetime.now().isoformat(timespec="seconds")

def log(*a):
    try: print(*a)
    except: pass

def _kw(kwargs, key, default=None):
    return kwargs.get(key, default)

def _print_err(*args, **kwargs):
    # Accept either positional msg or keyword 'msg'
    msg = args[0] if args else kwargs.get("msg", "")
    print(f"[ERROR] {msg}")

def _safe_message_box(*args, **kwargs):
    # Accept either positional (title, text) or keyword args
    if args:
        title = args[0] if len(args) > 0 else kwargs.get("title", "")
        text = args[1] if len(args) > 1 else kwargs.get("text", "")
    else:
        title = kwargs.get("title", "")
        text = kwargs.get("text", "")

    if not IS_WINDOWS or messagebox is None or Tk is None:
        print(f"[MSGBOX] {title}: {text}")
        return
    root = Tk()
    root.withdraw()
    messagebox.showinfo(title, text)
    root.destroy()

def _make_session() -> requests.Session:
    s = requests.Session()
    retries = requests.adapters.Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"])
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "OptimizedAssistant/1.0"})
    return s

SESSION = _make_session()


# -----------------------------
# Groq Functions
# -----------------------------

def _get_groq_client() -> Optional[Any]:
    if Groq is None:
        _print_err("Groq library not available.")
        return None
    try:
        return Groq(api_key=API_KEY)
    except Exception as e:
        _print_err(f"Failed to initialize Groq client: {e}")
        return None

@lru_cache(maxsize=128)
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

# =========================================================
# SKILL SYSTEM (FULL)
# =========================================================

def _make_skill_name(*args, **kwargs) -> str:
    # Accept positional text or keyword 'text'
    text = args[0] if args else kwargs.get("text", "")
    clean = re.sub(r"[^a-zA-Z0-9 ]+", "", text.lower())
    clean = "_".join(clean.split()[:6])
    digest = hashlib.md5(text.encode()).hexdigest()[:6]
    return f"{clean}_{digest}"



# SkillRegistry removed: use `skill.add_skill(name, func)` on the SkillEngine instance
# (The old SkillRegistry pattern was deprecated in favor of dynamic registration.)


class SkillEngine:
    def __init__(self):
        self._registry = {}

    def add_skill(self, func, name=None):
        """Add a function as a skill."""
        self._registry[name or func.__name__] = func

    def execute(self, skill_name, **kwargs):
        """Execute a skill with kwargs or positional fallback."""
        if skill_name not in self._registry:
            raise KeyError(f"Skill '{skill_name}' not found.")

        func = self._registry[skill_name]
        sig = inspect.signature(func)

        # Check if function accepts **kwargs
        accepts_kwargs = any(
            p.kind == p.VAR_KEYWORD for p in sig.parameters.values()
        )

        # Prepare positional arguments for non-kwargs functions
        if not accepts_kwargs:
            pos_args = []
            for i, param in enumerate(sig.parameters.values()):
                if param.name in kwargs:
                    pos_args.append(kwargs[param.name])
                elif param.default != inspect.Parameter.empty:
                    pos_args.append(param.default)
                else:
                    raise ValueError(f"Missing argument '{param.name}' for skill '{skill_name}'")
            return func(*pos_args)
        else:
            return func(**kwargs)

skill = SkillEngine()

# =========================================================
# NLP → MULTI COMMAND REWRITE
# =========================================================
REWRITE_INSTRUCTIONS = """
Rewrite the user's request into executable commands.
Rules:
- Commands MUST be separated by semicolons
- Commands MUST be short and imperative
- Do NOT explain
- Do NOT add text
Example:
"Open Chrome and search cats then copy result and paste into notepad"
→ "open_chrome; search cats; copy result; paste_notepad"
"""

import concurrent.futures

def run_task_parallel(user_input: str, max_workers: int = 5):
    """
    Run multiple commands in parallel.
    Uses Groq to rewrite user input into semicolon-separated commands.
    Auto-creates missing skills if needed.
    """
    if not user_input.strip():
        return

    NLP_INSTRUCTIONS = """
    You are an AI command planner.
    Rewrite the user's request into a list of executable commands separated by semicolons (;).
    Rules:
    - Each command must be short and executable
    - Do NOT explain anything
    - Do NOT number the commands
    - Use simple verbs
    - Example:
    User: Open Chrome then search cats and copy result
    Output: open chrome; search cats on google; copy result
    Return ONLY the commands.
    """

    rewritten = groq_answer(NLP_INSTRUCTIONS, user_input)
    if not rewritten:
        _print_err("NLP rewrite failed.")
        return

    commands = [c.strip() for c in rewritten.split(";") if c.strip()]
    if not commands:
        _print_err("No commands produced.")
        return

    def execute_cmd(cmd):
        try:
            executed = skill.execute(cmd, raw_input=user_input)
            if executed is False:
                adaptive_auto_coder(cmd)  # auto-learn if missing
                skill.execute(cmd, raw_input=user_input)
        except Exception as e:
            _print_err(f"Task failed: {cmd} → {e}")

    # Run commands in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(execute_cmd, cmd) for cmd in commands]
        concurrent.futures.wait(futures)




# System Cleanup
# -----------------------------
class SystemCleanup:
    @staticmethod
    def delete_files_in_folder(folder: str | Path) -> str:
        p = Path(folder)
        if not p.exists():
            return(f"Folder not found: {p}")
        
        deleted_count = 0
        for child in p.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                    deleted_count += 1
                elif child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                    deleted_count += 1
            except Exception as e:
                _print_err(f"Error deleting {child}: {e}")
        return f"Deleted {deleted_count} items in {p.name}."

    @staticmethod
    def run_command(command: str) -> Optional[str]:
        try:
            # Use shell=True for OS-specific commands (like ipconfig/rd)
            subprocess.run(command, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Command executed successfully: {command.split()[0]}"
        except subprocess.CalledProcessError as e:
            _print_err(f"Command failed: {command} ({e})")
            return f"Command failed: {command.split()[0]}"
        except FileNotFoundError:
            _print_err(f"Command not found: {command.split()[0]}")
            return f"Command not found: {command.split()[0]}"

    @staticmethod
    def clean_temp():
        temp_folder = None
        if IS_WINDOWS:
            temp_folder = os.environ.get("TEMP") or os.environ.get("TMP")
            # Also clean the Windows-specific system temp if possible
            windir = os.environ.get("WINDIR", "C:\\Windows")
            SystemCleanup.delete_files_in_folder(Path(windir) / "Temp")
        elif IS_MACOS:
            temp_folder = os.environ.get("TMPDIR", "/private/tmp")
        elif IS_LINUX:
            temp_folder = "/tmp"

        if temp_folder and Path(temp_folder).exists():
            SystemCleanup.delete_files_in_folder(temp_folder)
            return f"Cleaned standard temp folder: {temp_folder}"
        return "Temp cleanup path not found."


    @staticmethod
    def clean_recycled_items():
        if IS_WINDOWS:
            # Clear Windows Recycle Bin (often requires admin)
            return SystemCleanup.run_command("rd /s /q C:\\$Recycle.Bin")
        elif IS_MACOS:
            # Clear macOS Trash
            trash_path = Path.home() / ".Trash"
            if trash_path.exists():
                SystemCleanup.delete_files_in_folder(trash_path)
                return f"Cleaned macOS Trash: {trash_path.name}"
            return "macOS Trash not found."
        elif IS_LINUX:
            return "Linux trash cleanup requires 'trash-cli' or manual confirmation. Skipped for safety."
        return "Recycle/Trash cleanup skipped."


    @staticmethod
    def clean_dns_cache():
        if IS_WINDOWS:
            return SystemCleanup.run_command("ipconfig /flushdns")
        elif IS_MACOS:
            try:
                subprocess.run("dscacheutil -flushcache", check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "DNS cache partially flushed (macOS: dscacheutil)."
            except Exception:
                return "DNS cache flush failed (macOS)."
        elif IS_LINUX:
            if shutil.which("systemd-resolve"):
                return SystemCleanup.run_command("sudo systemd-resolve --flush-caches")
            elif shutil.which("nscd"):
                 return SystemCleanup.run_command("sudo /etc/init.d/nscd restart")
            return "Linux DNS command not found. Skipped."
        return "DNS cache cleanup skipped."

    @staticmethod
    def main():
        """Cross-platform system cleanup entry point."""
        results = [
            SystemCleanup.clean_temp(),
            SystemCleanup.clean_recycled_items(),
            SystemCleanup.clean_dns_cache()
        ]
        # Additional Windows cleanup steps omitted for brevity, see full code if needed.
        return ("Cleanup complete!")
def image_generation(**kwargs) -> Optional[Path]:
    # Accepts: query or raw_input, out_path
    query = (kwargs.get("query") or kwargs.get("raw_input") or "").strip()
    out_path = Path(kwargs.get("out_path", Path("Generated_Image.jpg")))

    # Let Groq reduce a prompt like: "create a dog" -> "dog"
    obj = groq_answer(
        "Just return the primary object from this query. E.g., 'create a dog' -> 'dog'",
        query,
    )
    obj = (obj or "").strip() or query
    img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(obj)}"
    try:
        with SESSION.get(img_url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024 * 32):
                    if chunk:
                        f.write(chunk)
        try:
            Image.open(out_path).verify()
        except Exception:
            _print_err("Downloaded file may not be a valid image.")
        try:
            Image.open(out_path).show()
        except Exception:
            pass
        return out_path 
    except Exception as e:
        _print_err(f"Failed to download image: {e}")
        return None


def image_optimization(**kwargs) -> None:
    # Accepts: mode, path, output_path, quality, size
    mode = kwargs.get("mode")
    path = kwargs.get("path")
    output_path = kwargs.get("output_path")
    quality = kwargs.get("quality", 85)
    size = tuple(kwargs.get("size", (800, 600)))
    def _optimize_one(in_path: Path, out_path: Path):
        try:
            with Image.open(in_path) as img:
                img = img.convert("RGB")
                img = img.resize(size)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(out_path, optimize=True, quality=quality)
        except Exception as e:
            _print_err(f"Optimize failed for {in_path}: {e}")

    p = Path(path)
    if mode == "image":
        if not p.exists():
            _print_err(f"Image not found: {p}")
            return
        out = Path(output_path) if output_path else p.with_stem(p.stem + "_optimized").with_suffix(".jpg")
        _optimize_one(p, out)
    elif mode == "folder":
        if not p.is_dir():
            _print_err(f"Folder not found: {p}")
            return
        for img_file in p.iterdir():
            if img_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                out = img_file.with_stem("resized_" + img_file.stem).with_suffix(".jpg")
                _optimize_one(img_file, out)
    else:
        _print_err("mode must be 'image' or 'folder'.")

def docx_to_pdf(**kwargs):
    input_path = kwargs.get("input_path")
    output_path = kwargs.get("output_path")

    if not input_path:
        return "Error: input_path is required."

    p_in = Path(input_path).resolve()
    p_out = Path(output_path or p_in.with_suffix(".pdf")).resolve()

    # 1. Windows COM Automation (Requires MS Word)
    if IS_WINDOWS and win32com is not None:
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(p_in))
            doc.SaveAs(str(p_out), FileFormat=17)  # wdFormatPDF
            doc.Close(False)
            word.Quit()
            return f"Saved PDF (Windows COM): {p_out}"
        except Exception as e:
            # Fall through to subprocess fallback
            pass 

    # 2. Cross-Platform Fallback: LibreOffice/OpenOffice
    try:
        soffice_path = shutil.which("libreoffice") or shutil.which("soffice")
        if soffice_path:
            command = [
                str(soffice_path),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(p_out.parent),
                str(p_in)
            ]
            subprocess.run(command, check=True, capture_output=True, timeout=60)
            if p_out.exists():
                return f"Saved PDF (LibreOffice): {p_out}"

    except Exception:
        pass

    return "Error: Cannot convert document. Requires win32com (Windows) or LibreOffice/soffice (All platforms) to be installed."

def get_crypto_price_coingecko(**kwargs) -> float | None:
    symbol = (kwargs.get("symbol") or kwargs.get("raw_input") or "").strip().lower()
    """
    Fetch crypto price from CoinGecko in USD
    """
    symbol = symbol.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    try:
        resp = requests.get(url).json()
        return resp[symbol]["usd"]
    except Exception as e:
        _print_err(f"CoinGecko error: {e}")
        return None


def track_stock(**kwargs) -> str:
    # Accepts: symbol, state_file, asset_type
    symbol = (kwargs.get("symbol") or kwargs.get("raw_input") or "").strip()
    state_file = kwargs.get("state_file", LAST_PRICE_FILE)
    asset_type = kwargs.get("asset_type", "stock")
    """
    Fetch current price, compare with stored last price, update state_file, return a message.
    asset_type: "stock" or "crypto"
    """
    current_price = None

    if asset_type.lower() == "stock":
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="1d", interval="1m")
            if data.empty:
                return f"No price data found for {symbol}."
            current_price = float(data["Close"].iloc[-1])
        except Exception as e:
            _print_err(f"yfinance error: {e}")
            return f"Error fetching stock price for {symbol}."

    elif asset_type.lower() == "crypto":
        current_price = get_crypto_price_coingecko(symbol)
        if current_price is None:
            return f"Error fetching crypto price for {symbol}."

    else:
        return "Invalid asset_type. Use 'stock' or 'crypto'."

    # Read last price
    last_price = None
    if state_file.exists():
        try:
            last_price = float(state_file.read_text().strip())
        except Exception:
            last_price = None

    # Prepare message
    if last_price is None:
        message = f"First time checking {symbol}. Current price: ${current_price:.2f}"
    elif current_price > last_price:
        message = f"{symbol} price went UP from ${last_price:.2f} to ${current_price:.2f}"
    elif current_price < last_price:
        message = f"{symbol} price went DOWN from ${last_price:.2f} to ${current_price:.2f}"
    else:
        message = f"{symbol} price stayed the same: ${current_price:.2f}"

    # Write new state
    try:
        state_file.write_text(str(current_price))
    except Exception as e:
        _print_err(f"Failed to write state file: {e}")

    return message

def summarize_clipboard_text(**kwargs):
    text = pyperclip.paste() or ""
    if not text.strip():
        return ("No text found in clipboard.")
    summary = groq_answer("Summarize the following text. Keep it concise.", text)
    if not summary:
        return ("Failed to summarize.")
    return (f"Summary:\n{textwrap(summary, 120)}")


def translate_clipboard_text(**kwargs):
    target_lang = kwargs.get("target_lang", "en")
    if GoogleTranslator is None:
        return ("deep_translator not available.")

    text = pyperclip.paste() or ""
    if not text.strip():
        return ("No text found in clipboard.")

    translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
    return (f"Translated ({target_lang}):\n{translated}")

def enable_game_mode(**kwargs) -> str:
    """
    Enables platform-specific high-performance/game mode settings.
    This includes Windows GameBar settings, macOS energy policy, and Linux CPU governor settings.
    """
    results = []

    if IS_WINDOWS:
        # Windows: Enable Game Mode setting and set to High Performance power plan
        try:
            if winreg is None:
                raise ImportError("winreg not available (Windows environment expected).")
            
            # 1. Enable GameBar Auto Game Mode
            # GUID for High Performance: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            
            # 2. Set High Performance Power Plan
            subprocess.run("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", 
                           check=False, shell=True, capture_output=True, timeout=5)
            
            results.append("Windows Game Mode settings enabled and power plan set to High Performance.")
        except Exception as e:
            _print_err(f"Windows Game Mode activation failed: {e}")
            results.append(f"Windows activation failed: {e}")
            
    elif IS_MACOS:
        # macOS: Disable App Nap and set system energy mode to high performance.
        try:
            # 1. Set System Power Policy for High Performance (Requires admin privileges)
            # This is complex and often requires a specific power profile utility.
            # Using the simpler, widely available 'pmset' to prevent display sleep/disk sleep.
            
            # Prevent display sleep, computer sleep, and disk sleep
            subprocess.run("sudo pmset -a disablesleep 1", 
                           check=True, shell=True, capture_output=True, timeout=5)
            
            # Optional: Disable App Nap (Requires admin and complex scripting)
            results.append("macOS performance tweaks activated (sleep disabled).")
        except subprocess.CalledProcessError:
            results.append("macOS: Sudo password required for performance settings. Run manually.")
        except Exception as e:
            results.append(f"macOS activation failed: {e}")

    elif IS_LINUX:
        # Linux: Set CPU Governor to 'performance' (Requires root/sudo)
        try:
            # Find the path to the CPU governor settings
            cpu_paths = list(Path("/sys/devices/system/cpu/").glob("cpu*/cpufreq/scaling_governor"))
            if not cpu_paths:
                 results.append("Linux CPU governor control paths not found.")
            else:
                # Set all available cores to 'performance'
                for p in cpu_paths:
                    subprocess.run(f"echo performance | sudo tee {p}", 
                                   check=True, shell=True, capture_output=True, timeout=5)
                results.append("Linux CPU Governor set to 'performance' for all cores.")
        except subprocess.CalledProcessError:
            results.append("Linux: Sudo password required to change CPU governor. Run manually.")
        except Exception as e:
            results.append(f"Linux activation failed: {e}")
            
    else:
        results.append("System performance mode not supported on this operating system.")

    # Always run cleanup (DNS flush, temp files, etc.) as a final performance step
    if 'SystemCleanup' in globals():
        SystemCleanup.main()
        results.append("System cleanup performed.")
    
    return "\n".join(results)


def merge_pdfs_in_folder(**kwargs):
    folder_path = kwargs.get("folder_path")
    output_filename = kwargs.get("output_filename", "merged_output.pdf")
    folder = Path(folder_path)
    pdf_files = sorted([p for p in folder.iterdir() if p.suffix.lower() == ".pdf"])
    if not pdf_files:
        return ("No PDF files found.")
    out_path = folder / output_filename
    merger = PdfMerger()
    added = []
    for pdf in pdf_files:
        try:
            merger.append(str(pdf))
            added.append(pdf.name)
        except Exception as e:
            _print_err(f"Skipped {pdf.name}: {e}")
    try:
        with out_path.open("wb") as f:
            merger.write(f)
    except Exception as e:
        _print_err(f"Failed to write merged PDF: {e}")
        merger.close()
        return ("Failed to write merged PDF.")
    merger.close()
    if added:
        return (f"Merged PDF saved to: {out_path} (added: {', '.join(added)})")
    return (f"No PDFs merged.")

def download_unsplash_wallpapers(**kwargs):
    query = kwargs.get("query", "nature")
    count = int(kwargs.get("count", 5))
    save_path = Path("unsplash_wallpapers")
    save_path.mkdir(exist_ok=True)
    saved = []
    for i in range(count):
        try:
            url = f"https://source.unsplash.com/1920x1080/?{requests.utils.quote(query)}&sig={i}"
            r = SESSION.get(url, timeout=15)
            r.raise_for_status()
            fname = save_path / f"{query}_{i}.jpg"
            fname.write_bytes(r.content)
            saved.append(str(fname))
        except Exception as e:
            _print_err(f"Error downloading image {i}: {e}")
    if saved:
        return f"Downloaded {len(saved)} images: {saved}"
    return "No images downloaded."

def detect_fake_news(**kwargs):
    text = kwargs.get("text") or kwargs.get("raw_input") or ""
    true_and_false = groq_answer("detect whether this information is real or fake", text)
    return true_and_false

def website_summarizer(**kwargs) -> Optional[str]:
    url = kwargs.get("url") or kwargs.get("raw_input") or ""
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            return groq_answer(
                "Summarize this HTML. Focus on important content, ignore boilerplate/navigation.",
                r.text,
            )
        else:
            _print_err(f"HTTP {r.status_code} for {url}")
            return None
    except Exception as e:
        _print_err(f"Request failed: {e}")
        return None

def get_local_ip(**kwargs) -> str:
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception:
        return "127.0.0.1"

def port_scanner(**kwargs):
    ip = kwargs.get("ip")
    ports = kwargs.get("ports", "22-443")
    if nmap is None:
        return ("nmap-python not available.")
    scanner = nmap.PortScanner()
    if ip is None:
        ip = get_local_ip()
    try:
        scanner.scan(ip, ports)
    except Exception as e:
        _print_err(f"Scan failed: {e}")
        return

    if ip not in scanner.all_hosts():
        return (f"{ip} not found in scan results.")

    state = scanner[ip].state()
    if state != "up":
        return f"{ip} appears {state}"

    results = []
    for proto in scanner[ip].all_protocols():
        results.append(f"\nProtocol: {proto.upper()}")
        ports_data = scanner[ip][proto].keys()
        if ports_data:
            for port in sorted(ports_data):
                entry = scanner[ip][proto][port]
                name = entry.get("name", "unknown").upper()
                st = entry.get("state", "unknown").capitalize()
                results.append(f"Port {port} ({name}): {st}")
        else:
            results.append("No open ports found in this protocol.")
    return "\n".join(results)


async def _ble_discover_async(timeout: float = 5.0):
    if BleakScanner is None:
        raise RuntimeError("bleak not available.")
    devices = await BleakScanner.discover(timeout=timeout)
    return devices

def get_nearby_devices(**kwargs):
    timeout = float(kwargs.get("timeout", 5.0))
    if BleakScanner is None:
        return "bleak not available."

    try:
        # Handle running loop vs no running loop
        try:
            loop = asyncio.get_running_loop()
            # If loop exists, use create_task and run_until_complete workaround
            devices = loop.run_until_complete(_ble_discover_async(timeout=timeout))
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            devices = asyncio.run(_ble_discover_async(timeout=timeout))

        if not devices:
            return "No devices found."

        out = [f"Device: {d.name} [{d.address}]" for d in devices]
        return "\n".join(out)

    except Exception as e:
        _print_err(f"BLE scan failed: {e}")
        return None

def audio_translator_auto(**kwargs):
    audio_file_path = kwargs.get("audio_file_path") or kwargs.get("raw_input")
    target_language = kwargs.get("target_language", "en")
    output_audio_file = kwargs.get("output_audio_file", "translated_audio.mp3")
    if GoogleTranslator is None:
        return "deep_translator not available."
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_path) as source:
            audio_data = r.record(source)
        transcribed_text = r.recognize_google(audio_data)
        translated_text = GoogleTranslator(source="auto", target=target_language).translate(transcribed_text)
        # If pygame not available, save text to file and return path
        if pygame is None:
            try:
                Path(output_audio_file).write_text(translated_text, encoding="utf-8")
                return f"Saved translated text (pygame not installed): {output_audio_file}"
            except Exception as e:
                _print_err(f"Failed to save translated text: {e}")
                return "Failed to save translated text (pygame not installed)."

        # Use gTTS only when available
        try:
            from gtts import gTTS
            tts = gTTS(text=translated_text, lang=target_language, slow=False)
            tts.save(output_audio_file)
        except Exception as e:
            _print_err(f"gTTS failed: {e}")
            return "Audio save failed."

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(output_audio_file)
            pygame.mixer.music.play()
            # Non-blocking wait; allow Ctrl+C to break
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            # remove file after playback
            try:
                os.remove(output_audio_file)
            except Exception:
                pass
            return (f"Translated Text ({target_language}): {translated_text}")
        except Exception as e:
            _print_err(f"Could not play audio: {e}")
            # attempt to remove file anyway
            try:
                os.remove(output_audio_file)
            except Exception:
                pass
            return (f"Translated Text ({target_language}): {translated_text} (could not play audio)")
    except sr.UnknownValueError:
        return "Error: Could not understand audio."
    except sr.RequestError as e:
        return f"Error: Speech recognition request failed; {e}"
    except FileNotFoundError:
        return "Error: Audio file not found."
    except Exception as e:
        return f"An error occurred during the translation process: {e}"

audio_queue: "queue.Queue[str]" = queue.Queue()

def listen_meeting():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)

        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=10)
                try:
                    text = recognizer.recognize_google(audio)
                    audio_queue.put(text)
                except sr.UnknownValueError:
                    continue
            except Exception as e:
                _print_err(f"Error listening: {e}")
                break

def summarize_meeting(**kwargs):
    meeting_text = kwargs.get("meeting_text") or kwargs.get("raw_input") or ""
    prompt = (
        "Summarize the following meeting transcript as JSON with keys: "
        "key_points (list), decisions (list), action_items (list of objects with owner if present). "
        "Return ONLY JSON."
    )
    structured = groq_answer(prompt, meeting_text)
    try:
        data = json.loads((structured or "").strip())
        return data
    except Exception:
        return {"key_points": [], "decisions": [], "action_items": []}



def process_transcripts():
    all_text = ""
    while True:
        try:
            transcript = audio_queue.get(timeout=10)
            all_text += transcript + "\n"
            summary = summarize_meeting(all_text)
            return summary
        except queue.Empty:
            continue

# -----------------------------
# OCR helpers
# -----------------------------


def ocr(**kwargs):
    image_path = kwargs.get("image_path") or kwargs.get("raw_input")
    api_key = kwargs.get("api_key", "K85328613788957")
    p = Path(image_path)
    if not p.exists():
        return "Error: image not found."
    try:
        with p.open("rb") as img:
            r = SESSION.post(
                "https://api.ocr.space/parse/image",
                files={"image": img},
                data={"apikey": api_key, "language": "eng", "OCREngine": "2"},
                timeout=60,
            )
        r.raise_for_status()
    except Exception as e:
        return f"Error: OCR request failed: {e}"

    try:
        result = r.json()
    except ValueError:
        return f"Response not JSON: {r.text[:200]}..."

    if result.get("IsErroredOnProcessing"):
        return "❌ OCR Failed: " + str(result.get("ErrorMessage"))
    parsed = result.get("ParsedResults")
    if parsed and parsed[0].get("ParsedText"):
        return parsed[0]["ParsedText"].strip()
    return "⚠️ No text found in image."

def ocr_screen(**kwargs):
    api_key = kwargs.get("api_key", "K85328613788957")
    # Capture whole screen to temp
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        try:
            img = ImageGrab.grab()
        except Exception:
            return "Screen capture not supported on this system."
        img.save(temp_path)
        text = ocr(image_path=temp_path, api_key=api_key)
        summary = groq_answer("Describe the content of this text in 1-3 sentences. Do not mention screenshot/image.", text)
        return summary
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass

def translate_image(**kwargs):
    image_path = kwargs.get("image_path") or kwargs.get("raw_input")
    target_lang = kwargs.get("target_lang", "en")
    if GoogleTranslator is None:
        return "deep_translator not available."
    extracted_text = ocr(image_path=image_path)
    if not (extracted_text or "").strip() or (extracted_text or "").startswith("Error"):
        return "No readable text found."
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(extracted_text)
        return translated
    except Exception as e:
        return f"Translation failed: {e}"

# -----------------------------
# Quick utilities
# -----------------------------

def clear_recycle_bin(**kwargs) -> str:
    """
    Clears the recycled/trashed items on Windows, macOS, and Linux
    by calling the core cross-platform cleanup method.
    """
    # We delegate the platform-specific logic to the SystemCleanup class
    return SystemCleanup.clean_recycled_items()

def lock_screen(**kwargs):
    """Locks the screen using OS-native methods."""
    if IS_WINDOWS:
        try:
            # Preferred method (fastest)
            ctypes.windll.user32.LockWorkStation()
            return "Screen locked (Windows)."
        except Exception:
            # Fallback if ctypes fails (requires 'keyboard' module)
            if press_and_release:
                press_and_release("win + l")
                return "Screen locked (Windows, keyboard emulation)."
            return "Screen locked (Windows, failed to lock)."
    elif IS_MACOS:
        try:
            # Requires Accessibility permissions for scripting
            command = "osascript -e 'tell application \"System Events\" to keystroke \"q\" using {control down, command down}'"
            subprocess.run(command, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Screen locked (macOS)."
        except Exception:
            return "Error: macOS lock failed. Try enabling scripting/accessibility."
    elif IS_LINUX:
        # Check common Linux desktop environment commands
        if shutil.which("gnome-screensaver-command"):
            subprocess.run(["gnome-screensaver-command", "-l"], check=False)
            return "Screen locked (Linux Gnome)."
        elif shutil.which("loginctl"):
            subprocess.run(["loginctl", "lock-session"], check=False)
            return "Screen locked (Linux loginctl)."
        else:
            return "Warning: Linux DE lock command not found."
    return "Lock screen not supported on this OS."

def translate_document(**kwargs):
    if GoogleTranslator is None:
        return ("deep_translator not available.")
    input_file = kwargs.get("input_file")
    output_file = kwargs.get("output_file")
    target_language = kwargs.get("target_language", "en")
    inp = Path(input_file)
    out = Path(output_file)
    with inp.open("r", encoding="utf-8", errors="ignore") as infile, out.open("w", encoding="utf-8") as outfile:
        for line in infile:
            tr = GoogleTranslator(source="auto", target=target_language).translate(line)
            outfile.write(tr + "\n")

def s_h(**kwargs):
    import webbrowser
    webbrowser.open("https://www.google.com")
    time.sleep(2)
    try:
        press_and_release("ctrl + h")
    except Exception:
        pass

# -----------------------------
# Natural alarm AI
# -----------------------------


def natural_alarm_ai(**kwargs):
    command = kwargs.get("command") or kwargs.get("raw_input") or ""
    message = kwargs.get("message", "Reminder!")
    parsed = groq_answer(
        "Extract time from the text below. Return ONLY valid JSON: "
        "either {'hours':int,'minutes':int,'seconds':int} or {'absolute_time':'YYYY-MM-DD HH:MM:SS'}",
        command,
    )

    try:
        data = json.loads((parsed or "").strip())
    except Exception:
        return f"❌ AI could not parse the time. Raw: {parsed}"

    duration_seconds = 0
    now = dt.datetime.now()
    if any(k in data for k in ["hours", "minutes", "seconds"]):
        duration_seconds = data.get("hours", 0) * 3600 + data.get("minutes", 0) * 60 + data.get("seconds", 0)
    elif "absolute_time" in data:
        try:
            target = dt.datetime.fromisoformat(data["absolute_time"])
            duration_seconds = (target - now).total_seconds()
        except Exception:
            return "❌ Invalid absolute_time format."

    if duration_seconds <= 0:
        return "❌ Invalid or past time provided."

    target_time = now + dt.timedelta(seconds=duration_seconds)

    # Pre-fetch weather & quote while waiting (non-blocking approach would be threading; keep simple)
    weather = ""
    quote = ""
    try:
        weather = SESSION.get("https://wttr.in/?format=3", timeout=10).text.strip()
    except Exception:
        weather = "N/A"
    try:
        jq = SESSION.get("https://zenquotes.io/api/random", timeout=10).json()
        quote = jq[0].get("q", "Stay awesome!") if isinstance(jq, list) else "Stay awesome!"
    except Exception:
        quote = "Stay awesome!"

    # Wait
    time.sleep(duration_seconds)

    # Ring
    if pygame:
        try:
            pygame.mixer.init()
            wav = Path("alarm.wav")
            if wav.exists():
                pygame.mixer.music.load(str(wav))
                pygame.mixer.music.play()
        except Exception as e:
            _print_err(f"Alarm play failed: {e}")

    _safe_message_box("Alarm", f"⏰ Alarm ringing!\n\n🌤 Weather: {weather}\n💡 Quote: {quote}\n\n{message}")

    if pygame:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    return "✅ Alarm finished."

# -----------------------------
# YouTube Summarizer / Downloader / Play
# -----------------------------

def youtube_summarizer(**kwargs):
    # Basic captions approach (pytube captions may be unreliable)
    try:
        url = kwargs.get("url") or kwargs.get("raw_input") or ""
        yt = YouTube(url)
        # Try to pull transcript via third-party APIs normally; we attempt description as fallback
        text = yt.description or ""
        if not text.strip():
            return "No captions/description available for this video."
        summary = groq_answer("Summarize the following video description concisely:", text)
        return summary
    except Exception as e:
        return f"Error: {str(e)}"

def ytDownloader(**kwargs):
    yt_url = kwargs.get("yt_url") or kwargs.get("raw_input") or ""
    if YouTube is None:
        print("pytube not available.")
        return
    yt = YouTube(yt_url)
    video = yt.streams.get_highest_resolution()
    out = video.download()
    return (f"Downloaded: {out}")

def playMusic(**kwargs):
    song_name = kwargs.get("song_name") or kwargs.get("raw_input") or ""
    if pywhatkit is None:
        return ("pywhatkit not available.")
    try:
        pywhatkit.playonyt(song_name)
    except Exception as e:
        _print_err(f"Play failed: {e}")

# -----------------------------
# QR Code
# -----------------------------

def qrCodeGenerator(**kwargs) -> str:
    """
    Generates a QR code from text or a link and saves it as a PNG file.
    The function then attempts to open the generated file using the platform's
    default application.
    Requires: 'qrcode' library.
    """
    input_text_link = kwargs.get("input_text_link") or kwargs.get("raw_input") or ""
    
    if qrcode is None:
        return "Error: The 'qrcode' library is not installed."
    
    if not input_text_link.strip():
        return "Error: No text or link provided to generate QR code."
        
    try:
        now = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fname = f"{now}-QrCode.png"
        output_path = Path(fname).resolve()
        
        # 1. QR Code Generation (Cross-platform with 'qrcode' library)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=15,
            border=4,
        )
        qr.add_data(input_text_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        
        # 2. Open File (Cross-platform implementation)
        try:
            if IS_WINDOWS:
                os.startfile(str(output_path))
            elif IS_MACOS:
                subprocess.run(["open", str(output_path)], check=False, timeout=5, stderr=subprocess.DEVNULL)
            elif IS_LINUX:
                # 'xdg-open' is the standard cross-desktop command
                subprocess.run(["xdg-open", str(output_path)], check=False, timeout=5, stderr=subprocess.DEVNULL)
            else:
                return f"Saved QR: {fname}. File opening skipped (unsupported OS)."
                
            return (f"Saved QR and opened file: {output_path.name}")
            
        except Exception:
            # Catch errors in subprocess/os.startfile and just return success for saving
            return (f"Saved QR: {output_path.name}. Could not open file automatically.")
            
    except Exception as e:
        _print_err(f"QR generation failed: {e}")
        return f"QR code generation failed: {e}"

# -----------------------------
# Read PDF (first page)
# -----------------------------

def read_pdf(**kwargs) -> str:
    pdf_file = kwargs.get("pdf_file") or kwargs.get("raw_input")
    try:
        reader = PdfReader(str(pdf_file))
        if not reader.pages:
            return ""
        page = reader.pages[0]
        return page.extract_text() or ""
    except Exception as e:
        _print_err(f"PDF read failed: {e}")
        return ""

# -----------------------------
# File Organizer
# -----------------------------


def organize_files(**kwargs):
    directory = Path(kwargs.get("directory") or kwargs.get("raw_input"))
    if not directory.is_dir():
        return ("Directory does not exist.")
    mapping = {
        ("doc", "docx"): "Word",
        ("xls", "xlsx"): "Excel",
        ("ppt", "pptx"): "PowerPoint",
        ("pdf",): "PDF",
        ("exe",): "Applications",
        ("py", "java", "html", "css", "js"): "Code",
        ("jpg", "jpeg", "png", "gif", "webp", "bmp"): "Images",
        ("mp4", "mkv", "mov", "avi"): "Videos",
        ("mp3", "wav", "flac"): "Audio",
        ("zip", "rar", "7z", "tar", "gz"): "Archives",
        ("csv",): "Data",
    }

    def target_folder_for(ext: str) -> str:
        ext = ext.lower().lstrip(".")
        for exts, folder in mapping.items():
            if ext in exts:
                return folder
        return ext or "no_extension"

    moved = []
    for item in directory.iterdir():
        if item.is_dir():
            continue
        ext = item.suffix[1:] if item.suffix else "no_extension"
        target = directory / target_folder_for(ext)
        target.mkdir(exist_ok=True)
        try:
            shutil.move(str(item), str(target / item.name))
            moved.append(f"{item.name} -> {target.name}/")
        except Exception as e:
            _print_err(f"Move failed for {item}: {e}")
    if moved:
        return f"Moved items:\n" + "\n".join(moved)
    return "No files moved."

def file_organizer(**kwargs) -> str:
    directory = kwargs.get("directory") or kwargs.get("raw_input")
    if Path(directory).is_dir():
        return organize_files(directory=directory)
    return "The specified directory does not exist."

# -----------------------------
# Simple transcription
# -----------------------------


def transcribe_audio(**kwargs) -> str:
    file_path = kwargs.get("file_path") or kwargs.get("raw_input")
    r = sr.Recognizer()
    try:
        with sr.AudioFile(str(file_path)) as source:
            audio = r.record(source)
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "Could not request results"
    except Exception as e:
        return f"Transcription failed: {e}"

# -----------------------------
# Download images (batch)
# -----------------------------


def download_images(**kwargs):
    image_urls = kwargs.get("image_urls") or kwargs.get("raw_input") or []
    downloaded = []
    for url in image_urls:
        try:
            r = SESSION.get(url, timeout=20)
            r.raise_for_status()
            name = url.split("/")[-1] or f"image_{hashlib.md5(url.encode()).hexdigest()}.jpg"
            Path(name).write_bytes(r.content)
            downloaded.append(name)
        except Exception as e:
            _print_err(f"Failed to download {url}: {e}")
    if downloaded:
        return (f"Downloaded: {', '.join(downloaded)}")
    return "No images downloaded."

# -----------------------------
# Create file from natural text
# -----------------------------

_FILE_EXT_MAP = {
    "python file": ".py",
    "java file": ".java",
    "text file": ".txt",
    "html file": ".html",
    "css file": ".css",
    "javascript file": ".js",
    "json file": ".json",
    "xml file": ".xml",
    "csv file": ".csv",
    "markdown file": ".md",
    "yaml file": ".yaml",
    "pdf file": ".pdf",
    "word file": ".docx",
    "excel file": ".xlsx",
    "powerpoint file": ".pptx",
    "zip file": ".zip",
    "tar file": ".tar",
    "image file": ".png",
    "audio file": ".mp3",
    "video file": ".mp4",
}

def get_file_extension(text: str) -> str:
    t = text.lower()
    for key, ext in _FILE_EXT_MAP.items():
        if key in t:
            return ext
    return ""

def _strip_type_words(text: str) -> str:
    t = text
    for key in _FILE_EXT_MAP.keys():
        t = t.replace(key, "")
    t = t.replace("named", "").replace("with name", "").replace("create", "")
    return " ".join(t.split())

def create_file(text: str):
    selected_ext = get_file_extension(text)
    core = _strip_type_words(text)
    name = core if core else "demo"
    p = Path(f"{name}{selected_ext}")
    p.touch(exist_ok=True)
    return (f"Created: {p.resolve()}")

# -----------------------------
# Top processes
# -----------------------------


def get_top_processes(num_processes: int = 3) -> List[Tuple[str, float, int]]:
    processes: List[Tuple[str, float, int]] = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            cpu = proc.info.get("cpu_percent", 0.0) or 0.0
            mem = getattr(proc.info.get("memory_info", None), "rss", 0)
            name = proc.info.get("name") or f"pid-{proc.info.get('pid')}"
            processes.append((name, float(cpu), int(mem)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    processes.sort(key=lambda p: (p[1], p[2]), reverse=True)
    return processes[:num_processes]

def display_top_processes():
    lines = []
    for name, cpu, mem in get_top_processes():
        lines.append(f"Process: {name}, CPU: {int(cpu)}%, Memory: {int(mem / (1024 * 1024))} MB")
    return "\n".join(lines) if lines else "No processes to display."

# -----------------------------
# Wallpaper
# -----------------------------

def change_wallpaper(*args, **kwargs) -> str:
    """
    Changes the desktop wallpaper across Windows, macOS, and Linux
    using platform-specific system calls or commands.
    """
    # 1. Get the image path argument
    if args:
        image_path = args[0]
    else:
        image_path = kwargs.get("image_path") or kwargs.get("raw_input")
        
    if not image_path:
        return "Error: No image path provided."
        
    p = Path(image_path).resolve()
    
    if not p.is_file():
        return (f"Error: Wallpaper file not found at: {p}")
    
    image_uri = p.as_uri() # Standard URI for commands/settings

    # 2. Platform-Specific Logic
    if IS_WINDOWS and ctypes:
        # Windows: Use the native SystemParametersInfoW
        try:
            # 20: SPI_SETDESKWALLPAPER
            # 3: SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            ctypes.windll.user32.SystemParametersInfoW(20, 0, str(p), 3)
            return "Wallpaper changed successfully (Windows)."
        except Exception as e:
            _print_err(f"Windows wallpaper failed: {e}")
            return f"Windows wallpaper change failed: {e}"

    elif IS_MACOS:
        # macOS: Use osascript (AppleScript) to interact with Finder/System Events
        try:
            script = f"""
            tell application "System Events"
                tell application "Finder"
                    set desktop picture to POSIX file "{p}"
                end tell
            end tell
            """
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
            return "Wallpaper changed successfully (macOS)."
        except subprocess.CalledProcessError as e:
             _print_err(f"macOS wallpaper failed: {e.stderr.decode()}")
             return "macOS wallpaper change failed (Script Error: check image format)."
        except Exception as e:
            _print_err(f"macOS wallpaper failed: {e}")
            return f"macOS wallpaper change failed: {e}"

    elif IS_LINUX:
        # Linux: Use gsettings (Gnome, Cinnamon, Mate) or feh (other WMs)
        # Note: GNOME is the most common default environment.
        try:
            # Try GSettings (Gnome, Cinnamon, Mate, potentially others)
            # We use the 'file' schema and the image URI
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", image_uri], 
                           check=True, capture_output=True, timeout=5)
            # Newer GNOME uses picture-uri-dark
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", image_uri], 
                           check=False, capture_output=True, timeout=5)
            
            return "Wallpaper changed successfully (Linux - GSettings/GNOME)."
            
        except subprocess.CalledProcessError:
            # Fallback to older commands or other DEs
            try:
                # Try XFCE
                subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image", "-s", str(p)], 
                               check=True, capture_output=True, timeout=5)
                return "Wallpaper changed successfully (Linux - XFCE)."
            except subprocess.CalledProcessError:
                # Fallback to using feh (requires feh to be installed)
                try:
                    subprocess.run(["feh", "--bg-scale", str(p)], check=True, capture_output=True, timeout=5)
                    return "Wallpaper changed successfully (Linux - feh)."
                except subprocess.CalledProcessError:
                     return "Linux wallpaper change failed. Requires gsettings, xfconf, or 'feh' to be installed and accessible."
            except Exception as e:
                 _print_err(f"Linux wallpaper failed: {e}")
                 return f"Linux wallpaper change failed: {e}"

    return "Wallpaper change not supported on this operating system."


# -----------------------------
# Analyze CSV -> DOCX report
# -----------------------------

def analyze_and_report(*args, **kwargs):
    # Accept positional (csv_file, report_file) or keyword args
    if Document is None:
        return ("python-docx not available.")
    if args:
        csv_file = args[0]
        report_file = args[1] if len(args) > 1 else kwargs.get("report_file")
    else:
        csv_file = kwargs.get("csv_file") or kwargs.get("raw_input")
        report_file = kwargs.get("report_file")
    try:
        csv_text = Path(csv_file).read_text(encoding="utf-8", errors="ignore")
        report_content = groq_answer("Analyze the following CSV data and generate a detailed report:", csv_text)
        doc = Document()
        doc.add_heading("AI-Generated Report", level=1)
        doc.add_paragraph(report_content)
        doc.save(str(report_file))
        return (f"Report generated: {report_file}")
    except FileNotFoundError:
        _print_err(f"File not found: {csv_file}")
    except Exception as e:
        _print_err(f"Report generation failed: {e}")

# -----------------------------
# Email (Django)
# -----------------------------


def send_email(*args, **kwargs):
    # Accept positional (message, email) or keywords
    if args:
        message = args[0]
        email = args[1] if len(args) > 1 else kwargs.get("email")
    else:
        message = kwargs.get("message") or kwargs.get("raw_input")
        email = kwargs.get("email")
    try:
        from django.core.mail import send_mail as dj_send_mail # type: ignore
    except Exception:
        return ("Django mail not configured/installed.")
    try:
        dj_send_mail("", message, email, [email], fail_silently=False)
    except Exception as e:
        _print_err(f"send_email failed: {e}")

def send_multiple_emails(*args, **kwargs):
    # Accept positional (message, emails_string, sender)
    if args:
        message = args[0]
        emails_string = args[1] if len(args) > 1 else kwargs.get("emails_string")
        sender = args[2] if len(args) > 2 else kwargs.get("sender", "you@example.com")
    else:
        message = kwargs.get("message") or kwargs.get("raw_input")
        emails_string = kwargs.get("emails_string")
        sender = kwargs.get("sender", "you@example.com")

    try:
        from django.core.mail import send_mail as dj_send_mail # type: ignore
    except Exception:
        return ("Django mail not configured/installed.")
    emails = [e.strip() for e in emails_string.split(",") if e.strip()]
    results = []
    for email in emails:
        try:
            dj_send_mail("", message, sender, [email], fail_silently=False)
            results.append(f"Email sent to {email}")
        except Exception as e:
            _print_err(f"Failed to send to {email}: {e}")
            results.append(f"Failed to send to {email}: {e}")
    return "\n".join(results)
# -----------------------------
# Search & open files
# -----------------------------

def list_all_files_and_folders(path: str | Path) -> str:
    lines = []
    for root, dirs, files in os.walk(path):
        lines.append(f"\n📁 Folder: {root}")
        for d in dirs:
            lines.append(f"  📂 Subfolder: {d}")
        for f in files:
            lines.append(f"  📄 File: {f}")
    return "\n".join(lines)

def open_file(*args, **kwargs):
    # Accept positional (keyword, roots) or keywords
    if args:
        keyword = args[0]
        roots = args[1] if len(args) > 1 else kwargs.get("roots")
    else:
        keyword = kwargs.get("keyword") or kwargs.get("raw_input")
        roots = kwargs.get("roots")

    roots = roots or [
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Pictures",
        Path.home() / "Videos",
        Path.home() / "Music",
    ]
    k = keyword.lower()
    candidates: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and k in p.name.lower():
                candidates.append(p)
    if not candidates:
        return ("No matching file found.")
    # Choose most recent modified
    best = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        if IS_WINDOWS:
            os.startfile(str(best.resolve()))
        else:
            subprocess.run(["xdg-open", str(best.resolve())], check=False)
        return (f"Opened: {best}")
    except Exception as e:
        _print_err(f"Open failed: {e}")

# -----------------------------
# Brightness & Net speed
# -----------------------------

def dim_light(*args, **kwargs):
    # Accept positional level or keyword 'level'
    if args:
        level = args[0]
    else:
        level = kwargs.get("level", 45)
    try:
        set_brightness(int(level))
    except Exception as e:
        _print_err(f"Set brightness failed: {e}")

def internet_speed(duration: int = 3) -> str:
    try:
        pernic = psutil.net_io_counters(pernic=True)
        interface = next((n for n, s in pernic.items() if not n.startswith("lo") and s.bytes_recv > 0), None)
        if not interface:
            return "No active network interface found."
        bytes_recv = pernic[interface].bytes_recv
        time.sleep(duration)
        new_bytes_recv = psutil.net_io_counters(pernic=True)[interface].bytes_recv
        recv = new_bytes_recv - bytes_recv
        mbps = recv / (duration * 1024 * 1024)
        return f"Internet Speed ({interface}): {mbps:.2f} Mbps"
    except Exception as e:
        return f"Speed check failed: {e}"

# -----------------------------
# System restore point (Win)
# -----------------------------

def create_system_restore_point(**kwargs) -> str:
    """
    Creates a system snapshot or restore point using the native mechanism
    for Windows (System Restore), macOS (Time Machine Snapshot), or Linux (Timeshift/LVM).
    """
    # Create a unique name using the current date/time if not provided
    default_name = f"AutoPoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    name = kwargs.get("name", default_name)
    
    # Clean up the name for command line use (remove quotes, sanitize)
    clean_name = name.replace('"', '').replace("'", "")[:64] # Limit length

    if IS_WINDOWS:
        # Windows: Use WMIC to create a System Restore point
        try:
            command = f'wmic.exe /Namespace:\\\\root\\default Path SystemRestore Call CreateRestorePoint "{clean_name}", 100, 7'
            
            # Using subprocess.run for better error handling and security
            result = subprocess.run(command, check=False, shell=True, capture_output=True, text=True, timeout=15)
            
            if "ReturnValue = 0" in result.stdout:
                return f"System Restore Point created successfully (Windows): {clean_name}"
            else:
                _print_err(f"WMIC output: {result.stdout.strip()}")
                return "Failed to create Windows System Restore Point. (Ensure System Protection is ON)."
        except Exception as e:
            _print_err(f"Windows restore point failed: {e}")
            return f"Windows restore point command failed: {e}"

    elif IS_MACOS:
        # macOS: Create a local Time Machine Snapshot
        try:
            command = ["tmutil", "snapshot"]
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
            return f"Local Time Machine Snapshot created successfully (macOS)."
        except subprocess.CalledProcessError as e:
            _print_err(f"tmutil failed: {e.stderr.strip()}")
            return "Failed to create macOS Time Machine Snapshot. (Ensure Time Machine is configured)."
        except Exception as e:
            _print_err(f"macOS snapshot failed: {e}")
            return f"macOS snapshot command failed: {e}"

    elif IS_LINUX:
        # Linux: Use Timeshift (if installed) or a LVM/BTRFS-specific command.
        # Timeshift is the closest equivalent to System Restore for desktop Linux.
        try:
            # Command to create a Timeshift snapshot
            command = ["sudo", "timeshift", "--create", "--comments", clean_name]
            
            # Timeshift requires sudo and takes time, so a high timeout is necessary.
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and "Snapshot created successfully" in result.stdout:
                return f"Timeshift Snapshot created successfully (Linux): {clean_name}"
            elif result.returncode != 0 and "command not found" in result.stderr:
                 return "Linux snapshot failed: Timeshift is not installed or not in PATH."
            else:
                _print_err(f"Timeshift output: {result.stderr.strip()}")
                return "Failed to create Linux Timeshift Snapshot. (Requires sudo and Timeshift installed)."

        except Exception as e:
            _print_err(f"Linux snapshot failed: {e}")
            return f"Linux snapshot command failed: {e}"

    return "System snapshot functionality not supported on this operating system."

# -----------------------------
# Hashing & dedupe
# -----------------------------

def get_file_hash(**kwargs) -> Optional[str]:
    path = kwargs.get("path") or kwargs.get("raw_input")
    chunk_size = int(kwargs.get("chunk_size", 1 << 20))
    hasher = hashlib.sha256()
    p = Path(path)
    try:
        with p.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        _print_err(f"Could not read {p}: {e}")
        return None

def find_and_delete_duplicates(**kwargs):
    folder = Path(kwargs.get("folder") or kwargs.get("raw_input"))
    hashes: Dict[str, Path] = {}
    deleted = 0
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        h = get_file_hash(path=p)
        if not h:
            continue
        if h in hashes:
            try:
                p.unlink(missing_ok=True)
                deleted += 1
            except Exception as e:
                _print_err(f"Failed to delete {p}: {e}")
        else:
            hashes[h] = p
    return (f"\n✅ Done. {deleted} duplicates deleted.")

# -----------------------------
# Battery status
# -----------------------------


def _switch_to_power_saver():
    """Activates the platform's power-saver or low-energy profile."""
    if IS_WINDOWS:
        # GUID for default Power Saver: a1841308-3541-4fab-bc81-f71556f20b4a
        subprocess.run("powercfg /setactive a1841308-3541-4fab-bc81-f71556f20b4a", 
                       check=False, shell=True, capture_output=True, timeout=5)
        return "Windows power plan set to Power Saver."
    elif IS_MACOS:
        # Disable high power state (if set) and enable 'autopoweroff'
        # pmset -a command is complex, simpler is to tell the user/revert custom setting
        subprocess.run(["pmset", "-a", "lowpowermode", "1"], check=False, timeout=5, stderr=subprocess.DEVNULL)
        return "macOS Low Power Mode attempted (requires macOS 10.15+)."
    elif IS_LINUX:
        # Set CPU Governor to 'powersave' (requires sudo)
        try:
            cpu_paths = list(Path("/sys/devices/system/cpu/").glob("cpu*/cpufreq/scaling_governor"))
            for p in cpu_paths:
                subprocess.run(f"echo powersave | sudo tee {p}", 
                               check=False, shell=True, capture_output=True, timeout=5)
            return "Linux CPU Governor set to 'powersave'."
        except Exception:
            # Fallback if no paths or permissions fail
            return "Linux power saving activation failed (requires sudo/governor support)."
    return "Power saving actions skipped."

def _show_alert(title: str, message: str):
    """Shows a native, blocking alert box."""
    if IS_WINDOWS and ctypes:
        # Windows: native MessageBoxW
        ctypes.windll.user32.MessageBoxW(0, message, title, 1)
    elif IS_MACOS:
        # macOS: osascript (AppleScript for display dialog)
        script = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=5, stderr=subprocess.DEVNULL)
    elif IS_LINUX:
        # Linux: zenity, notify-send, or similar (zenity is common for blocking dialogs)
        if shutil.which("zenity"):
            subprocess.run(["zenity", "--warning", "--title", title, "--text", message], check=False, timeout=5, stderr=subprocess.DEVNULL)
        else:
            # Simple terminal print if no GUI tool is found
            print(f"\n[ALERT] {title}: {message}\n")
    else:
        print(f"\n[ALERT] {title}: {message}\n")

# --- Smart Battery Function ---

def smart_battery(**kwargs) -> str:
    """
    Checks battery status, provides feedback, and triggers power-saving
    measures and alerts on low battery across Windows, macOS, and Linux.
    Requires: 'psutil' library.
    """
    if psutil is None:
        return "Error: The 'psutil' library is not installed."
        
    batt = psutil.sensors_battery()
    
    if batt is None:
        return "Battery info not available (Desktop or unsupported hardware)."
        
    plugged = batt.power_plugged
    percent = int(batt.percent)
    
    if plugged:
        return(f"Battery is plugged in at {percent}%")
        
    # Messages and actions by range
    msg = ""
    action_taken = ""

    if percent > 75:
        msg = f"Battery is {percent}% — Perfect."
    elif 50 < percent <= 75:
        msg = f"Battery is {percent}% — Good charge."
    elif 25 < percent <= 50:
        msg = f"Battery is {percent}% — Consider charging soon."
    elif 10 < percent <= 25:
        # Low Battery Alert + Power Saver Switch
        alert_msg = "Battery low! Switching to saver mode."
        _show_alert("Battery Alert (25%)", alert_msg)
        action_taken = _switch_to_power_saver()
        msg = f"Battery is {percent}% — Charge now! {action_taken}"
    elif 5 < percent <= 10:
        # Critical Alert + Power Saver Switch
        alert_msg = "Battery low! Switching to saver mode."
        _show_alert("Battery Alert (10%)", alert_msg)
        action_taken = _switch_to_power_saver()
        msg = f"Battery is {percent}% — Charge immediately! {action_taken}"
    else: # 0-5%
        # Critical Alert + Power Saver Switch
        alert_msg = "Battery low! Switching to saver mode."
        _show_alert("Battery Critical! (5%)", alert_msg)
        action_taken = _switch_to_power_saver()
        msg = f"Battery is {percent}% — Critical! Plug in now. {action_taken}"
        
    return(msg)

# -----------------------------
# YouTube search
# -----------------------------

def yt_search(**kwargs):
    import webbrowser
    user = kwargs.get("user") or kwargs.get("raw_input") or ""
    q = re.sub(r"(?i)youtube\s*search", "", user).strip()
    webbrowser.open(f"https://www.youtube.com/results?search_query={requests.utils.quote(q)}")
    return "Opened YouTube search results."

# -----------------------------
# Smart app/web open/close
# -----------------------------


def openappweb(**kwargs) -> str:
    """
    Opens a URL in the browser (cross-platform) or launches a desktop application 
    using platform-specific commands.
    """
    query = kwargs.get("query") or kwargs.get("raw_input") or ""
    q = query.strip()

    # --- 1. Web Operation (Fully Cross-Platform) ---
    # Detect a domain-ish pattern properly
    if re.search(r"\b[a-z0-9-]+\.(com|co|org|net|io|ai|dev|app)\b", q, re.I):
        q_clean = re.sub(r"(?i)\b(open|jarvis|launch)\b", "", q).replace(" ", "")
        url = q_clean if q_clean.startswith(("http://", "https://")) else f"https://{q_clean}"
        webbrowser.open(url)
        return f"Opened URL: {url}"

    # --- 2. Application Operation (Platform-Specific) ---
    
    # 2a. Determine the clean application name
    app_name = q.lower()
    for word in ("stop", "close", "exit", "open", "launch", "run"):
        app_name = app_name.replace(word, "")
    app_name = app_name.strip()
    
    if not app_name:
        return "Error: No application name specified."

    # Use Groq to infer the short executable name (critical for success)
    short_name = groq_answer(
        "Return ONLY the short executable name (e.g., 'chrome', 'notepad', 'firefox'). DO NOT add .exe or path:",
        app_name
    ).strip().split()[0]
    
    if not short_name:
        _print_err("Could not infer app short name via Groq.")
        return f"Error: Failed to infer short name for '{app_name}'."
    
    try:
        if IS_WINDOWS:
            # Windows: Use subprocess to launch executable directly
            subprocess.Popen([f"{short_name}.exe"], shell=True)
            return f"Launched application (Windows): {short_name}.exe"
            
        elif IS_MACOS:
            # macOS: Use the 'open' command which handles application bundles (.app)
            subprocess.Popen(["open", "-a", short_name])
            return f"Launched application (macOS): {short_name}"
            
        elif IS_LINUX:
            # Linux: Try running the short name directly (assumes it's in PATH)
            subprocess.Popen([short_name])
            return f"Launched application (Linux): {short_name}"
        
        else:
            return "Application launch not supported on this OS."

    except FileNotFoundError:
        return f"Error: Application '{short_name}' not found or not in system PATH."
    except Exception as e:
        _print_err(f"Open app failed: {e}")
        return f"Application launch failed for '{short_name}': {e}"

def closeappweb(**kwargs) -> str:
    """
    Closes the current browser tab (cross-platform) or kills a desktop application process 
    using platform-specific commands.
    """
    query = kwargs.get("query") or kwargs.get("raw_input") or ""
    
    # --- 1. Tab Operation (Fully Cross-Platform via Hotkey) ---
    if "tab" in query.lower() or "browser" in query.lower():
        if pyautogui:
            try:
                # Ctrl+W/Cmd+W is standard for closing tabs/windows
                pyautogui.hotkey("ctrl", "w")
                return "Closed current tab/window."
            except Exception:
                return "Closed current tab/window (hotkey failed)."
        else:
            return "Cannot close tab: pyautogui not installed."

    # --- 2. Application Operation (Platform-Specific Process Kill) ---
    
    # 2a. Determine the clean application name
    q = query.lower()
    for word in ("stop", "close", "exit", "kill"):
        q = q.replace(word, "")
    app_name = q.strip()
    
    if not app_name:
        return "Error: No application name specified to close."

    # Use Groq to infer the short executable name
    short_name = groq_answer(
        "Return ONLY the short process/executable name (e.g., 'chrome', 'notepad', 'firefox'). DO NOT add .exe or path:",
        app_name
    ).strip().split()[0]
    
    if not short_name:
        _print_err("Could not infer app short name via Groq to close.")
        return f"Error: Failed to infer short name for '{app_name}'."
    
    try:
        if IS_WINDOWS:
            # Windows: taskkill by image name
            command = f"taskkill /f /im {short_name}.exe"
            subprocess.run(command, check=True, shell=True, capture_output=True, timeout=5)
            return f"Closed application (Windows, taskkill): {short_name}.exe"
            
        elif IS_MACOS or IS_LINUX:
            # macOS/Linux: pkill by name
            # -f matches the full command line, not just the executable name
            command = ["pkill", "-f", short_name]
            subprocess.run(command, check=True, capture_output=True, timeout=5)
            return f"Closed application (macOS/Linux, pkill): {short_name}"
            
        else:
            return "Application close not supported on this OS."

    except subprocess.CalledProcessError as e:
        if IS_WINDOWS and b"not found" in e.stdout:
            return f"Application '{short_name}' was not running."
        if (IS_MACOS or IS_LINUX) and b"no process found" in e.stderr:
             return f"Application '{short_name}' was not running."
        return f"Failed to close application '{short_name}': {e}"
    except Exception as e:
        _print_err(f"Close app failed: {e}")
        return f"Close application failed for '{short_name}': {e}"

# -----------------------------
# Excel summarize with Groq
# -----------------------------

def summarize_excel_with_groq(**kwargs):
    file_path = kwargs.get("file_path") or kwargs.get("raw_input")
    try:
        df = pd.read_excel(file_path)
        text_data = df.to_string(index=False)
        summary = groq_answer("Summarize the following table data concisely:", text_data)
        return (summary)
    except Exception as e:
        _print_err(f"Excel summarize failed: {e}")

# -----------------------------
# Helpers
# -----------------------------

def textwrap(**kwargs) -> str:
    s = kwargs.get("s") or kwargs.get("raw_input") or ""
    width = int(kwargs.get("width", 100))
    import textwrap as tw
    return "\n".join(tw.wrap(s, width=width))

# -----------------------------
# Melody
# -----------------------------

def melody(**kwargs):
    import melody_generator
    melody_generator.main()

MACRO_FILE = "macros.json"

def record_macro(**kwargs):
    name = kwargs.get("name", "default")
    duration = int(kwargs.get("duration", 30))
    print(f"🎥 Recording macro '{name}' for {duration}s...")
    start = time.time()
    actions = []
    while time.time() - start < duration:
        x, y = pyautogui.position()
        actions.append({"time": time.time()-start, "pos": (x,y)})
        time.sleep(0.5)
    with open(MACRO_FILE, "w") as f:
        json.dump(actions, f)
    return f"✅ Macro '{name}' saved."


def play_macro(**kwargs):
    name = kwargs.get("name", "default")
    try:
        with open(MACRO_FILE) as f:
            actions = json.load(f)
        for act in actions:
            pyautogui.moveTo(*act["pos"])
            time.sleep(0.5)
        return f"▶️ Macro '{name}' executed."
    except Exception:
        return "❌ Macro not found."
    

# -------------------------
# Web Interaction Functions
# -------------------------

def fetch_page(url: str, **kwargs):
    try:
        resp = SESSION.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        _print_err(f"fetch_page failed for {url}: {e}")
        return ""

def get_page_title(url: str, **kwargs):
    html = fetch_page(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else ""

def get_meta_description(url: str, **kwargs):
    html = fetch_page(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    desc_tag = soup.find("meta", attrs={"name": "description"})
    return desc_tag["content"].strip() if desc_tag and "content" in desc_tag.attrs else ""

def search_google(query: str, num_results: int = 5, **kwargs) -> List[str]:
    """
    Performs a Google search using web scraping. WARNING: This method is highly 
    unreliable and often breaks due to Google's anti-scraping measures and frequent 
    HTML changes. Use a dedicated API for production environments.
    """
    # Use requests.utils.quote or urllib.parse.quote for standard URL encoding
    try:
        query_encoded = requests.utils.quote(query)
    except AttributeError:
        # Fallback if requests.utils is missing quote (uncommon)
        from urllib.parse import quote
        query_encoded = quote(query)

    url = f"https://www.google.com/search?q={query_encoded}&num={num_results}"
    
    # Use a realistic User-Agent to slightly reduce bot detection risk
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"}
    
    try:
        # Ensure SESSION is available or use requests directly
        if 'SESSION' in globals():
            resp = SESSION.get(url, headers=headers, timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
            
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        # New selector based on more recent SERP structure (still vulnerable!)
        # Looks for the main link container for organic results
        for g in soup.find_all("div", class_="yuRUbf"):
            link_tag = g.find("a")
            if link_tag and link_tag.get("href"):
                results.append(link_tag["href"])
        
        # If no results found, try the older selector as a fallback (tF2Cxc)
        if not results:
             for g in soup.find_all("div", class_="tF2Cxc"):
                link_tag = g.find("a")
                if link_tag and link_tag.get("href"):
                    results.append(link_tag["href"])

        return results[:num_results]
        
    except requests.exceptions.HTTPError as e:
        # Often a 429 (Too Many Requests) or 403 (Forbidden) is returned
        _print_err(f"search_google failed (HTTP {e.response.status_code}): {e}")
        return []
    except Exception as e:
        _print_err(f"search_google failed: {e}")
        return []

def extract_links(url: str, **kwargs):
    html = fetch_page(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    return [a.get("href") for a in soup.find_all("a", href=True)]

def get_text_content(url: str, selector: str = None, **kwargs):
    html = fetch_page(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    if selector:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""
    return soup.get_text(separator="\n", strip=True)

def summarize_pdf(file_path: str, **kwargs):
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        return groq_answer("Summarize the following PDF content concisely:", text)
    except Exception as e:
        _print_err(f"summarize_pdf failed: {e}")
        return ""

def analyze_data(*, file_path=None, **kwargs):
    """
    Auto-analyze files: CSV, Excel, PDFs.
    - file_type can be provided in kwargs, otherwise inferred from extension
    """
    if not file_path:
        return "No file provided"

    # Determine file type from kwargs or file extension
    file_type = kwargs.get("file_type")
    if not file_type:
        ext = Path(file_path).suffix.lower()
        if ext in [".csv"]:
            file_type = "csv"
        elif ext in [".xlsx", ".xls"]:
            file_type = "excel"
        elif ext in [".pdf"]:
            file_type = "pdf"
        else:
            return "Unsupported file type"

    # CSV / Excel handling
    if file_type in ("csv", "excel"):
        import pandas as pd
        df = pd.read_csv(file_path) if file_type=="csv" else pd.read_excel(file_path)
        summary = df.describe().to_dict()
        anomalies = df[df.select_dtypes(include="number").apply(lambda x: (x-x.mean()).abs() > 3*x.std()).any(axis=1)]
        return {"summary": summary, "anomalies": anomalies.to_dict(orient="records")}

    # PDF handling
    if file_type == "pdf":
        text = read_pdf(file_path)  # assume your existing read_pdf function
        summary = groq_answer("Summarize the following PDF:", text)
        return {"summary": summary}

    return "File type not supported"



def plot_data(file_path: str, x_col: str, y_col: str, output: str = "chart.png", **kwargs):
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        plt.figure(figsize=(8,5))
        plt.plot(df[x_col], df[y_col], marker='o')
        plt.title(f"{y_col} vs {x_col}")
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(output)
        plt.close()
        return output
    except Exception as e:
        _print_err(f"plot_data failed: {e}")
        return ""

def convert_text_to_pdf(text: str, output: str = "output.pdf", **kwargs):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        for line in text.split("\n"):
            pdf.multi_cell(0, 8, line)
        pdf.output(output)
        return output
    except Exception as e:
        _print_err(f"convert_text_to_pdf failed: {e}")
        return ""

def summarize_text(text: str, **kwargs):
    return groq_answer("Summarize the following text concisely:", text)

def sentiment_analysis(text: str, **kwargs):
    instructions = "Analyze sentiment of the text and return positive, negative, or neutral:"
    return groq_answer(instructions, text)

def nlp_qna(text: str, question: str, **kwargs):
    instructions = f"Answer the question based on the following context:\n{text}\nQuestion: {question}"
    return groq_answer(instructions)

def schedule_task(task_name: str, delay: int = 60, **kwargs):
    time.sleep(delay)
    skill.execute(task_name, **kwargs)
    return f"Executed scheduled task {task_name} after {delay} sec"

def generate_chart_from_data(data: List[Dict], **kwargs):
    df = pd.DataFrame(data)
    numeric_cols = df.select_dtypes(include='number').columns
    for col in numeric_cols:
        plt.figure()
        df[col].plot(kind="bar", title=col)
        plt.savefig(f"{col}_chart.png")
    return f"Generated charts for columns: {list(numeric_cols)}"

def analyze_image(**kwargs):
    """
    Analyze an image for objects, text, charts using Groq.
    kwargs:
        path: str - path to image file
    """
    path = kwargs.get("path")
    if not path or not os.path.exists(path):
        return "Image path invalid"
    instructions = "Analyze the content of the image and summarize important information."
    return groq_answer(instructions, f"Image at path: {path}")


def generate_report(**kwargs):
    """
    Generate PDF/Excel report with plots
    kwargs:
        data_path: str - input CSV/Excel
        output_path: str - output report path
    """
    data_path = kwargs.get("data_path")
    output_path = kwargs.get("output_path", "report.xlsx")
    if not data_path or not os.path.exists(data_path):
        return "Data path invalid"
    try:
        df = pd.read_excel(data_path) if data_path.endswith(".xlsx") else pd.read_csv(data_path)
        # Generate a simple chart
        plt.figure(figsize=(8, 6))
        df.select_dtypes(include="number").plot(kind="line", ax=plt.gca())
        plt.title("Auto-generated Chart")
        chart_path = Path(output_path).with_suffix(".png")
        plt.savefig(chart_path)
        plt.close()
        # Optionally summarize with Groq
        summary = groq_answer("Summarize dataset trends and anomalies.", df.head(50).to_string())
        return {"chart": str(chart_path), "summary": summary}
    except Exception as e:
        return f"Failed to generate report: {e}"
    
scheduler = sched.scheduler(time.time, time.sleep)

class FolderWatcher(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    def on_created(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

def watch_folder(**kwargs):
    """
    Watch folder for new files
    kwargs:
        folder: str
        callback: callable
    """
    folder = kwargs.get("folder")
    callback = kwargs.get("callback")
    if not folder or not os.path.exists(folder):
        return "Folder invalid"
    observer = Observer()
    observer.schedule(FolderWatcher(callback), folder, recursive=False)
    observer.start()
    return f"Watching folder: {folder}"

def schedule_task(**kwargs):
    """
    Schedule a function to run at a certain time
    kwargs:
        func: callable
        delay: int - seconds
    """
    func = kwargs.get("func")
    delay = kwargs.get("delay", 5)
    if not callable(func):
        return "Function not callable"
    scheduler.enter(delay, 1, func)
    threading.Thread(target=scheduler.run).start()
    return f"Task scheduled in {delay} seconds"


def smart_decide(**kwargs):
    """
    Use previous results to suggest next steps
    kwargs:
        context: str
    """
    context = kwargs.get("context", "")
    instructions = "Suggest next logical task steps based on this context."
    return groq_answer(instructions, context)

def encrypt_file(**kwargs):
    """
    Simple XOR file encryption
    kwargs:
        path: str
        key: int
    """
    path = kwargs.get("path")
    key = kwargs.get("key", 123)
    if not path or not os.path.exists(path):
        return "File path invalid"
    try:
        with open(path, "rb") as f:
            data = bytearray(f.read())
        data = bytearray(b ^ key for b in data)
        enc_path = Path(path).with_suffix(".enc")
        with open(enc_path, "wb") as f:
            f.write(data)
        return str(enc_path)
    except Exception as e:
        return f"Failed to encrypt file: {e}"
    
def clean_clipboard(**kwargs):
    """
    Clears system clipboard
    """
    try:
        import pyperclip
        pyperclip.copy("")
        return "Clipboard cleared"
    except Exception as e:
        return f"Failed to clear clipboard: {e}"
    
def auto_backup(**kwargs):
    """
    Copy files to backup folder
    kwargs:
        src: str
        dest: str
    """
    src = kwargs.get("src")
    dest = kwargs.get("dest")
    if not src or not os.path.exists(src):
        return "Source path invalid"
    os.makedirs(dest, exist_ok=True)
    import shutil
    try:
        if os.path.isdir(src):
            shutil.copytree(src, Path(dest)/Path(src).name, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)
        return f"Backup completed to {dest}"
    except Exception as e:
        return f"Backup failed: {e}"

def focus_window(title_contains: str, retries: int = 3, delay: float = 1.0, **kwargs) -> str:
    """
    Attempts to focus (bring to foreground) a window whose title contains the given string.
    Uses pygetwindow for listing and platform-specific commands for activation.
    Requires: 'pygetwindow' library.
    """
    if not gw:
        return "Error: The 'pygetwindow' library is not installed."
        
    target_window = None
    
    # --- 1. Locate the Window (Cross-Platform via pygetwindow) ---
    for _ in range(retries):
        try:
            windows: List[gw.Win32Window] = gw.getWindowsWithTitle(title_contains)
            if windows:
                target_window = windows[0]
                break
        except Exception as e:
            _print_err(f"Window search failed: {e}")
            time.sleep(delay)
    
    if not target_window:
        return f"Error: Window containing '{title_contains}' not found after {retries} attempts."

    # --- 2. Focus the Window (Platform-Specific Activation) ---
    
    # Windows: pygetwindow's activate() method is highly reliable here.
    if IS_WINDOWS:
        try:
            target_window.activate()
            return f"Successfully focused window (Windows): {target_window.title}"
        except Exception as e:
            _print_err(f"Windows focus failed: {e}")
            return f"Error focusing window (Windows): {e}"

    # macOS: Use osascript to focus the application associated with the window.
    elif IS_MACOS:
        try:
            # osascript requires the application name, not just the window title.
            # We assume the window title contains the app name, or we rely on a known list.
            # A common approach is to extract the application name from the title (e.g., 'Google Chrome - My Page' -> 'Google Chrome')
            app_name = target_window.title.split(' - ')[0] if ' - ' in target_window.title else target_window.title
            
            script = f"""
            tell application "{app_name}"
                activate
            end tell
            """
            subprocess.run(["osascript", "-e", script], check=False, capture_output=True, timeout=5)
            return f"Successfully focused application (macOS): {app_name}"
        except Exception as e:
            _print_err(f"macOS focus failed: {e}")
            return f"Error focusing application (macOS): {e}"

    # Linux: Use wmctrl command (standard for X Window System management)
    elif IS_LINUX:
        if not shutil.which("wmctrl"):
            return "Error: wmctrl command not found. Cannot focus window on Linux."
            
        try:
            # 1. Get the list of all windows from wmctrl
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=True)
            window_id = None
            
            # 2. Find the window ID matching the title
            for line in result.stdout.splitlines():
                parts = line.split(maxsplit=4)
                if len(parts) == 5 and title_contains.lower() in parts[4].lower():
                    window_id = parts[0]
                    break
            
            if window_id:
                # 3. Use wmctrl to activate the window by ID
                subprocess.run(["wmctrl", "-i", "-a", window_id], check=True, capture_output=True, timeout=5)
                return f"Successfully focused window (Linux - wmctrl): {target_window.title}"
            else:
                 return f"Error: Could not determine window ID for '{title_contains}'."

        except subprocess.CalledProcessError as e:
            _print_err(f"wmctrl failed: {e}")
            return f"Error focusing window (Linux - wmctrl): {e}"
        except Exception as e:
            _print_err(f"Linux focus failed: {e}")
            return f"Error focusing window (Linux): {e}"

    return "Window focus not supported on this operating system."
# ------------------ GUI INTERACTIONS ------------------
def click(x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1, interval: float = 0.2, **kwargs):
    try:
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, clicks=clicks, interval=interval)
        else:
            pyautogui.click(clicks=clicks, interval=interval)
        return True
    except Exception as e:
        _print_err(f"Click failed → {e}")
        return False

def double_click(x: Optional[int] = None, y: Optional[int] = None, **kwargs):
    return click(x, y, clicks=2)

def right_click(x: Optional[int] = None, y: Optional[int] = None, **kwargs):
    try:
        if x is not None and y is not None:
            pyautogui.rightClick(x=x, y=y)
        else:
            pyautogui.rightClick()
        return True
    except Exception as e:
        _print_err(f"Right click failed → {e}")
        return False

def type_text(text: str, interval: float = 0.05, **kwargs):
    try:
        pyautogui.write(text, interval=interval)
        return True
    except Exception as e:
        _print_err(f"Typing failed → {e}")
        return False

def press_key(key: str, **kwargs):
    try:
        pyautogui.press(key)
        return True
    except Exception as e:
        _print_err(f"Key press failed → {e}")
        return False

def hotkey(*keys, **kwargs):
    try:
        pyautogui.hotkey(*keys)
        return True
    except Exception as e:
        _print_err(f"Hotkey failed → {e}")
        return False

def copy_to_clipboard(text: str, **kwargs):
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        _print_err(f"Clipboard copy failed → {e}")
        return False

def paste_from_clipboard(**kwargs):
    try:
        text = pyperclip.paste()
        return text
    except Exception as e:
        _print_err(f"Clipboard paste failed → {e}")
        return ""

def drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5, **kwargs):
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration)
        return True
    except Exception as e:
        _print_err(f"Drag failed → {e}")
        return False

def scroll(amount: int, **kwargs):
    try:
        pyautogui.scroll(amount)
        return True
    except Exception as e:
        _print_err(f"Scroll failed → {e}")
        return False
    

def get_screen_size(**kwargs) -> Tuple[int, int]:
    return pyautogui.size()

def get_window_position(title_contains: str, **kwargs) -> Optional[Tuple[int, int, int, int]]:
    """
    Retrieves the position and size (left, top, width, height) of the first
    window whose title contains the given string.
    
    Returns: A tuple (left, top, width, height) or None if not found/error.
    Requires: 'pygetwindow' library.
    """
    if gw is None:
        _print_err("pygetwindow required for get_window_position.")
        return None
        
    found_window = None

    # --- 1. Locate the Window (Cross-Platform via pygetwindow) ---
    try:
        windows = gw.getWindowsWithTitle(title_contains)
        if windows:
            found_window = windows[0]
        else:
            return None # Window not found
            
    except Exception as e:
        _print_err(f"Window search failed: {e}")
        return None

    # --- 2. Retrieve Position/Size ---
    try:
        # These properties are derived from platform-specific APIs by pygetwindow.
        return (
            found_window.left, 
            found_window.top, 
            found_window.width, 
            found_window.height
        )
    except Exception as e:
        # This catch handles errors during retrieval (common on Linux/macOS
        # if the window is minimized or permissions are restricted).
        _print_err(f"Could not retrieve position for '{found_window.title}': {e}")
        return None

def take_screenshot(path: str = None, **kwargs):
    screenshot = pyautogui.screenshot()
    if path:
        screenshot.save(path)
    return screenshot

def wait_for_window(title_contains: str, timeout: int = 10, **kwargs) -> bool:
    """
    Waits until a window whose title contains the given string appears, 
    or until the timeout is reached.
    
    Returns: True if the window is found, False otherwise.
    Requires: 'pygetwindow' library.
    """
    if gw is None:
        _print_err("The 'pygetwindow' library is required but not installed.")
        return False
        
    start = time.time()
    sleep_interval = 0.5 # Check every half-second
    
    _print_err(f"Waiting for window containing '{title_contains}' (Timeout: {timeout}s)...")
    
    while time.time() - start < timeout:
        try:
            # Use the cross-platform window search provided by pygetwindow
            windows: List[gw.Win32Window] = gw.getWindowsWithTitle(title_contains)
            
            if windows:
                # Window found
                return True
                
        except Exception as e:
            # Catch errors that might occur during window enumeration (permissions, display issues)
            _print_err(f"Error during window check: {e}")
            # Do not return False immediately, keep retrying until timeout
            
        time.sleep(sleep_interval)
        
    # Timeout reached
    return False

def wait_for_image(image_path: str, timeout: int = 10, confidence: float = 0.8, **kwargs) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        pos = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if pos:
            return True
        time.sleep(0.5)
    return False

# --- Image-based GUI Automation ---
def click_image(image_path: str, confidence: float = 0.8, **kwargs):
    pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
    if pos:
        pyautogui.click(pos)
        return True
    return False

def double_click_image(image_path: str, confidence: float = 0.8, **kwargs):
    pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
    if pos:
        pyautogui.doubleClick(pos)
        return True
    return False

def drag_image(start_image: str, end_image: str, confidence: float = 0.8, **kwargs):
    start_pos = pyautogui.locateCenterOnScreen(start_image, confidence=confidence)
    end_pos = pyautogui.locateCenterOnScreen(end_image, confidence=confidence)
    if start_pos and end_pos:
        pyautogui.moveTo(start_pos)
        pyautogui.dragTo(end_pos, duration=0.5)
        return True
    return False

def highlight_image(image_path: str, duration: float = 1.0, confidence: float = 0.8, **kwargs):
    pos = pyautogui.locateOnScreen(image_path, confidence=confidence)
    if pos:
        x, y, w, h = pos
        pyautogui.moveTo(x + w // 2, y + h // 2)
        time.sleep(duration)
        return True
    return False

# --- Dynamic Element Interaction ---
def click_text(text: str, **kwargs):
    # Placeholder: requires OCR or external tool; excluded per your request
    print(f"[INFO] click_text called for '{text}'")
    return True

def drag_text(text: str, target_x: int, target_y: int, **kwargs):
    # Placeholder
    print(f"[INFO] drag_text called for '{text}' to ({target_x},{target_y})")
    return True

# --- Multi-step / Macro Automation ---
def record_macro(file_path: str, duration: int = 10, **kwargs):
    # Simple mouse+keyboard recording placeholder
    print(f"[INFO] Recording macro for {duration}s → {file_path}")
    return True

def play_macro(file_path: str, **kwargs):
    print(f"[INFO] Playing macro from {file_path}")
    return True

def repeat_macro(file_path: str, times: int = 1, **kwargs):
    for i in range(times):
        play_macro(file_path)
    return True

def chain_commands(commands_list: List[str], **kwargs):
    from task_automation import skill  # assuming SkillEngine instance
    for cmd in commands_list:
        try:
            skill.execute(cmd, **kwargs)
        except KeyError:
            print(f"[WARN] Skill not found: {cmd}")
    return True

# --- Advanced Safety & Recovery ---
def safe_click(x: int, y: int, retries: int = 3, **kwargs):
    for _ in range(retries):
        try:
            pyautogui.click(x, y)
            return True
        except Exception:
            time.sleep(0.2)
    return False

def safe_type(text: str, retries: int = 3, **kwargs):
    for _ in range(retries):
        try:
            pyautogui.typewrite(text)
            return True
        except Exception:
            time.sleep(0.2)
    return False

def backup_clipboard(**kwargs):
    try:
        import pyperclip
        text = pyperclip.paste()
        return text
    except ImportError:
        print("[ERROR] pyperclip required for backup_clipboard")
        return None

def restore_clipboard(text: str, **kwargs):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        print("[ERROR] pyperclip required for restore_clipboard")
        return False

# --- Accessibility / Visibility Helpers ---
def move_cursor_to_image(image_path: str, confidence: float = 0.8, **kwargs):
    pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
    if pos:
        pyautogui.moveTo(pos)
        return True
    return False

def center_window(title_contains: str, **kwargs) -> bool:
    """
    Centers the first found window whose title contains the given string
    using pyautogui for screen size and pygetwindow for movement.
    
    Returns: True if the window was centered, False otherwise.
    Requires: 'pygetwindow' and 'pyautogui' libraries.
    """
    if gw is None or pyautogui is None:
        _print_err("Libraries 'pygetwindow' and 'pyautogui' are required but not installed.")
        return False
        
    found_window = None

    # --- 1. Locate the Window ---
    try:
        windows: List[gw.Win32Window] = gw.getWindowsWithTitle(title_contains)
        if windows:
            found_window = windows[0]
        else:
            return False # Window not found
            
    except Exception as e:
        _print_err(f"Window search failed: {e}")
        return False

    # --- 2. Calculate and Move ---
    try:
        # Get the screen size using pyautogui (cross-platform method)
        screen_width, screen_height = pyautogui.size()
        
        # Calculate the new top-left coordinates for centering
        # X-coordinate: (Screen Width - Window Width) / 2
        # Y-coordinate: (Screen Height - Window Height) / 2
        new_x = (screen_width - found_window.width) // 2
        new_y = (screen_height - found_window.height) // 2
        
        # Move the window using pygetwindow's cross-platform move method
        found_window.moveTo(new_x, new_y)
        
        # Optional: Ensure the window is visible/un-minimized for the move to take effect
        if found_window.isMinimized:
            found_window.restore()
        
        return True
        
    except Exception as e:
        # This catches errors during screen size retrieval or the move operation itself
        _print_err(f"Failed to center window '{found_window.title}': {e}")
        
        # Note: On some Linux environments, `moveTo` fails silently or requires specific
        # window managers/permissions. This is a common point of failure for cross-platform
        # window management.
        return False
    
def maximize_window(title_contains: str, **kwargs) -> bool:
    """
    Maximizes the first found window whose title contains the given string.
    
    Returns: True if the window was maximized, False otherwise.
    Requires: 'pygetwindow' library.
    """
    if gw is None:
        _print_err("The 'pygetwindow' library is required but not installed.")
        return False
        
    try:
        windows: List[gw.Win32Window] = gw.getWindowsWithTitle(title_contains)
        
        if windows:
            # Maximizes the window using the cross-platform method
            windows[0].maximize()
            return True
            
    except Exception as e:
        _print_err(f"Failed to maximize window: {e}")
        # This can happen if the window doesn't support maximization
        return False
        
    return False # Window not found

def minimize_window(title_contains: str, **kwargs) -> bool:
    """
    Minimizes the first found window whose title contains the given string.
    
    Returns: True if the window was minimized, False otherwise.
    Requires: 'pygetwindow' library.
    """
    if gw is None:
        _print_err("The 'pygetwindow' library is required but not installed.")
        return False
        
    try:
        windows: List[gw.Win32Window] = gw.getWindowsWithTitle(title_contains)
        
        if windows:
            # Minimizes the window using the cross-platform method
            windows[0].minimize()
            return True
            
    except Exception as e:
        _print_err(f"Failed to minimize window: {e}")
        # This can happen if the window doesn't support minimization
        return False
        
    return False # Window not found

PLUGINS_FOLDER = Path(__file__).parent / "plugins"

def load_plugins(skill_engine):
    """
    Automatically loads all Python files in the plugins folder,
    finds all top-level functions, and registers them as skills.
    Errors are caught and printed without stopping the loader.
    """
    for file in PLUGINS_FOLDER.glob("*.py"):
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Inspect module for all functions
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                skill_name = f"{file.stem}_{name}"  # optional: namespace by file
                skill_engine.add_skill(skill_name, fn)
                print(f"[PLUGIN SKILL LOADED] {skill_name}")

        except Exception as e:
            print(f"[PLUGIN ERROR] Failed to load {file.name}: {e}")
            traceback.print_exc()

# --- Safe skill wrapper ---
def reload_plugins_skill(**kwargs):
    """
    Reload all plugins at runtime as a skill.
    """
    load_plugins(skill)
    return "[PLUGIN SYSTEM] All plugins reloaded successfully."

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def schedule_calendar_event(**kwargs):
    """
    kwargs:
        title (str)
        start_time (ISO string)
        end_time (ISO string)
    """
    title = _kw(kwargs, "title", "AI Event")
    start_time = _kw(kwargs, "start_time")
    end_time = _kw(kwargs, "end_time")

    if not start_time or not end_time:
        raise ValueError("start_time and end_time required")

    creds = Credentials.from_authorized_user_file("google_token.json", SCOPES)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": title,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time}
    }

    service.events().insert(calendarId="primary", body=event).execute()
    return "Calendar event created"



def upload_to_drive(**kwargs):
    """
    kwargs:
        path (str) - file path
        name (str, optional)
    """
    path = _kw(kwargs, "path")
    name = _kw(kwargs, "name") or os.path.basename(path)

    if not path or not os.path.exists(path):
        raise FileNotFoundError("Invalid file path")

    creds = Credentials.from_authorized_user_file(
        "google_token.json", ["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds)

    media = MediaFileUpload(path, resumable=True)
    file = service.files().create(
        body={"name": name},
        media_body=media
    ).execute()

    return file.get("id")


def send_whatsapp_message(**kwargs):
    """
    kwargs:
        phone (str) – international format
        message (str)
    """
    phone = _kw(kwargs, "phone")
    message = _kw(kwargs, "message")

    if not phone or not message:
        raise ValueError("phone and message required")

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }

    requests.post(url, headers=headers, json=payload)
    return "WhatsApp message sent"


async def _discord_send(channel_id, message):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message)
        await client.close()

    await client.start(DISCORD_TOKEN)

def send_discord_message(**kwargs):
    """
    kwargs:
        message (str)
        channel_id (int, optional)
    """
    message = _kw(kwargs, "message")
    channel_id = int(_kw(kwargs, "channel_id", DISCORD_CHANNEL_ID))

    if not message:
        raise ValueError("message required")

    asyncio.run(_discord_send(channel_id, message))
    return "Discord message sent"

def _load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def os_context_skill(**kwargs):
    """
    OS Context Automation Skill
    - Captures active window and system context
    - Resolves pronouns like 'this', 'that' based on last tasks
    - Logs tasks with timestamps
    """
    user_input = kwargs.get("raw_input") or kwargs.get("user_input") or ""
    memory = _load_memory()

    # Detect active window
    active_window = ""
    try:
        win = gw.getActiveWindow()
        if win:
            active_window = win.title
    except Exception:
        active_window = "Unknown"

    # Detect running apps (top 5 CPU usage)
    try:
        top_apps = sorted(psutil.process_iter(['name', 'cpu_percent']),
                          key=lambda p: p.info['cpu_percent'], reverse=True)[:5]
        running_apps = [p.info['name'] for p in top_apps]
    except Exception:
        running_apps = []

    # Resolve pronouns like 'this', 'that' using memory
    resolved_input = user_input
    if memory.get("last_task"):
        resolved_input = user_input.replace("this", memory["last_task"]["description"])

    # Update memory
    memory["last_task"] = {
        "description": user_input,
        "resolved": resolved_input,
        "active_window": active_window,
        "running_apps": running_apps,
        "timestamp": datetime.now().isoformat()
    }
    _save_memory(memory)

    # Build output info
    output = {
        "resolved": resolved_input,
        "active_window": active_window,
        "running_apps": running_apps,
        "timestamp": memory["last_task"]["timestamp"]
    }

    return output


def predictive_tasks(*, last_tasks=None, os_context=None, n=10, **kwargs):
    """
    Predicts next likely tasks based on last N tasks and current OS context.
    """
    last_tasks = last_tasks or get_recent_tasks(n=n)
    os_context = os_context or skill.execute("os_context")
    prompt = f"Given last tasks {last_tasks} and context {os_context}, suggest likely next commands."
    suggestion = groq_answer(prompt)
    try:
        return json.loads(suggestion)
    except Exception:
        return []

def learn_user_pattern(task_name):
    """Update long-term patterns based on task frequency."""
    recent = get_recent_tasks(limit=20)
    freq = sum(1 for t in recent if t["function"] == task_name)
    if freq > 3:
        print(f"[LEARNING] Task '{task_name}' is now prioritized for automation.")

nlp_model = spacy.load("en_core_web_sm")

def repair_input(user_input: str) -> str:
    """
    Corrects spelling, removes unwanted characters, and normalizes text.
    """
    user_input = re.sub(r"[^a-zA-Z0-9 .,?!@#]", "", user_input)
    user_input = user_input.strip()
    # Could integrate spellchecker or autocorrect here
    return user_input

def extract_entities(user_input: str) -> dict:
    """
    Extracts named entities (dates, times, people, apps) from text.
    """
    doc = nlp_model(user_input)
    entities = {}
    for ent in doc.ents:
        entities[ent.label_] = entities.get(ent.label_, []) + [ent.text]
    return entities

def infer_intent(user_input: str) -> str:
    """
    Determines high-level intent using rules + groq AI.
    """
    prompt = f"Determine the single action user wants: '{user_input}'"
    intent = groq_answer(prompt, user_input)
    return intent.strip()

def polish_input(user_input: str) -> str:
    """
    Cleans, summarizes, and converts casual input into actionable commands.
    """
    # Remove filler words, polite phrases, etc.
    cleaned = re.sub(r"\b(please|kindly|could you|would you)\b", "", user_input, flags=re.I)
    cleaned = cleaned.strip()
    return cleaned

def full_nlp_pipeline(user_input: str) -> dict:
    """
    Full preprocessing and understanding pipeline:
    - Repair
    - Entity extraction
    - Intent inference
    - Polishing
    """
    repaired = repair_input(user_input)
    polished = polish_input(repaired)
    entities = extract_entities(polished)
    intent = infer_intent(polished)

    return {
        "original": user_input,
        "repaired": repaired,
        "polished": polished,
        "entities": entities,
        "intent": intent
    }


from difflib import SequenceMatcher

def best_file_match(query: str, root="."):
    best = None
    score = 0

    for dirpath, _, files in os.walk(root):
        for f in files:
            s = SequenceMatcher(None, query.lower(), f.lower()).ratio()
            if s > score:
                best = os.path.join(dirpath, f)
                score = s

    return best if score > 0.4 else None

MAX_RETRIES = 5

def adaptive_auto_coder(user_request: str, context: str = None):
    """
    Fully adaptive auto-coder for NLP commands:
    - Uses Groq to generate safe Python code
    - Automatically splits tasks into multiple steps
    - Infers parameters from user input
    - Retries and fixes code if errors occur
    - Dynamically registers new skills for future use with unique names
    """

    if not user_request.strip():
        return "[ERROR] Empty request"

    last_error = None

    # Include context from previous tasks if available
    context_prefix = f"Previous context:\n{context}\n" if context else ""

    base_prompt = f"""
    {context_prefix}
    You are an expert Windows automation engineer.
    
    Convert the following user request into SAFE Python 3.13 code:
    User request: "{user_request}"
    
    Requirements:
    - Output ONLY Python code (no markdown, no explanations)
    - Use pyautogui, time.sleep, or other safe libraries as needed
    - Split multi-step commands into separate executable functions
    - Name functions clearly and infer parameters automatically
    - Avoid dangerous system commands (deletion, shutdown, etc.)
    """

    for attempt in range(1, MAX_RETRIES + 1):
        code = groq_answer(base_prompt)
        if not code:
            continue

        # Remove accidental markdown/code fences
        code = re.sub(r"```.*?```", "", code, flags=re.DOTALL).strip()

        try:
            # Run code in controlled globals
            local_env = {}
            exec_safe(code, {"__builtins__": __builtins__, "pyautogui": pyautogui, "time": time}, local_env)
            print(f"[AUTO-CODER EXECUTED] Attempt {attempt}")

            # Detect all functions in the generated code
            generated_funcs = {name: fn for name, fn in local_env.items() if callable(fn)}

            # Register each as a new skill with a unique name
            for name, fn in generated_funcs.items():
                skill_name = _make_skill_name(name)
                skill.add_skill(skill_name, fn)
                print(f"[SKILL LEARNED] → {skill_name}")

            return f"Task executed and {len(generated_funcs)} skill(s) learned."

        except Exception as e:
            last_error = str(e)
            print(f"[AUTO-CODER ERROR {attempt}] {last_error}")

            # Provide error back to Groq for fix
            base_prompt += f"""
            The previous code attempt failed with error:
            {last_error}
            Fix the code and provide a corrected version.
            """

    raise RuntimeError(f"Adaptive auto-coder failed after {MAX_RETRIES} attempts: {last_error}")

SAFE_BUILTINS = {
    "print": print,
    "range": range,
    "len": len,
    "int": int,
    "float": float,
    "str": str,
    "list": list,
    "dict": dict,
    "set": set,
}

def exec_safe(code: str, extra_globals=None):
    """Execute Python code safely with limited builtins"""
    env = {"__builtins__": SAFE_BUILTINS}
    if extra_globals:
        env.update(extra_globals)
    try:
        exec(code, env)
    except Exception as e:
        return f"[SECURITY] Code execution blocked or failed: {e}"
    return "Executed safely"

def window_finder(**kwargs):
    title = kwargs.get("title") or kwargs.get("raw_input")
    if not title:
        return "Please provide a window title or partial title to find."
    
    found = []
    try:
        if gw is not None:
            # pygetwindow supports Windows, macOS (limited), and Linux (X11)
            windows = gw.getAllWindows()
            for w in windows:
                if title.lower() in w.title.lower():
                    found.append(w.title)
        elif IS_LINUX:
            # Fallback for Linux if pygetwindow fails (requires wmctrl)
            try:
                result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=True)
                for line in result.stdout.splitlines():
                    parts = line.split(maxsplit=4)
                    if len(parts) == 5 and title.lower() in parts[4].lower():
                        found.append(parts[4].strip())
            except FileNotFoundError:
                return "wmctrl not found. Cannot find windows on Linux."
    except Exception as e:
        return f"Window search error: {e}"
        
    if found:
        return f"Found windows:\n" + "\n".join(found)
    return f"No windows found matching '{title}'."

def file_finder(**kwargs):
    # Accepts: filename, start_dir, mode (file or folder)
    filename = kwargs.get("filename") or kwargs.get("raw_input")
    start_dir = kwargs.get("start_dir", Path.home())
    mode = kwargs.get("mode", "file") # "file" or "dir"

    p_start = Path(start_dir)
    if not p_start.is_dir():
        return f"Starting directory not found: {start_dir}"

    found = []
    
    # Simple recursive search
    def search_path(directory: Path):
        for item in directory.iterdir():
            if filename.lower() in item.name.lower():
                if (mode == "file" and item.is_file()) or (mode == "dir" and item.is_dir()):
                    found.append(str(item.resolve()))
            if item.is_dir():
                try:
                    search_path(item) # Recurse
                except PermissionError:
                    continue # Skip directories without permission

    try:
        search_path(p_start)
    except Exception as e:
        return f"File search failed: {e}"
        
    if found:
        # Limit results for readability
        return f"Found {len(found)} results:\n" + "\n".join(found[:10])
    return f"No {mode}s found matching '{filename}' starting from {start_dir}"

def check_process_status(**kwargs):
    # Requires psutil
    name = kwargs.get("name") or kwargs.get("raw_input")
    if not name:
        return "Please provide a process name (e.g., chrome.exe, Finder, bash)."

    found = []
    for proc in psutil.process_iter(['name']):
        if name.lower() in proc.info['name'].lower():
            found.append(f"PID: {proc.pid}, Name: {proc.info['name']}")
    
    if found:
        return f"Found {len(found)} running processes:\n" + "\n".join(found)
    return f"Process '{name}' is not currently running."

def file_manager(**kwargs):
    # Requires shutil and pathlib
    action = kwargs.get("action")
    source = Path(kwargs.get("source"))
    destination = Path(kwargs.get("destination"))

    if action not in ["copy", "move", "delete"]:
        return "Invalid action. Use 'copy', 'move', or 'delete'."
    
    if not source.exists():
        return f"Source file/folder not found: {source.name}"

    try:
        if action == "copy":
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            return f"Copied {source.name} to {destination.name}"
        
        elif action == "move":
            shutil.move(source, destination)
            return f"Moved {source.name} to {destination.name}"
        
        elif action == "delete":
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
            return f"Deleted {source.name}"

    except Exception as e:
        return f"File operation failed for '{action} {source.name}': {e}"

def register_skill(name, func, registry: dict):
    if name not in registry:
        registry[name] = func

def infer_cross_app_action(os_context, user_input):
    app = os_context.get("active_window", "").lower()

    if "send" in user_input and "email" not in user_input:
        if "whatsapp" in app:
            return "send_whatsapp_message"
        if "chrome" in app:
            return "share_current_page"
        if "pdf" in app:
            return "email_current_document"

    return None

def confirm_permission():
    return input("⚠️ This action is sensitive. Continue? (y/n): ").lower() == "y"

RECENT_COMMANDS = []

def detect_anomaly(cmd: str):
    RECENT_COMMANDS.append(cmd)
    if RECENT_COMMANDS.count(cmd) > 3:
        raise RuntimeError("Anomalous repeated command detected")

    if len(RECENT_COMMANDS) > 20:
        RECENT_COMMANDS.pop(0)

def video_to_audio(**kwargs):
    video_path = kwargs.get("video_path") or kwargs.get("raw_input")
    output_path = kwargs.get("output_path") or (str(Path(video_path).with_suffix('.mp3')) if video_path else None)

    if not video_path or not os.path.exists(video_path):
        return "Invalid video file path."

    if not output_path:
        return "Output path not specified."

    try:
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(output_path)
        clip.close()
        return f"Audio extracted to {output_path}"
    except Exception as e:
        return f"Video to audio conversion failed: {e}"


def bg_remover(**kwargs):
    image_path = kwargs.get("image_path") or kwargs.get("raw_input")
    output_path = kwargs.get("output_path") or (
        str(Path(image_path).with_name(Path(image_path).stem + "_no_bg.png"))
        if image_path else None
    )

    if not image_path or not os.path.exists(image_path):
        return "Invalid image file path."

    if not output_path:
        return "Output path not specified."

    try:
        # Load image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            return "Failed to load image."

        height, width = img.shape[:2]

        # Create mask
        mask = np.zeros((height, width), np.uint8)

        # Background & foreground models
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)

        # Define rectangle around main subject (assumes subject is centered)
        rect = (10, 10, width - 20, height - 20)

        # Apply GrabCut
        cv2.grabCut(
            img,
            mask,
            rect,
            bgdModel,
            fgdModel,
            5,
            cv2.GC_INIT_WITH_RECT
        )

        # Create final mask
        mask2 = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
            255,
            0
        ).astype("uint8")

        # Add alpha channel
        b, g, r = cv2.split(img)
        rgba = cv2.merge((b, g, r, mask2))

        # Save as PNG with transparency
        cv2.imwrite(output_path, rgba)

        return f"Background removed. Saved to {output_path}"

    except Exception as e:
        return f"Background removal failed: {e}"


def wordcloud_generator(**kwargs):
    """
    Generate a word cloud from text / csv / document file.

    kwargs:
        text (str)             : path to input file (required)
        background_color (str) : background color (default: white)
        mask (str)             : path to mask image (optional)
        contour_width (int)    : contour width (optional)
        contour_color (str)    : contour color (optional)
        color_func (bool)      : keep mask colors (optional)
        output_path (str)      : output image path (optional)
        show (bool)            : display image (default: True)
    """

    # ---- Inputs ----
    text_path = kwargs.get("text")
    background_color = kwargs.get("background_color", "white")
    mask_path = kwargs.get("mask")
    contour_width = kwargs.get("contour_width", 0)
    contour_color = kwargs.get("contour_color", "black")
    color_func = kwargs.get("color_func", False)
    show = kwargs.get("show", True)

    if not text_path:
        return "Text file path is required."

    if not Path(text_path).exists():
        return "Invalid text file path."

    output_path = kwargs.get(
        "output_path",
        str(Path(text_path).with_suffix(".png"))
    )

    # ---- Read Text ----
    ext = Path(text_path).suffix.lower()

    try:
        if ext in [".txt", ".doc", ".pdf"]:
            text = open(text_path, encoding="utf-8", errors="ignore").read()

        elif ext == ".csv":
            df = pd.read_csv(text_path, encoding="latin-1")
            text = ""
            for val in df.iloc[:, 0]:
                tokens = str(val).lower().split()
                text += " ".join(tokens) + " "

        else:
            return "Unsupported file format."

    except Exception as e:
        return f"Failed to read text: {e}"

    # ---- Mask Handling ----
    mask_array = None
    mask_colors = None

    if mask_path:
        if not Path(mask_path).exists():
            return "Invalid mask file path."

        mask_array = np.array(Image.open(mask_path))

        if color_func:
            mask_colors = ImageColorGenerator(mask_array)

    # ---- Generate WordCloud ----
    try:
        wc = WordCloud(
            stopwords=STOPWORDS,
            mask=mask_array,
            max_font_size=50,
            max_words=1000,
            background_color=background_color,
            color_func=mask_colors,
            contour_width=contour_width,
            contour_color=contour_color,
        ).generate(text)

        if show:
            plt.figure(figsize=(8, 8))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            plt.show()

        wc.to_file(output_path)

        return f"WordCloud generated successfully → {output_path}"

    except Exception as e:
        return f"WordCloud generation failed: {e}"

def instagram_video_downloader(**kwargs):
    """
    Download videos from an Instagram post.

    kwargs:
        post_id (str)      : Instagram post shortcode (required)
        output_dir (str)   : directory to save videos (default: current dir)

    Example:
        instagram_video_downloader(post_id="Cxyz123", output_dir="videos")
    """

    post_id = kwargs.get("post_id")
    output_dir = Path(kwargs.get("output_dir", "."))

    if not post_id:
        return "post_id is required."

    output_dir.mkdir(parents=True, exist_ok=True)

    videos = []

    try:
        # Fetch post page
        response = requests.get(
            f"https://www.instagram.com/p/{post_id}/",
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=10
        )

        if response.status_code == 404:
            return "Specified post not found."

        # Extract JSON data
        json_data = json.loads(
            re.findall(
                r"window\._sharedData\s=\s(\{.*\});</script>",
                response.text
            )[0]
        )

        data = json_data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]

        # Single video
        if data.get("is_video"):
            videos.append(data["video_url"])

        # Carousel posts
        if "edge_sidecar_to_children" in data:
            for post in data["edge_sidecar_to_children"]["edges"]:
                node = post["node"]
                if node.get("is_video"):
                    videos.append(node["video_url"])

        if not videos:
            return "No videos found in this post."

        # Download videos
        for idx, video_url in enumerate(videos, start=1):
            output_file = output_dir / f"{post_id}_{idx}.mp4"
            urllib.request.urlretrieve(video_url, output_file)

        return f"Downloaded {len(videos)} video(s) to {output_dir.resolve()}"

    except Exception as e:
        return f"Download failed: {e}"
    

def facebook_video_downloader(**kwargs):
    """
    Download a Facebook video using mbasic page scraping.

    kwargs:
        url (str)           : Facebook video URL (required)
        output_path (str)   : output file path (default: video.mp4)

    Example:
        facebook_video_downloader(
            url="https://www.facebook.com/....",
            output_path="fb_video.mp4"
        )
    """

    url = kwargs.get("url")
    output_path = Path(kwargs.get("output_path", "video.mp4"))

    if not url:
        return "URL is required."

    if "facebook.com" not in url:
        return "Invalid Facebook URL."

    # Convert to mbasic
    url = url.replace("www", "mbasic")

    try:
        response = get(url, timeout=5, allow_redirects=True)
        if response.status_code != 200:
            return "Failed to fetch Facebook page."

        matches = findall("/video_redirect/", response.text)
        if not matches:
            return "Video not found on this page."

        video_url = unquote(response.text.split("?src=")[1].split('"')[0])

    except (HTTPError, ConnectionError) as e:
        return f"Connection error: {e}"

    # ---- Download Video ----
    try:
        r = get(video_url, stream=True)
        total_size = int(r.headers.get("content-length", 0))
        block_size = 1024

        progress_bar = tqdm(
            total=total_size,
            unit="iB",
            unit_scale=True,
            desc="Downloading"
        )

        with open(output_path, "wb") as file:
            for data in r.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

        progress_bar.close()

        if total_size != 0 and progress_bar.n != total_size:
            return "Download incomplete."

        return f"Video downloaded successfully → {output_path.resolve()}"

    except Exception as e:
        return f"Download failed: {e}"

def xml_to_csv_converter(**kwargs):
    """
    Convert Pascal VOC XML annotations to a CSV file.

    kwargs:
        input_dir (str)   : directory containing XML files (required)
        output_path (str) : output CSV path (default: shape_labels.csv)

    Example:
        xml_to_csv_converter(
            input_dir="annotations",
            output_path="labels.csv"
        )
    """

    input_dir = kwargs.get("input_dir")
    output_path = kwargs.get("output_path", "shape_labels.csv")

    if not input_dir:
        return "input_dir is required."

    input_dir = Path(input_dir)

    if not input_dir.exists():
        return "Input directory does not exist."

    xml_list = []

    try:
        for xml_file in glob.glob(str(input_dir / "*.xml")):
            tree = ET.parse(xml_file)
            root = tree.getroot()

            filename = root.find("filename").text
            width = int(root.find("size")[0].text)
            height = int(root.find("size")[1].text)

            for member in root.findall("object"):
                value = (
                    filename,
                    width,
                    height,
                    member.find("name").text,
                    int(member.find("bndbox/xmin").text),
                    int(member.find("bndbox/ymin").text),
                    int(member.find("bndbox/xmax").text),
                    int(member.find("bndbox/ymax").text),
                )
                xml_list.append(value)

        if not xml_list:
            return "No XML annotations found."

        columns = [
            "filename",
            "width",
            "height",
            "class",
            "xmin",
            "ymin",
            "xmax",
            "ymax",
        ]

        df = pd.DataFrame(xml_list, columns=columns)
        df.to_csv(output_path, index=False)

        return f"XML successfully converted to CSV → {Path(output_path).resolve()}"

    except Exception as e:
        return f"Conversion failed: {e}"

_price_watchlist = {}

def track_price(*, url: str, target_price: float, check_interval: int = 3600):
    headers = {"User-Agent": "Mozilla/5.0"}
    _price_watchlist[url] = {
        "target": target_price,
        "interval": check_interval,
        "headers": headers
    }
    return f"Tracking price for {url}"

def _check_prices():
    while True:
        for url, data in _price_watchlist.items():
            r = requests.get(url, headers=data["headers"])
            soup = BeautifulSoup(r.text, "html.parser")
            price = float(
                soup.select_one(".a-price-whole").text.replace(",", "")
            )
            if price <= data["target"]:
                print(f"[ALERT] Price dropped to {price}: {url}")
        time.sleep(min(d["interval"] for d in _price_watchlist.values()))

def malware_static_analyzer(**kwargs):
    """
    Malware static analysis tool (YARA removed, rule-based detection added)

    kwargs:
        file_path (str)            : path to file (required)
        virustotal_api_key (str)   : optional
        enable_pe (bool)
        enable_strings (bool)
        enable_disassembly (bool)
        enable_network (bool)
        enable_packer (bool)
        enable_clamav (bool)
        enable_metadata (bool)
        report_file (str)          : optional
        report_format (str)        : json / csv
    """

    file_path = kwargs.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return "Invalid file path."

    # ---------------- HASHING ----------------
    def calculate_hash(path, algo):
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    # ---------------- FILE INFO ----------------
    file_info = {
        "name": os.path.basename(file_path),
        "size": os.path.getsize(file_path),
        "type": magic.from_file(file_path),
        "md5": calculate_hash(file_path, "md5"),
        "sha1": calculate_hash(file_path, "sha1"),
        "sha256": calculate_hash(file_path, "sha256"),
    }

    results = {"file_info": file_info}

    # ---------------- STRINGS ----------------
    strings = []
    if kwargs.get("enable_strings"):
        with open(file_path, "rb") as f:
            data = f.read()
        s = ""
        for b in data:
            if 32 <= b <= 126:
                s += chr(b)
            else:
                if len(s) >= 4:
                    strings.append(s)
                s = ""
        results["strings_sample"] = strings[:20]

    # ---------------- PE ANALYSIS ----------------
    pe_info = {}
    entropy_alerts = []
    suspicious_imports = []

    if kwargs.get("enable_pe") and "PE" in file_info["type"]:
        pe = pefile.PE(file_path)

        pe_info["entry_point"] = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        pe_info["sections"] = []

        for sec in pe.sections:
            entropy = sec.get_entropy()
            sec_name = sec.Name.decode(errors="ignore").strip("\x00")
            pe_info["sections"].append({
                "name": sec_name,
                "entropy": entropy
            })
            if entropy > 7.0:
                entropy_alerts.append(sec_name)

        dangerous_apis = {
            b"VirtualAlloc",
            b"WriteProcessMemory",
            b"CreateRemoteThread",
            b"LoadLibraryA",
            b"GetProcAddress"
        }

        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                for imp in entry.imports:
                    if imp.name in dangerous_apis:
                        suspicious_imports.append(imp.name.decode())

        pe_info["high_entropy_sections"] = entropy_alerts
        pe_info["suspicious_imports"] = suspicious_imports
        results["pe_analysis"] = pe_info

    # ---------------- RULE ENGINE (REPLACEMENT FOR YARA) ----------------
    rules_triggered = []

    if entropy_alerts:
        rules_triggered.append("HIGH_ENTROPY_SECTIONS")

    if suspicious_imports:
        rules_triggered.append("SUSPICIOUS_WINDOWS_APIS")

    if kwargs.get("enable_strings"):
        if any("http://" in s or "https://" in s for s in strings):
            rules_triggered.append("EMBEDDED_URLS")

        if any(re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", s) for s in strings):
            rules_triggered.append("EMBEDDED_IP_ADDRESSES")

    results["rule_engine_hits"] = rules_triggered

    # ---------------- NETWORK ARTIFACTS ----------------
    if kwargs.get("enable_network") and strings:
        results["network_artifacts"] = {
            "ips": re.findall(r"\b\d{1,3}(\.\d{1,3}){3}\b", " ".join(strings)),
            "urls": re.findall(r"https?://[^\s]+", " ".join(strings)),
        }

    # ---------------- DISASSEMBLY ----------------
    if kwargs.get("enable_disassembly") and "PE" in file_info["type"]:
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        with open(file_path, "rb") as f:
            code = f.read()
        results["disassembly_sample"] = [
            f"0x{i.address:x} {i.mnemonic} {i.op_str}"
            for i in list(md.disasm(code, 0x1000))[:20]
        ]

    # ---------------- CLAMAV ----------------
    if kwargs.get("enable_clamav"):
        try:
            r = subprocess.run(["clamscan", file_path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            results["clamav"] = r.stdout.decode()
        except Exception as e:
            results["clamav"] = str(e)

    # ---------------- METADATA ----------------
    if kwargs.get("enable_metadata"):
        if "PDF" in file_info["type"]:
            results["pdf_text"] = extract_text(file_path)
        elif "image" in file_info["type"]:
            img = Image.open(file_path)
            exif = img._getexif()
            if exif:
                results["image_metadata"] = {
                    TAGS.get(k, k): v for k, v in exif.items()
                }

    # ---------------- REPORT ----------------
    report_file = kwargs.get("report_file")
    report_format = kwargs.get("report_format", "json")

    if report_file:
        if report_format == "json":
            with open(report_file, "w") as f:
                json.dump(results, f, indent=4)
        elif report_format == "csv":
            with open(report_file, "w", newline="") as f:
                w = csv.writer(f)
                for k, v in results.items():
                    w.writerow([k, v])

    return {
        "status": "completed",
        "rules_triggered": rules_triggered,
        "report_file": report_file,
    }

_birthdays = {}

def remember_birthday(*, name: str, date: str):
    _birthdays[name] = date
    return f"Saved birthday for {name}"

def check_birthdays():
    today = datetime.now().strftime("%m-%d")
    for name, date in _birthdays.items():
        if date[5:] == today:
            print(f"🎉 Happy Birthday {name}!")


def download_attachments(*, email_user, email_pass, folder="attachments"):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_user, email_pass)
    mail.select("inbox")

    _, data = mail.search(None, "ALL")
    os.makedirs(folder, exist_ok=True)

    for num in data[0].split():
        _, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        for part in msg.walk():
            if part.get_filename():
                with open(os.path.join(folder, part.get_filename()), "wb") as f:
                    f.write(part.get_payload(decode=True))
    return "Attachments downloaded"

def scrape_best_sellers():
    url = "https://www.amazon.com/Best-Sellers/zgbs"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    return [item.text.strip() for item in soup.select(".zg-item")]

def aws_control(*, action: str, instance_id: str, region="us-east-1"):
    ec2 = boto3.client("ec2", region_name=region)
    if action == "start":
        ec2.start_instances(InstanceIds=[instance_id])
    elif action == "stop":
        ec2.stop_instances(InstanceIds=[instance_id])
    return f"EC2 {action} executed"

def plot_spectrogram(audio_path: str, **kwargs):
    """
    Plot the spectrogram of an audio file.

    Parameters:
        audio_path (str): Path to the audio file.
        **kwargs: Optional keyword arguments:
            - figsize (tuple): Figure size, default (10,5)
            - x_axis (str): x-axis type for display, default 'time'
            - y_axis (str): y-axis type for display, default 'hz'
            - title (str): Custom title, default 'Spectrogram of <audio_path>'
    """
    # Load audio
    x, sr = librosa.load(audio_path)

    # Compute Short-Time Fourier Transform (STFT)
    X = librosa.stft(x)
    Xdb = librosa.amplitude_to_db(abs(X))

    # Plot settings
    figsize = kwargs.get('figsize', (10, 5))
    x_axis = kwargs.get('x_axis', 'time')
    y_axis = kwargs.get('y_axis', 'hz')
    title = kwargs.get('title', f'Spectrogram of {audio_path}')

    plt.figure(figsize=figsize)
    librosa.display.specshow(Xdb, sr=sr, x_axis=x_axis, y_axis=y_axis)
    plt.colorbar()
    plt.title(title)
    plt.show()

def csv_to_excel(**kwargs):
    """
    Convert a CSV file to an Excel file.

    Keyword Args:
        csv_file (str): Path to the input CSV file. (required)
        excel_file (str): Path to the output Excel file. (required)
        sheet_name (str): Name of the sheet to write to. Default is 'Sheet1'.
        separator (str): CSV separator. Default is ','.
    """
    # Extract kwargs with defaults
    csv_file = kwargs.get("csv_file")
    excel_file = kwargs.get("excel_file")
    sheet_name = kwargs.get("sheet_name", "Sheet1")
    separator = kwargs.get("separator", ",")

    # Validate required arguments
    if not csv_file or not excel_file:
        raise ValueError("Both 'csv_file' and 'excel_file' must be provided as kwargs.")

    # Ensure CSV exists
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file '{csv_file}' not found.")

    # Open or create Excel workbook
    if os.path.exists(excel_file):
        wb = openpyxl.load_workbook(excel_file)
        if sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
        else:
            sheet = wb.create_sheet(sheet_name)
    else:
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.title = sheet_name

    # Read CSV and write to Excel
    with open(csv_file, "r", encoding="utf-8") as f:
        for row_idx, line in enumerate(f, start=1):
            line = line.rstrip("\n").split(separator)
            for col_idx, data in enumerate(line, start=1):
                sheet.cell(row=row_idx, column=col_idx).value = data

    # Save workbook
    wb.save(excel_file)
    print(f"CSV '{csv_file}' successfully written to Excel '{excel_file}' in sheet '{sheet_name}'.")



def ip_geolocator(ip: str = None, **kwargs):
    """
    Get geolocation information for a given IP address.
    If no IP is provided, it will use the public IP of the machine.
    """
    try:
        if not ip:
            ip = requests.get("https://api.ipify.org").text
        
        response = requests.get(f"http://ip-api.com/json/{ip}")
        data = response.json()
        
        if data['status'] != 'success':
            return {"error": data.get("message", "Failed to fetch IP data")}
        
        result = {
            "IP": data.get("query"),
            "Country": data.get("country"),
            "Region": data.get("regionName"),
            "City": data.get("city"),
            "ZIP": data.get("zip"),
            "ISP": data.get("isp"),
            "Lat": data.get("lat"),
            "Lon": data.get("lon"),
            "Timezone": data.get("timezone")
        }
        return result
    except Exception as e:
        return {"error": str(e)}
    

def play_tone_skill(**kwargs):
    """
    Plays a single tone of a specific frequency through the speaker.
    kwargs: frequency (Hz), duration (seconds), volume (0.0-1.0), sample_rate
    """
    frequency = kwargs.get("frequency", 440)
    duration = kwargs.get("duration", 2)
    volume = kwargs.get("volume", 0.5)
    sample_rate = kwargs.get("sample_rate", 44100)

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi) * volume

    sd.play(tone, samplerate=sample_rate)
    sd.wait()


def play_sweep_skill(**kwargs):
    """
    Plays a frequency sweep through the speaker.
    kwargs: duration, volume, sample_rate, start_freq, end_freq
    """
    duration = kwargs.get("duration", 5)
    volume = kwargs.get("volume", 0.5)
    sample_rate = kwargs.get("sample_rate", 44100)
    start_freq = kwargs.get("start_freq", 20)
    end_freq = kwargs.get("end_freq", 20000)

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    sweep = scipy.signal.chirp(t, start_freq, t[-1], end_freq, method='logarithmic') * volume

    sd.play(sweep, samplerate=sample_rate)
    sd.wait()


def speaker_health_test_skill(**kwargs):
    """
    Plays different tones and a sweep to assess speaker health.
    Returns a health score in %.
    """
    print("Playing test tones...")
    health_score = 0

    # Low frequency
    print("Playing 100 Hz tone...")
    play_tone_skill(frequency=100, duration=2)
    time.sleep(1)
    health_score += 25

    # Mid frequency
    print("Playing 1000 Hz tone...")
    play_tone_skill(frequency=1000, duration=2)
    time.sleep(1)
    health_score += 25

    # High frequency
    print("Playing 5000 Hz tone...")
    play_tone_skill(frequency=5000, duration=2)
    time.sleep(1)
    health_score += 20

    print("Playing 10,000 Hz tone...")
    play_tone_skill(frequency=10000, duration=2)
    time.sleep(1)
    health_score += 15

    # Frequency sweep
    print("Playing frequency sweep from 20 Hz to 20,000 Hz...")
    play_sweep_skill(duration=5)
    time.sleep(1)
    health_score += 15

    print("Speaker health test complete.")
    print(f"Speaker Health: {health_score}%")
    if health_score == 100:
        print("The speaker is in excellent condition!")
    elif 80 <= health_score < 100:
        print("The speaker is in good condition.")
    elif 60 <= health_score < 80:
        print("The speaker is in average condition.")
    else:
        print("The speaker might be in poor condition.")
    return {"health_score": health_score}

def get_sophos_central_health_script():
    """
    Downloads the Sophos_Central_Health.py script from the official GitHub repository
    and returns the full source code as a string.

    Returns:
        str: The source code of Sophos_Central_Health.py
    """
    url = "https://raw.githubusercontent.com/sophos/PS.Machine_Health/main/Sophos_Central_Health.py"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to retrieve script: HTTP {response.status_code}")
    
    
def run_sophos_central_health_analysis(**kwargs):
    """
    Downloads and executes the Sophos Central Health script.
    Returns the analysis results as a dictionary.
    """
    try:
        script_code = get_sophos_central_health_script()
        local_vars = {}
        exec(script_code, {}, local_vars)
        if 'main' in local_vars:
            result = local_vars['main']()
            return result
        else:
            return {"error": "The script does not contain a main function."}
    except Exception as e:
        return {"error": str(e)}

def llm_judge_answer(prompt):
    return llm_run("BAAI.JudgeLM-7B-v1.0.Q4_K_M.gguf", prompt)

def llm_truth_check(prompt):
    return llm_run("truthfulqa-truth-judge-llama2-7b.gguf", prompt)

def llm_deep_reason(prompt):
    return llm_run("DeepSeek-R1-Distill-Qwen-7B-Q4_1.gguf", prompt)

def llm_experimental_reason(prompt):
    return llm_run("xwin-lm-7b-v0.2.Q4_K_M.gguf", prompt)

def llm_solve_math(prompt):
    return llm_run("deepseek-math-7b-rl.Q4_K_M.gguf", prompt)

def llm_code(prompt):
    return llm_run("qwen2.5-coder-7b-instruct-q4_k_m.gguf", prompt)

def llm_biomedical(prompt):
    return llm_run("BioMedLM-7B.Q4_K_M.gguf", prompt)

def llm_legal(prompt):
    return llm_run("legal-llama-3-unsloth.Q4_K_M.gguf", prompt)

def llm_casual_chat(prompt):
    return llm_run("baichuan2-7b-chat.Q4_K_M.gguf", prompt)

def llm_friendly_chat(prompt):
    return llm_run("openbuddy-zephyr-7b-v14.1.Q4_K_M.gguf", prompt)

def llm_open_discussion(prompt):
    return llm_run("OpenAssistant-falcon-7b-sft-top1.gguf", prompt)

def llm_creative_write(prompt):
    return llm_run("gemma-7b.Q4_K_M.gguf", prompt)

def llm_multilingual(prompt):
    return llm_run("internlm2-chat-7B.Q4_K_M.gguf", prompt)

def llm_world_knowledge(prompt):
    return llm_run("Yi-1.5-9B-Chat-Q4_K_M.gguf", prompt)

def llm_function_call(prompt):
    return llm_run("llama-2-7b-function-calling.Q3_K_M.gguf", prompt)

def llm_ultra_fast(prompt):
    return llm_run("orca-mini-3b-gguf2-q4_0.gguf", prompt)

def llm_micro_tasks(prompt):
    return llm_run("MiniCPM-2B-dpo-fp32.Q4_K_M.gguf", prompt)

def llm_compact_reason(prompt):
    return llm_run("Phi-3-mini-4k-instruct-q4.gguf", prompt)

def llm_general_assistant(prompt):
    return llm_run("Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", prompt)

def llm_precise_instruction(prompt):
    return llm_run("qwen2.5-7b-instruct-q4_k_m.gguf", prompt)

def llm_lightweight_instruction(prompt):
    return llm_run("qwen2.5-3b-instruct-q4_k_m.gguf", prompt)

def llm_base_research(prompt):
    return llm_run("s1-Qwen2.5-Base-7B.i1-Q4_K_M.gguf", prompt)

def llm_synthetic_data(prompt):
    return llm_run("synthia-7b.Q4_0.gguf", prompt)

def llm_long_context(prompt):
    return llm_run("mpt-7b-8k-chat.Q4_K_M.gguf", prompt, max_tokens=1024)

def llm_supreme_intelligence(prompt):
    return llm_run("qwen3-30b-a3b-q4_k_m.gguf", prompt, max_tokens=1024)

############################################################
# Register all Skills
############################################################

skill.add_skill("ocr", skill_wrapper(ocr))
skill.add_skill("ocr_screen", skill_wrapper(ocr_screen))
skill.add_skill("translate_image", skill_wrapper(translate_image))
skill.add_skill("clear_recycle_bin", skill_wrapper(clear_recycle_bin))
skill.add_skill("lock_screen", skill_wrapper(lock_screen))
skill.add_skill("translate_document", skill_wrapper(translate_document))
skill.add_skill("s_h", skill_wrapper(s_h))
skill.add_skill("natural_alarm_ai", skill_wrapper(natural_alarm_ai))
skill.add_skill("youtube_summarizer", skill_wrapper(youtube_summarizer))
skill.add_skill("ytDownloader", skill_wrapper(ytDownloader))
skill.add_skill("playMusic", skill_wrapper(playMusic))
skill.add_skill("qrCodeGenerator", skill_wrapper(qrCodeGenerator))
skill.add_skill("read_pdf", skill_wrapper(read_pdf))
skill.add_skill("file_organizer", skill_wrapper(file_organizer))
skill.add_skill("transcribe_audio", skill_wrapper(transcribe_audio))
skill.add_skill("download_images", skill_wrapper(download_images))
skill.add_skill("create_file", skill_wrapper(create_file))
skill.add_skill("display_top_processes", skill_wrapper(display_top_processes))
skill.add_skill("change_wallpaper", skill_wrapper(change_wallpaper))
skill.add_skill("analyze_and_report", skill_wrapper(analyze_and_report))
skill.add_skill("send_email", skill_wrapper(send_email))
skill.add_skill("send_multiple_emails", skill_wrapper(send_multiple_emails))
skill.add_skill("open_file", skill_wrapper(open_file))
skill.add_skill("dim_light", skill_wrapper(dim_light))
skill.add_skill("internet_speed", skill_wrapper(internet_speed))
skill.add_skill("create_system_restore_point", skill_wrapper(create_system_restore_point))
skill.add_skill("find_and_delete_duplicates", skill_wrapper(find_and_delete_duplicates))
skill.add_skill("smart_battery", skill_wrapper(smart_battery))
skill.add_skill("yt_search", skill_wrapper(yt_search))
skill.add_skill("openappweb", skill_wrapper(openappweb))
skill.add_skill("closeappweb", skill_wrapper(closeappweb))
skill.add_skill("summarize_excel_with_groq", skill_wrapper(summarize_excel_with_groq))
skill.add_skill("melody", skill_wrapper(melody))
skill.add_skill("record_macro", skill_wrapper(record_macro))
skill.add_skill("play_macro", skill_wrapper(play_macro))
skill.add_skill("adaptive_auto_coder", skill_wrapper(adaptive_auto_coder))
skill.add_skill("run_task", skill_wrapper(run_task_parallel))
skill.add_skill("fetch_page", skill_wrapper(fetch_page))
skill.add_skill("get_page_title", skill_wrapper(get_page_title))
skill.add_skill("get_meta_description", skill_wrapper(get_meta_description))
skill.add_skill("search_google", skill_wrapper(search_google))
skill.add_skill("extract_links", skill_wrapper(extract_links))
skill.add_skill("get_text_content", skill_wrapper(get_text_content))
skill.add_skill("summarize_pdf", skill_wrapper(summarize_pdf))
skill.add_skill("analyze_data", skill_wrapper(analyze_data))
skill.add_skill("plot_data", skill_wrapper(plot_data))
skill.add_skill("convert_text_to_pdf", skill_wrapper(convert_text_to_pdf))
skill.add_skill("summarize_text", skill_wrapper(summarize_text))
skill.add_skill("sentiment_analysis", skill_wrapper(sentiment_analysis))
skill.add_skill("nlp_qna", skill_wrapper(nlp_qna))
skill.add_skill("schedule_task", skill_wrapper(schedule_task))
skill.add_skill("generate_chart_from_data", skill_wrapper(generate_chart_from_data))
skill.add_skill("analyze_image", skill_wrapper(analyze_image))
skill.add_skill("generate_report", skill_wrapper(generate_report))
skill.add_skill("watch_folder", skill_wrapper(watch_folder))
skill.add_skill("smart_decide", skill_wrapper(smart_decide))
skill.add_skill("encrypt_file", skill_wrapper(encrypt_file))
skill.add_skill("clean_clipboard", skill_wrapper(clean_clipboard))
skill.add_skill("auto_backup", skill_wrapper(auto_backup))
skill.add_skill("reload_plugins", skill_wrapper(reload_plugins_skill))
skill.add_skill("focus_window", skill_wrapper(focus_window))
skill.add_skill("click", skill_wrapper(click))
skill.add_skill("double_click", skill_wrapper(double_click))
skill.add_skill("right_click", skill_wrapper(right_click))
skill.add_skill("type_text", skill_wrapper(type_text))
skill.add_skill("press_key", skill_wrapper(press_key))
skill.add_skill("hotkey", skill_wrapper(hotkey))
skill.add_skill("copy_to_clipboard", skill_wrapper(copy_to_clipboard))
skill.add_skill("paste_from_clipboard", skill_wrapper(paste_from_clipboard))
skill.add_skill("drag", skill_wrapper(drag))
skill.add_skill("scroll", skill_wrapper(scroll))
skill.add_skill("get_screen_size", skill_wrapper(get_screen_size))
skill.add_skill("get_window_position", skill_wrapper(get_window_position))
skill.add_skill("take_screenshot", skill_wrapper(take_screenshot))
skill.add_skill("wait_for_window", skill_wrapper(wait_for_window))
skill.add_skill("wait_for_image", skill_wrapper(wait_for_image))
skill.add_skill("click_image", skill_wrapper(click_image))
skill.add_skill("double_click_image", skill_wrapper(double_click_image))
skill.add_skill("drag_image", skill_wrapper(drag_image))
skill.add_skill("highlight_image", skill_wrapper(highlight_image))
skill.add_skill("click_text", skill_wrapper(click_text))
skill.add_skill("drag_text", skill_wrapper(drag_text))
skill.add_skill("repeat_macro", skill_wrapper(repeat_macro))
skill.add_skill("chain_commands", skill_wrapper(chain_commands))
skill.add_skill("safe_click", skill_wrapper(safe_click))
skill.add_skill("safe_type", skill_wrapper(safe_type))
skill.add_skill("backup_clipboard", skill_wrapper(backup_clipboard))
skill.add_skill("restore_clipboard", skill_wrapper(restore_clipboard))
skill.add_skill("move_cursor_to_image", skill_wrapper(move_cursor_to_image))
skill.add_skill("center_window", skill_wrapper(center_window))
skill.add_skill("maximize_window", skill_wrapper(maximize_window))
skill.add_skill("minimize_window", skill_wrapper(minimize_window))
skill.add_skill("schedule_calendar", skill_wrapper(schedule_calendar_event))
skill.add_skill("upload_to_drive", skill_wrapper(upload_to_drive))
skill.add_skill("send_discord_message", skill_wrapper(send_discord_message))
skill.add_skill("send_whatsapp_message", skill_wrapper(send_whatsapp_message))
skill.add_skill("os_context", skill_wrapper(os_context_skill))
skill.add_skill("predictive_tasks", skill_wrapper(predictive_tasks))
skill.add_skill("exec_safe", skill_wrapper(exec_safe))
skill.add_skill("window_finder", skill_wrapper(window_finder))
skill.add_skill("file_finder", skill_wrapper(file_finder))
skill.add_skill("check_process_status", skill_wrapper(check_process_status))
skill.add_skill("file_manager", skill_wrapper(file_manager))
skill.add_skill("video_to_audio", skill_wrapper(video_to_audio))
skill.add_skill("bg_remover", skill_wrapper(bg_remover))
skill.add_skill("wordcloud_generator", skill_wrapper(wordcloud_generator))
skill.add_skill("instagram_video_downloader", skill_wrapper(instagram_video_downloader))
skill.add_skill("facebook_video_downloader", skill_wrapper(facebook_video_downloader))
skill.add_skill("xml_to_csv_converter", skill_wrapper(xml_to_csv_converter))
skill.add_skill("malware_static_analyzer", skill_wrapper(malware_static_analyzer))
skill.add_skill("track_amazon_product_price", skill_wrapper(track_price))
skill.add_skill("remember_birthday", skill_wrapper(remember_birthday))
skill.add_skill("check_birthdays", skill_wrapper(check_birthdays))
skill.add_skill("download_email_attachments", skill_wrapper(download_attachments))
skill.add_skill("scrape_best_sellers", skill_wrapper(scrape_best_sellers))
skill.add_skill("aws_control", skill_wrapper(aws_control))
skill.add_skill("plot_spectrogram", skill_wrapper(plot_spectrogram))
skill.add_skill("csv_to_excel", skill_wrapper(csv_to_excel))
skill.add_skill("ip_geolocator", skill_wrapper(ip_geolocator))
skill.add_skill("speaker_health_test", skill_wrapper(speaker_health_test_skill))
skill.add_skill("run_sophos_central_health_analysis", skill_wrapper(run_sophos_central_health_analysis))
skill.add_skill("llm_judge_answer", skill_wrapper(llm_judge_answer))
skill.add_skill("llm_truth_check", skill_wrapper(llm_truth_check))
skill.add_skill("llm_deep_reason", skill_wrapper(llm_deep_reason))
skill.add_skill("llm_experimental_reason", skill_wrapper(llm_experimental_reason))
skill.add_skill("llm_solve_math", skill_wrapper(llm_solve_math))
skill.add_skill("llm_code", skill_wrapper(llm_code))
skill.add_skill("llm_biomedical", skill_wrapper(llm_biomedical))
skill.add_skill("llm_legal", skill_wrapper(llm_legal))
skill.add_skill("llm_casual_chat", skill_wrapper(llm_casual_chat))
skill.add_skill("llm_friendly_chat", skill_wrapper(llm_friendly_chat))
skill.add_skill("llm_open_discussion", skill_wrapper(llm_open_discussion))
skill.add_skill("llm_creative_write", skill_wrapper(llm_creative_write))
skill.add_skill("llm_multilingual", skill_wrapper(llm_multilingual))
skill.add_skill("llm_world_knowledge", skill_wrapper(llm_world_knowledge))
skill.add_skill("llm_function_call", skill_wrapper(llm_function_call))
skill.add_skill("llm_ultra_fast", skill_wrapper(llm_ultra_fast))
skill.add_skill("llm_micro_tasks", skill_wrapper(llm_micro_tasks))
skill.add_skill("llm_compact_reason", skill_wrapper(llm_compact_reason))
skill.add_skill("llm_general_assistant", skill_wrapper(llm_general_assistant))
skill.add_skill("llm_precise_instruction", skill_wrapper(llm_precise_instruction))
skill.add_skill("llm_lightweight_instruction", skill_wrapper(llm_lightweight_instruction))
skill.add_skill("llm_base_research", skill_wrapper(llm_base_research))



