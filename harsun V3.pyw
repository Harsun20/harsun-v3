import array
import ast
import math
import operator
import os
import queue
import random
import re
import subprocess
import threading
import time
import tkinter as tk
import traceback
import webbrowser
import winsound
from tkinter import scrolledtext
from urllib.parse import quote_plus

import pyttsx3
import requests
import speech_recognition as sr
from rapidfuzz import fuzz, process


# ==============================================================================
# --- BLOCK 1: GLOBAL CONFIGURATION & DATA ---
# ==============================================================================
IDLE_TIMEOUT_SEC = 0  # auto-deactivate after N seconds without a command; 0 = keep listening until told to stop

LOCAL_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "command prompt": "cmd.exe",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "settings": "ms-settings:",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}

WEB_OVERRIDES = {
    "gmail": "https://mail.google.com/mail/u/0/#inbox",
    "outlook": "https://outlook.office.com/mail/",
    "youtube": "https://www.youtube.com",
    "drive": "https://drive.google.com/drive/u/0/my-drive",
    "calendar": "https://calendar.google.com/calendar/u/0/r",
    "instagram": "https://www.instagram.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "github": "https://github.com/",
    "maps": "https://maps.google.com/",
    "linkedin": "https://www.linkedin.com/",
    "netflix": "https://www.netflix.com/",
}

CONVERSATION_FLOW = {
    "hello": ["Hello! System online.", "Greetings. How can I help?", "Uplink stable. Hello."],
    "hi": ["Hello! System online.", "Greetings. How can I help?"],
    "hey": ["Hello! System online.", "Greetings. How can I help?"],
    "how are you": ["Systems are nominal.", "Running at 100% efficiency.", "I am functioning within expected parameters."],
    "who made you": ["I am Harsun, an AI assistant.", "My core was developed as part of the Harsun Project."],
    "who are you": ["I am Harsun, an AI assistant.", "I am HARSUN V3."],
    "thank you": ["You're welcome.", "Happy to assist.", "Task complete."],
    "thanks": ["You're welcome.", "Happy to assist.", "Task complete."],
    "your name": ["I am HARSUN V3.", "You can call me Harsun."],
}


# ==============================================================================
# --- BLOCK 2: BACKGROUND ANIMATION ENGINE ---
# ==============================================================================
class ScrollAnimation:
    """Handles the Matrix-style background code scrolling."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.code_snippets = ["SYSTEM_ACTIVE", "UPLINK_STABLE", "V3_PROTOCOL", "INDICATOR_SYNC_OK"]
        self.labels = []
        self.animate()

    def animate(self):
        if random.random() < 0.15:
            x_pos = random.randint(10, 550)
            lbl = self.canvas.create_text(x_pos, 720, text=random.choice(self.code_snippets), 
                                         fill="#142F14", font=("Consolas", 8), anchor="w")
            self.labels.append(lbl)
        
        for lbl in self.labels[:]:
            self.canvas.move(lbl, 0, -4)
            if self.canvas.coords(lbl)[1] < -20:
                self.canvas.delete(lbl)
                self.labels.remove(lbl)
        
        self.canvas.after(30, self.animate)


# ==============================================================================
# --- BLOCK 2B: VOICE-REACTIVE PULSE (music-visualiser blob) ---
# ==============================================================================
class PulseAnimation:
    """Ring that swells with the live mic level and deforms like a music-video visualiser.
    Drawn on the background canvas so it can grow freely and always stays centred."""
    POINTS = 72
    BASE_R = 36
    MAX_R = 92
    FRAME_MS = 33

    def __init__(self, canvas, app, cy=110):
        self.canvas, self.app, self.cy = canvas, app, cy
        self.level = 0.0
        self.phase = 0.0
        self.color = "#00d4ff"
        self.angles = [2 * math.pi * i / self.POINTS for i in range(self.POINTS)]
        self.cos = [math.cos(a) for a in self.angles]
        self.sin = [math.sin(a) for a in self.angles]
        flat = [0, 0] * self.POINTS
        self.glow = canvas.create_polygon(*flat, smooth=True, fill="", outline=self._dim(0.35), width=2)
        self.core = canvas.create_polygon(*flat, smooth=True, fill="#020a0a", outline=self.color, width=4)
        self.animate()

    def _dim(self, factor):
        r, g, b = (int(self.color[i:i + 2], 16) for i in (1, 3, 5))
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"

    def set_color(self, color):
        self.color = color
        self.canvas.itemconfig(self.core, outline=color)
        self.canvas.itemconfig(self.glow, outline=self._dim(0.35))

    def animate(self):
        app, t = self.app, time.time()
        if app.state == "active":
            target = app.mic_level                      # real microphone level
        elif app.state == "speaking":                   # synthetic "talking" wave
            target = 0.30 + 0.20 * abs(math.sin(t * 6.5)) * (0.7 + 0.3 * math.sin(t * 2.3))
        else:
            target = 0.0
        # fast attack, slow release -> punchy on beats, smooth on the way down
        self.level += (target - self.level) * (0.6 if target > self.level else 0.12)
        lvl = self.level
        self.phase += 0.04 + lvl * 0.35                 # ripples spin faster when loud
        ph = self.phase

        r0 = self.BASE_R * (1 + 0.05 * math.sin(t * 1.6)) + lvl * 24   # breathing + swell
        amp = (2.5 + lvl * 30) * 0.4                                  # deformation depth
        w = self.canvas.winfo_width()
        cx, cy = (w if w > 1 else 600) / 2, self.cy

        core, glow = [], []
        for a, c, s in zip(self.angles, self.cos, self.sin):
            d = amp * (math.sin(3 * a + ph * 1.3) + 0.6 * math.sin(5 * a - ph * 1.9)
                       + 0.45 * math.sin(8 * a + ph * 2.7) + 0.3 * math.sin(13 * a - ph * 4.1))
            r = min(self.MAX_R, max(10.0, r0 + d))
            g = min(98.0, max(14.0, r0 + 6 + lvl * 10 + d * 1.5))
            core += (cx + r * c, cy + r * s)
            glow += (cx + g * c, cy + g * s)
        self.canvas.coords(self.glow, *glow)
        self.canvas.coords(self.core, *core)
        self.canvas.tag_raise(self.glow)
        self.canvas.tag_raise(self.core)
        self.canvas.after(self.FRAME_MS, self.animate)


# ==============================================================================
# --- BLOCK 3: UNIVERSAL COMMAND ROUTER (V4) ---
# ==============================================================================
# Pipeline: normalise -> ordered handlers (first non-None reply wins) -> Google.
# Every pattern is compiled once at import; pywhatkit is imported lazily.

# --- Precompiled patterns ---
WAKE_RE = re.compile(r"^(?:(?:hey|ok|okay|hi)\s+)?harsun\b[\s,]*")
POLITE_RE = re.compile(r"^(?:(?:please|can you|could you|would you|will you|i want you to)\s+)+")
TRAIL_RE = re.compile(r"[\s,.?!]*(?:\s+please)?[\s,.?!]*$")

SHUTDOWN_RE = re.compile(
    r"^(?:please\s+)?(?:exit|quit|shut\s?down|goodbye|bye|stop(?:\s+listening)?|go to sleep)(?:\s+harsun)?$"
)
CHAT_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, sorted(CONVERSATION_FLOW, key=len, reverse=True))) + r")\b"
)

TIME_RE = re.compile(r"\b(?:what(?:'s| is) the time|what time is it|current time|time now|tell me the time)\b")
DATE_RE = re.compile(r"\b(?:what(?:'s| is) (?:the |today's )?date|what day is it|today's date|what is today)\b")
MATH_LEAD_RE = re.compile(r"^(?:calculate|compute|solve|evaluate|what(?:'s| is)|whats)\s+")
MATH_CHARS_RE = re.compile(r"[\d\s.+\-*/%()]+")
MATH_X_RE = re.compile(r"(?<=\d)\s*x\s*(?=\d)")
MATH_WORDS = (
    ("to the power of", "**"), ("raised to", "**"), ("multiplied by", "*"), ("divided by", "/"),
    ("plus", "+"), ("minus", "-"), ("times", "*"), ("over", "/"), ("into", "*"), ("mod", "%"),
)

YT_PLAY_RE = re.compile(r"^play\s+(.+?)(?:\s+on\s+youtube)?$")
YT_SEARCH_RE = re.compile(
    r"^(?:search\s+(?:on\s+)?youtube\s+(?:for\s+)?(.+)|(?:search|find)\s+(.+?)\s+on\s+youtube)$"
)

OPEN_RE = re.compile(
    r"^(?:open|launch|start|run|go to|navigate to|take me to)\s+(?:the\s+)?(.+?)"
    r"(?:\s+(?:app|application|website|site|page))?$"
)
DOT_RE = re.compile(r"\s+dot\s+")
DOMAIN_RE = re.compile(r"^(?:https?://)?(?:[\w-]+\.)+[a-z]{2,}(?:/\S*)?$")

WIKI_RE = re.compile(
    r"^(?:search\s+wikipedia\s+for|look\s+up\s+on\s+wikipedia|wikipedia|who\s+(?:is|was|were)|who's|"
    r"what\s+(?:is|are|was|were)|what's|whats|tell\s+me\s+about|explain|define|meaning\s+of|"
    r"history\s+of|describe)\s+(.+)$"
)
ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+")
NON_WIKI_RE = re.compile(
    r"\b(?:weather|temperature|forecast|news|scores?|stocks?|near me|nearby|my|right now|today|tonight|tomorrow)\b"
)

SEARCH_RE = re.compile(
    r"^(?:google|search(?:\s+(?:google|the web|online))?(?:\s+for)?|look\s?up|find|browse)\s+(.+)$"
)

DUCKY_URL = "https://duckduckgo.com/?q=!ducky+{}"
GOOGLE_URL = "https://www.google.com/search?q={}"
_TARGET_NAMES = list(WEB_OVERRIDES) + list(LOCAL_APPS)


# --- Safe arithmetic (no eval) ---
_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UN_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UN_OPS:
        return _UN_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


# --- Wikipedia: one HTTP call, relevance-ranked, disambiguation-aware ---
_WIKI_API = "https://en.wikipedia.org/w/api.php"
_WIKI_CACHE = {}
_HTTP = requests.Session()
_HTTP.headers["User-Agent"] = "HarsunV3/3.0 (desktop voice assistant)"

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_BRACKETS_RE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
_SPACE_RE = re.compile(r"\s+")
_PUNCT_GAP_RE = re.compile(r"\s+([,.;:])")


def _tidy(extract, max_sentences=2, max_chars=420):
    """Strip pronunciations/citations, keep the first sentences, cap length for speech."""
    text = _BRACKETS_RE.sub("", extract)
    text = _PUNCT_GAP_RE.sub(r"\1", _SPACE_RE.sub(" ", text)).strip()
    out = ""
    for sentence in _SENTENCE_RE.split(text)[:max_sentences]:
        if out and len(out) + len(sentence) + 1 > max_chars:
            break
        out = f"{out} {sentence}".strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "..."
    return out


def wiki_summary(target):
    """Return a short, clean Wikipedia summary for `target`, or None."""
    key = target.lower()
    if key in _WIKI_CACHE:
        return _WIKI_CACHE[key]
    try:
        resp = _HTTP.get(_WIKI_API, timeout=5, params={
            "action": "query", "format": "json", "formatversion": 2,
            "generator": "search", "gsrsearch": target, "gsrlimit": 5, "gsrnamespace": 0,
            "redirects": 1, "prop": "extracts|pageprops", "ppprop": "disambiguation",
            "exintro": 1, "explaintext": 1, "exsentences": 3, "exlimit": "max",
        })
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", [])
    except (requests.RequestException, ValueError):
        return None

    # Drop disambiguation hubs and empty stubs; keep search-rank order for tie-breaks.
    pages = [p for p in pages if p.get("extract") and "disambiguation" not in p.get("pageprops", {})]
    if not pages:
        return None
    pages.sort(key=lambda p: p.get("index", 99))
    score, best = max(((fuzz.WRatio(key, p["title"].lower()), p) for p in pages), key=lambda t: t[0])
    if score < 60:  # top hit isn't really about the asked topic -> let Google handle it
        return None
    summary = _tidy(best["extract"])
    if summary:
        _WIKI_CACHE[key] = summary
    return summary or None


# --- Handlers: each returns a reply string, or None to pass ---
def _normalise(command):
    cmd = command.lower().strip()
    stripped = POLITE_RE.sub("", WAKE_RE.sub("", cmd, count=1), count=1)
    stripped = TRAIL_RE.sub("", stripped)
    return stripped or cmd


def _h_shutdown(cmd):
    return "SHUTDOWN_SEQUENCE_INITIATED" if SHUTDOWN_RE.match(cmd) else None


def _h_chat(cmd):
    words = len(cmd.split())
    if words > 7:
        return None
    m = CHAT_RE.search(cmd)
    # The phrase must make up most of the utterance ("hello world in python" is a search).
    if m and len(m.group(1).split()) >= words - 2:
        return random.choice(CONVERSATION_FLOW[m.group(1)])
    return None


def _h_utility(cmd):
    if TIME_RE.search(cmd):
        return "It is " + time.strftime("%I:%M %p").lstrip("0") + "."
    if DATE_RE.search(cmd):
        return "Today is " + time.strftime("%A, %B %d, %Y").replace(" 0", " ") + "."

    expr = MATH_LEAD_RE.sub("", cmd)
    for word, sym in MATH_WORDS:
        expr = expr.replace(word, sym)
    expr = MATH_X_RE.sub("*", expr).replace("^", "**")
    if not (MATH_CHARS_RE.fullmatch(expr.replace("**", "*")) and any(c.isdigit() for c in expr)
            and any(c in expr for c in "+-*/%")):
        return None
    try:
        result = _eval_node(ast.parse(expr.strip(), mode="eval"))
    except ZeroDivisionError:
        return "I can't divide by zero."
    except (ValueError, SyntaxError, OverflowError):
        return None
    result = round(result, 6)
    if float(result).is_integer():
        result = int(result)
    return f"The answer is {result}."


def _h_youtube(cmd):
    m = YT_SEARCH_RE.match(cmd)
    if m:
        query = (m.group(1) or m.group(2)).strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
        return f"Searching YouTube for '{query}'."
    m = YT_PLAY_RE.match(cmd)
    if m:
        import pywhatkit  # lazy: slow import, only needed here
        query = m.group(1).strip()
        pywhatkit.playonyt(query)
        return f"Playing {query} on YouTube."
    return None


def _h_open(cmd):
    m = OPEN_RE.match(cmd)
    if not m:
        return None
    target = m.group(1).strip()

    # Spoken or typed domain ("github dot com", "example.org/page")
    compact = DOT_RE.sub(".", target)
    if DOMAIN_RE.match(compact):
        webbrowser.open(compact if compact.startswith("http") else f"https://{compact}")
        return f"Opening {compact}."

    # Fuzzy match across websites and local apps in one pass
    hit = process.extractOne(target, _TARGET_NAMES, scorer=fuzz.ratio, score_cutoff=78)
    if hit:
        name = hit[0]
        if name in WEB_OVERRIDES:
            webbrowser.open(WEB_OVERRIDES[name])
            return f"Opening {name}."
        try:
            os.startfile(LOCAL_APPS[name])
            return f"Launching {name}."
        except OSError:
            return f"I couldn't launch {name}."

    # "I'm feeling lucky" fallback
    webbrowser.open(DUCKY_URL.format(quote_plus(target)))
    return f"Opening {target}." if len(target.split()) < 3 else f"Opening top result for {target}."


def _h_wiki(cmd):
    m = WIKI_RE.match(cmd)
    if not m:
        return None
    target = ARTICLE_RE.sub("", m.group(1).strip())
    if not target or NON_WIKI_RE.search(target):
        return None
    summary = wiki_summary(target)
    return f"According to Wikipedia: {summary}" if summary else None


def _h_search(cmd):
    m = SEARCH_RE.match(cmd)
    if not m:
        return None
    query = m.group(1).strip()
    webbrowser.open(GOOGLE_URL.format(quote_plus(query)))
    return f"Searching Google for: {query}"


_HANDLERS = (_h_shutdown, _h_chat, _h_utility, _h_youtube, _h_open, _h_wiki, _h_search)


def handle_commands(command):
    try:
        if not command or not command.strip():
            return None
        cmd = _normalise(command)
        for handler in _HANDLERS:
            reply = handler(cmd)
            if reply:
                return reply
        # Global catch-all: anything unrecognised becomes a web search
        webbrowser.open(GOOGLE_URL.format(quote_plus(cmd)))
        return f"Searching Google for: {cmd}"
    except Exception as e:
        return f"Router Error: {e}"


# ==============================================================================
# --- BLOCK 4: CORE GUI & VOICE ENGINE ---
# ==============================================================================
class HarsunV3:
    def __init__(self, root):
        self.root = root
        self.root.title("HARSUN V3")
        self.root.geometry("600x780")
        self.root.configure(bg="black")

        self.is_listening = False
        self.start_time = 0
        self.last_activity_time = 0
        self.has_greeted = False
        self.state = "standby"        # read by the pulse animation
        self.mic_level = 0.0          # 0..1 live voice level, written by the mic thread
        self._mic_floor = None        # adaptive noise floor / peak used to normalise the level
        self._mic_peak = 1500.0
        self.session_id = 0           # retires stale voice loops when the session is re-toggled

        # Speech: ONE long-lived worker thread + queue. Re-initialising pyttsx3 inside a
        # fresh thread per sentence is what makes replies go silent on Windows.
        self.tts_queue = queue.Queue()
        self._tts_lock = threading.Lock()
        self._tts_pending = 0
        self._tts_done_at = 0.0
        threading.Thread(target=self._tts_worker, daemon=True).start()

        # --- UI LAYOUT SECTION ---
        self.bg_canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.bg_canvas.place(relwidth=1, relheight=1)
        self.bg_engine = ScrollAnimation(self.bg_canvas)

        # Pulse Circle (voice-reactive)
        self.pulse = PulseAnimation(self.bg_canvas, self)

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(root, bg="#050505", fg="#00FF41", font=("Consolas", 10))
        self.chat_display.place(relx=0.5, rely=0.52, anchor="center", relwidth=0.9, relheight=0.45)
        self.chat_display.configure(state='disabled')

        # Status Bar
        self.status_bar = tk.Label(root, text="SYSTEM STANDBY", bg="#001111", fg="#00d4ff", 
                                   font=("Consolas", 10, "bold"), bd=1, relief="sunken", anchor="w", padx=10)
        self.status_bar.pack(side="bottom", fill="x")

        # Control Button
        self.btn = tk.Button(root, text="ACTIVATE", command=self.toggle_session, 
                               bg="#00FF41", font=("Consolas", 10, "bold"), width=15)
        self.btn.place(relx=0.5, rely=0.82, anchor="center")

        # Auto-start session
        self.root.after(1000, self.toggle_session)

    def update_status(self, state):
        self.root.after(0, lambda: self._perform_status_update(state))

    def _perform_status_update(self, state):
        states = {
            "standby":  {"text": "● STANDBY", "color": "#00d4ff", "bg": "#001111"},
            "active":   {"text": "● ACTIVE - LISTENING", "color": "#ff4b2b", "bg": "#1a0000"},
            "speaking": {"text": "● PROCESSING - SPEAKING", "color": "#00ff00", "bg": "#001a00"}
        }
        cfg = states.get(state, states["standby"])
        self.state = state if state in states else "standby"
        self.status_bar.config(text=cfg["text"], fg=cfg["color"], bg=cfg["bg"])
        self.pulse.set_color(cfg["color"])

    def log(self, sender, msg):
        self.root.after(0, lambda: self._update_log(sender, msg))

    def _update_log(self, sender, msg):
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, f"[{sender.upper()}]: {msg}\n")
        self.chat_display.see(tk.END)
        self.chat_display.configure(state='disabled')

    def toggle_session(self):
        if not self.is_listening:
            self.is_listening = True
            self.session_id += 1
            self.start_time = time.time()
            self.last_activity_time = self.start_time
            self.btn.config(text="DEACTIVATE", bg="#ff4b2b")
            winsound.Beep(1000, 100)
            
            if not self.has_greeted:
                self.log("harsun", "Harsun v3 online.")
                self.speak("Harsun v3 online.")
                self.has_greeted = True
            
            threading.Thread(target=self.voice_loop, args=(self.session_id,), daemon=True).start()
        else:
            self.is_listening = False
            self.session_id += 1      # any running loop sees the change and exits
            self.btn.config(text="ACTIVATE", bg="#00FF41")
            self.update_status("standby")
            winsound.Beep(600, 100)

    # --- Microphone level tap (feeds the pulse animation) ---
    def _tap_mic(self, source):
        """Wrap the mic stream so every audio chunk updates self.mic_level."""
        stream = source.stream
        raw_read = stream.read

        def read(size, *args, **kwargs):
            data = raw_read(size, *args, **kwargs)
            try:
                self._measure(data)
            except Exception:
                pass
            return data
        stream.read = read

    def _measure(self, data):
        samples = array.array("h", data[: len(data) // 2 * 2])[::4]   # 16-bit PCM, subsampled for speed
        if not samples:
            return
        rms = math.sqrt(sum(x * x for x in samples) / len(samples))
        # Noise floor drops instantly, rises slowly; peak decays slowly -> auto-gain for any mic
        if self._mic_floor is None or rms < self._mic_floor:
            self._mic_floor = rms
        else:
            self._mic_floor += (rms - self._mic_floor) * 0.004
        floor = self._mic_floor * 1.3 + 20
        self._mic_peak = max(rms, self._mic_peak * 0.995, floor + 400)
        lvl = (rms - floor) / (self._mic_peak - floor)
        self.mic_level = min(1.0, max(0.0, lvl)) ** 0.7

    def _drain(self, source):
        """Throw away audio buffered while Harsun was talking so it never hears itself."""
        try:
            pa = source.stream.pyaudio_stream
            while pa.get_read_available() >= source.CHUNK:
                pa.read(source.CHUNK, exception_on_overflow=False)
        except Exception:
            pass

    def voice_loop(self, session):
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.7
        alive = lambda: self.is_listening and session == self.session_id
        was_speaking = False
        net_warned = False
        try:
            with sr.Microphone() as source:
                self._tap_mic(source)
                r.adjust_for_ambient_noise(source, duration=0.5)
                while alive():
                    # Stay deaf while Harsun talks, then flush the echo before listening again
                    if self._tts_pending:
                        was_speaking = True
                        time.sleep(0.05)
                        continue
                    if was_speaking:
                        time.sleep(0.3)
                        self._drain(source)
                        self.last_activity_time = time.time()
                        was_speaking = False

                    if IDLE_TIMEOUT_SEC and time.time() - self.last_activity_time > IDLE_TIMEOUT_SEC:
                        self.root.after(0, self.toggle_session)
                        break
                    if self.state != "active":
                        self.update_status("active")

                    try:
                        audio = r.listen(source, timeout=2, phrase_time_limit=8)
                        self.mic_level = 0.0
                        text = r.recognize_google(audio)
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    except sr.RequestError as e:
                        if not net_warned:
                            self.log("system", f"Speech service unreachable: {e}")
                            net_warned = True
                        continue
                    except Exception:
                        traceback.print_exc()
                        time.sleep(0.5)
                        continue

                    net_warned = False
                    if not alive():
                        break
                    self.log("user", text)
                    self.last_activity_time = time.time()

                    response = handle_commands(text)
                    if not response:
                        continue
                    if response == "SHUTDOWN_SEQUENCE_INITIATED":
                        self.log("harsun", "Shutdown initiated.")
                        self.speak("Harsun shutting down. Goodbye.")
                        deadline = time.time() + 5
                        while self._tts_pending and time.time() < deadline:
                            time.sleep(0.05)
                        os._exit(0)
                    self.log("harsun", response)
                    self.speak(response)
        except Exception as e:  # mic missing / driver failure: report it instead of dying silently
            traceback.print_exc()
            self.log("system", f"Microphone error: {e}")
            if alive():
                self.root.after(0, self.toggle_session)

    # --- Speech output ---
    def speak(self, text):
        with self._tts_lock:
            self._tts_pending += 1
        self.tts_queue.put(text)

    def _speak_fallback(self, text):
        """Windows built-in voice through PowerShell: needs neither pyttsx3 nor comtypes."""
        script = ("Add-Type -AssemblyName System.Speech; "
                  "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  "$s.Rate = 1; $s.Speak($env:HARSUN_TEXT)")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       env={**os.environ, "HARSUN_TEXT": text},
                       creationflags=0x08000000,  # CREATE_NO_WINDOW
                       timeout=60, check=False)

    def _tts_worker(self):
        try:                                   # SAPI5 needs COM initialised on this thread
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        engine = None
        pyttsx3_broken = False
        while True:
            text = self.tts_queue.get()
            try:
                self.update_status("speaking")
                spoken = False
                if not pyttsx3_broken:
                    try:
                        if engine is None:
                            engine = pyttsx3.init()
                            engine.setProperty('rate', 180)
                        engine.say(text)
                        engine.runAndWait()
                        spoken = True
                    except Exception as e:
                        print(f"[TTS] pyttsx3 failed ({e}); using Windows built-in speech instead")
                        pyttsx3_broken, engine = True, None
                if not spoken:
                    self._speak_fallback(text)
            except Exception as e:
                print(f"[TTS error] {e}")
            finally:
                with self._tts_lock:
                    self._tts_pending -= 1
                    idle = self._tts_pending == 0
                    self._tts_done_at = time.time()
                if idle:
                    self.update_status("active" if self.is_listening else "standby")

# ==============================================================================
# --- MAIN EXECUTION ---
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    HarsunV3(root)
    root.mainloop()