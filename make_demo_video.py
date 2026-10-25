"""
make_demo_video.py
------------------
Renders an animated walkthrough of BarcodeDashboard for the GitHub README:
title -> architecture -> app walkthrough (recreated Form1 UI) -> end card.

The app scene redraws the real Form1 layout (7 field toggles, Status group,
Start Scan / Stop) and plays scripted scans through the same rules
ComparisonCoordinator uses: compare once both cameras have a new value,
trim whitespace, case-sensitive.

Run from the repo root:

    pip install -r demo/requirements.txt
    python demo/make_demo_video.py

Edit SCANS below to change the barcodes shown.

Outputs (written to demo/):
    demo.mp4    1280x720 H.264  -> drag into the README on github.com for a video player
    demo.gif    800px wide      -> commit to the repo, plays inline in the README
    poster.png  title frame     -> optional thumbnail
"""

import subprocess
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import imageio_ffmpeg  # bundles an ffmpeg binary, nothing else to install

    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

# ---------------------------------------------------------------- settings
W, H = 1280, 720
FPS = 24
FADE = 0.35

PROJECT_NAME = "BarcodeDashboard"
REPO_URL = "github.com/AhmedMujtaba999/BarcodeDashboard"

# Must match CameraSetup.LoadDefaults()
CAM1 = {"kind": "SerialScanner", "where": "COM1", "detail": "9600 baud"}
CAM2 = {"kind": "TcpCameraHandler", "where": "192.168.0.100:2112", "detail": "TCP"}

# Scripted reads: (seconds into the app scene, cam number, barcode)
SCANS = [
    (6.2, 1, "8901234567890"),
    (7.2, 2, "8901234567890"),   # -> MATCH
    (9.4, 1, "4006381333931"),
    (10.4, 2, "4006381333924"),  # -> NO MATCH
    (12.6, 2, "SKU-7741-B"),
    (13.6, 1, "SKU-7741-B"),     # -> MATCH
]

# Demo palette (outside the app window)
BG = (13, 17, 28)
PANEL = (22, 28, 44)
PANEL_EDGE = (46, 56, 82)
TEXT = (232, 237, 247)
MUTED = (140, 152, 178)
BLUE = (96, 165, 250)
GREEN = (74, 222, 128)
RED = (248, 113, 113)
AMBER = (251, 191, 36)
VIOLET = (167, 139, 250)

# WinForms colours used by the real app
WF_CONTROL = (240, 240, 240)
WF_GAINSBORO = (220, 220, 220)
WF_GRAY = (128, 128, 128)
WF_LIGHTGREEN = (144, 238, 144)
WF_SEAGREEN = (46, 139, 87)
WF_GREEN = (0, 128, 0)
WF_RED = (220, 0, 0)
WF_BLACK = (0, 0, 0)

FONT_CANDIDATES = {
    "regular": ["Inter-Regular.otf", "segoeui.ttf", "Arial.ttf", "arial.ttf", "DejaVuSans.ttf"],
    "semibold": ["Inter-SemiBold.otf", "seguisb.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "bold": ["Inter-Bold.otf", "segoeuib.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "mono": ["DejaVuSansMono.ttf", "consola.ttf", "Menlo.ttc", "Courier New.ttf", "cour.ttf"],
}


@lru_cache(maxsize=None)
def font(kind, size):
    for name in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- helpers
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def appear(t, start, length=0.6):
    return ease((t - start) / length)


def background():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for gx in range(40, W, 40):
        for gy in range(40, H, 40):
            d.point((gx, gy), fill=(30, 37, 56))
    return img


def header(d, eyebrow, title, a=1.0):
    d.text((60, 42), eyebrow.upper(), font=font("semibold", 16), fill=mix(BG, BLUE, a))
    d.text((60, 66), title, font=font("bold", 32), fill=mix(BG, TEXT, a))


def chip(d, x, y, label, color, a=1.0):
    fnt = font("semibold", 18)
    w = d.textlength(label, font=fnt) + 32
    d.rounded_rectangle([x, y, x + w, y + 40], radius=20, fill=mix(BG, PANEL, a), outline=mix(BG, color, a), width=2)
    d.text((x + 16, y + 9), label, font=fnt, fill=mix(BG, TEXT, a))
    return x + w + 12


def centered(d, cx, y, text, fnt, fill):
    d.text((cx - d.textlength(text, font=fnt) / 2, y), text, font=fnt, fill=fill)


def result_icon(d, x, y, size, match):
    """Stand-in for the ✅ / ❌ emoji the app shows next to MATCH / NO MATCH."""
    d.rounded_rectangle([x, y, x + size, y + size], radius=size // 5, fill=(34, 160, 70) if match else (220, 50, 50))
    s = size
    if match:
        d.line([(x + s * .25, y + s * .52), (x + s * .43, y + s * .70), (x + s * .76, y + s * .32)], fill="white", width=max(2, s // 8), joint="curve")
    else:
        w = max(2, s // 8)
        d.line([(x + s * .3, y + s * .3), (x + s * .7, y + s * .7)], fill="white", width=w)
        d.line([(x + s * .7, y + s * .3), (x + s * .3, y + s * .7)], fill="white", width=w)


def cursor(d, x, y):
    pts = [(0, 0), (0, 22), (6, 17), (10, 26), (14, 24), (10, 15), (17, 15)]
    d.polygon([(x + px, y + py) for px, py in pts], fill="white", outline="black")


# ---------------------------------------------------------------- comparison (mirrors ComparisonCoordinator)
class Coordinator:
    def __init__(self, ignore_case=False, trim=True):
        self.ignore_case, self.trim = ignore_case, trim
        self.last = {1: "", 2: ""}
        self.new = {1: False, 2: False}

    def norm(self, s):
        s = s.strip() if self.trim else s
        return s.upper() if self.ignore_case else s

    def on_cam(self, cam, value):
        """Returns True/False once both cams have a new value, else None."""
        self.last[cam], self.new[cam] = value, True
        if self.new[1] and self.new[2]:
            self.new = {1: False, 2: False}
            return self.norm(self.last[1]) == self.norm(self.last[2])
        return None


# ---------------------------------------------------------------- scene: title
def scene_title(t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    a1, a2 = appear(t, 0.1), appear(t, 0.6)
    d.rectangle([60, 250, 60 + int(80 * a1), 256], fill=BLUE)
    d.text((60, 280 + int(14 * (1 - a1))), PROJECT_NAME, font=font("bold", 68), fill=mix(BG, TEXT, a1))
    d.text((62, 375), "Read barcodes from two scanners and flag mismatches in real time.",
           font=font("regular", 24), fill=mix(BG, MUTED, a2))
    x = 60
    for i, (label, color) in enumerate([("C# · .NET 8", VIOLET), ("WinForms", BLUE), ("Serial (COM)", AMBER),
                                        ("TCP/IP", GREEN), ("IScanner abstraction", BLUE)]):
        x = chip(d, x, 440, label, color, appear(t, 1.1 + i * 0.15, 0.4))
    return img


# ---------------------------------------------------------------- scene: architecture
def scene_architecture(t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    header(d, "How it works", "Two transports, one interface, one comparison", appear(t, 0))

    def box(x, y, w, h, title, lines, color, a, lit=False):
        d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=mix(BG, PANEL, a),
                            outline=mix(BG, color if lit else PANEL_EDGE, a), width=3 if lit else 2)
        d.text((x + 20, y + 18), title, font=font("bold", 22), fill=mix(BG, TEXT, a))
        for k, line in enumerate(lines):
            d.text((x + 20, y + 54 + k * 24), line, font=font("regular", 16), fill=mix(BG, MUTED, a))

    c1 = (70, 190, 330, 120)
    c2 = (70, 390, 330, 120)
    co = (530, 270, 320, 160)
    ui = (960, 270, 260, 160)

    # IScanner bracket around both sources
    a = appear(t, 0.2)
    d.rounded_rectangle([52, 160, 418, 530], radius=18, outline=mix(BG, BLUE, a * 0.7), width=2)
    d.text((70, 538), "both implement IScanner  ·  BarcodeScanned / ErrorOccurred", font=font("mono", 15),
           fill=mix(BG, BLUE, a))

    p1 = clamp((t - 1.0) / 1.0)
    p2 = clamp((t - 1.7) / 1.0)
    p3 = clamp((t - 2.9) / 0.9)

    box(*c1, "Cam 1 · SerialScanner", [f"{CAM1['where']} · {CAM1['detail']}", "reads lines ending \\r\\n"], AMBER,
        appear(t, 0.1), lit=t > 1.0)
    box(*c2, "Cam 2 · TcpCameraHandler", [CAM2["where"], "background receive thread"], GREEN,
        appear(t, 0.25), lit=t > 1.7)
    box(*co, "ComparisonCoordinator", ["waits for a new value from both", "trims whitespace", "case-sensitive compare"],
        BLUE, appear(t, 0.4), lit=p2 >= 1)
    box(*ui, "Form1", ["Cam 1 last / Cam 2 last", "status: MATCH or NO MATCH"], VIOLET, appear(t, 0.55), lit=p3 >= 1)

    # arrows
    def arrow(x1, y1, x2, y2, prog, color):
        d.line([(x1, y1), (x2, y2)], fill=PANEL_EDGE, width=3)
        if prog > 0:
            d.line([(x1, y1), (lerp(x1, x2, prog), lerp(y1, y2, prog))], fill=color, width=3)
        d.polygon([(x2, y2), (x2 - 11, y2 - 7), (x2 - 11, y2 + 7)], fill=color if prog >= 1 else PANEL_EDGE)

    a1 = (c1[0] + c1[2] + 6, c1[1] + c1[3] / 2, co[0] - 8, co[1] + 55)
    a2 = (c2[0] + c2[2] + 6, c2[1] + c2[3] / 2, co[0] - 8, co[1] + co[3] - 55)
    a3 = (co[0] + co[2] + 8, co[1] + co[3] / 2, ui[0] - 8, ui[1] + ui[3] / 2)
    arrow(*a1, p1, AMBER)
    arrow(*a2, p2, GREEN)
    arrow(*a3, p3, BLUE)

    def packet(seg, prog, label, color):
        if 0 < prog < 1:
            x, y = lerp(seg[0], seg[2], prog), lerp(seg[1], seg[3], prog)
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=color)
            f = font("mono", 15)
            d.text((x - d.textlength(label, font=f) / 2, y - 30), label, font=f, fill=color)

    packet(a1, p1, "8901234567890", AMBER)
    packet(a2, p2, "8901234567890", GREEN)
    packet(a3, p3, "match", BLUE)

    if p3 >= 1:
        a = appear(t, 3.8, 0.4)
        d.text((ui[0] + 20, ui[1] + ui[3] + 18), "MATCH", font=font("bold", 26), fill=mix(BG, GREEN, a))
        result_icon(d, ui[0] + 20 + d.textlength("MATCH ", font=font("bold", 26)), ui[1] + ui[3] + 20, 26, True)

    note = "Adding a new scanner type means implementing IScanner. The UI and comparison stay the same."
    centered(d, W / 2, 640, note, font("regular", 18), mix(BG, MUTED, appear(t, 4.3)))
    return img


# ---------------------------------------------------------------- scene: app walkthrough
S = 1.15             # scale from WinForms units to video pixels
CW, CH = 980, 280    # client area (real form is 980 wide; height trimmed of empty space)
TB = 36              # title bar height in px
WX = (W - int(CW * S)) // 2
WY = 150


def fx(x):
    return WX + x * S


def fy(y):
    return WY + TB + y * S


BOX = lambda i: (20 + 126 * i, 20, 110, 60)          # CamSelector toggle i (left -> right)
GROUP = (12, 108, 956, 150)
BTN_START = (12 + 748, 108 + 28, 90, 28)
BTN_STOP = (12 + 848, 108 + 28, 90, 28)


def center_of(rect):
    x, y, w, h = rect
    return fx(x + w / 2), fy(y + h / 2)


APP_EVENTS = [
    (0.0, "caption", "Pick the fields covered by Cam 1 and Cam 2"),
    (1.9, "check", 6),
    (3.1, "check", 4),
    (3.6, "caption", "Start Scan opens COM1 and connects to the TCP camera"),
    (4.5, "start", None),
    (5.6, "caption", "Each new pair of reads is compared automatically"),
    *[(ts, "scan", (cam, code)) for ts, cam, code in SCANS],
    (15.4, "caption", "Stop closes both connections"),
    (16.4, "stop", None),
]
APP_DUR = 18.5

REST = (fx(860), fy(240))
CURSOR_KEYS = [
    (0.0, REST), (1.0, REST),
    (1.8, center_of(BOX(6))), (2.2, center_of(BOX(6))),
    (3.0, center_of(BOX(4))), (3.6, center_of(BOX(4))),
    (4.4, center_of(BTN_START)), (5.0, center_of(BTN_START)),
    (5.8, REST), (15.4, REST),
    (16.3, center_of(BTN_STOP)), (APP_DUR, center_of(BTN_STOP)),
]
CLICKS = [1.9, 3.1, 4.5, 16.4]
CLOCK0 = datetime(2026, 10, 25, 10, 42, 5)


def cursor_at(t):
    for (t0, p0), (t1, p1) in zip(CURSOR_KEYS, CURSOR_KEYS[1:]):
        if t0 <= t <= t1:
            k = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            return lerp(p0[0], p1[0], k), lerp(p0[1], p1[1], k)
    return CURSOR_KEYS[-1][1]


def app_state(t):
    """Replay events up to time t, exactly as Form1 + ComparisonCoordinator would."""
    st = {"checked": [], "status": "Waiting to start…", "status_col": WF_BLACK, "result": None,
          "cam1": "—", "cam2": "—", "running": False, "log": [], "caption": "",
          "flash1": -9, "flash2": -9, "flash_status": -9}
    coord = Coordinator()

    def log(ts, msg):
        stamp = (CLOCK0 + timedelta(seconds=ts)).strftime("%H:%M:%S.%f")[:-3]
        st["log"].append((ts, f"{stamp}  {msg}"))

    for ts, kind, arg in APP_EVENTS:
        if ts > t:
            break
        if kind == "caption":
            st["caption"] = arg
        elif kind == "check":
            st["checked"].append(arg)
            field = 7 - arg
            cam = sum(1 for i in st["checked"] if i >= arg)
            log(ts, f"CamSelector       Field {field} → Cam {cam}")
        elif kind == "start":
            st["running"] = True
            st["status"] = f"Listening…  Cam1:SER({CAM1['where']})  Cam2:TCP({CAM2['where']})"
            log(ts, f"SerialScanner     {CAM1['where']} @ {CAM1['detail']} opened")
            log(ts + 0.1, f"TcpCameraHandler  {CAM2['where']} connected")
        elif kind == "scan":
            cam, code = arg
            st[f"cam{cam}"] = code
            st[f"flash{cam}"] = ts
            log(ts, f"Cam {cam} ← {code}")
            res = coord.on_cam(cam, code)
            if res is not None:
                st["result"] = res
                st["status"] = "MATCH" if res else "NO MATCH"
                st["status_col"] = WF_GREEN if res else WF_RED
                st["flash_status"] = ts
                log(ts + 0.02, f"ComparisonCoordinator → {'MATCH' if res else 'NO MATCH'}")
        elif kind == "stop":
            st["running"] = False
            st["status"], st["status_col"], st["result"] = "Stopped.", WF_BLACK, None
            log(ts, "Scanners disposed")
    return st


@lru_cache(maxsize=1)
def window_shadow():
    x0, y0, x1, y1 = WX, WY, WX + CW * S, WY + TB + CH * S
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 14], radius=10, fill=110)
    return mask.filter(ImageFilter.GaussianBlur(14))


def draw_window(img, st, t):
    d = ImageDraw.Draw(img)
    x0, y0 = WX, WY
    x1, y1 = WX + CW * S, WY + TB + CH * S

    # shadow + frame
    img.paste(Image.new("RGB", (W, H), (4, 6, 12)), (0, 0), window_shadow())
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=WF_CONTROL, outline=(90, 96, 110), width=1)

    # title bar
    d.rounded_rectangle([x0, y0, x1, y0 + TB], radius=8, fill=(255, 255, 255))
    d.rectangle([x0, y0 + TB - 8, x1, y0 + TB], fill=(255, 255, 255))
    d.line([(x0, y0 + TB), (x1, y0 + TB)], fill=(218, 218, 218))
    d.text((x0 + 14, y0 + 9), "Field Selector → Start Scan → Auto Compare", font=font("regular", 15), fill=(30, 30, 30))
    gx = x1 - 46 * 3
    for k, glyph in enumerate(["min", "max", "close"]):
        cx, cy = gx + 46 * k + 23, y0 + TB / 2
        col = (60, 60, 60)
        if glyph == "min":
            d.line([(cx - 5, cy), (cx + 5, cy)], fill=col)
        elif glyph == "max":
            d.rectangle([cx - 5, cy - 5, cx + 5, cy + 5], outline=col)
        else:
            d.line([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=col)
            d.line([(cx + 5, cy - 5), (cx - 5, cy + 5)], fill=col)

    # CamSelector: 7 toggles, numbered from the right; first two checked from the right become Cam 1 / Cam 2
    order = sorted(st["checked"], reverse=True)
    for i in range(7):
        bx, by, bw, bh = BOX(i)
        rect = [fx(bx), fy(by), fx(bx + bw), fy(by + bh)]
        field = 7 - i
        if i in st["checked"]:
            cam = order.index(i) + 1
            d.rectangle(rect, fill=WF_LIGHTGREEN, outline=WF_SEAGREEN, width=2)
            f = font("bold", 16)
            cx = (rect[0] + rect[2]) / 2
            centered(d, cx, rect[1] + 14, f"Field {field}", f, WF_BLACK)
            centered(d, cx, rect[1] + 36, f"Cam {cam}", f, WF_BLACK)
        else:
            d.rectangle(rect, fill=WF_GAINSBORO, outline=WF_GRAY, width=2)
            f = font("regular", 16)
            centered(d, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2 - 10, f"Field {field}", f, WF_BLACK)

    # Status group box
    gx_, gy_, gw, gh = GROUP
    gr = [fx(gx_), fy(gy_ + 8), fx(gx_ + gw), fy(gy_ + gh)]
    d.rectangle(gr, outline=(200, 200, 200), width=1)
    cap_f = font("regular", 15)
    d.rectangle([gr[0] + 8, gr[1] - 9, gr[0] + 16 + d.textlength("Status", font=cap_f), gr[1] + 9], fill=WF_CONTROL)
    d.text((gr[0] + 12, gr[1] - 10), "Status", font=cap_f, fill=(40, 40, 40))

    # status label (+ pulse when a comparison lands)
    sx, sy = fx(gx_ + 16), fy(gy_ + 28)
    pulse = clamp(1 - (t - st["flash_status"]) / 0.8)
    sf = font("bold", 22)
    if pulse > 0 and st["result"] is not None:
        tint = (215, 245, 220) if st["result"] else (250, 220, 220)
        w = d.textlength(st["status"], font=sf) + 44
        d.rounded_rectangle([sx - 8, sy - 4, sx + w, sy + 32], radius=6, fill=mix(WF_CONTROL, tint, pulse))
    d.text((sx, sy), st["status"], font=sf, fill=st["status_col"])
    if st["result"] is not None:
        result_icon(d, sx + d.textlength(st["status"] + " ", font=sf), sy + 2, 24, st["result"])

    # Cam 1 / Cam 2 last values (+ highlight on new read)
    lf = font("regular", 18)
    for cam, gy_off in ((1, 65), (2, 95)):
        lx, ly = fx(gx_ + 16), fy(gy_ + gy_off) + 6
        text = f"Cam {cam} last: {st[f'cam{cam}']}"
        flash = clamp(1 - (t - st[f"flash{cam}"]) / 0.7)
        if flash > 0:
            d.rounded_rectangle([lx - 6, ly - 3, lx + d.textlength(text, font=lf) + 6, ly + 25], radius=4,
                                fill=mix(WF_CONTROL, (255, 240, 170), flash))
        d.text((lx, ly), text, font=lf, fill=WF_BLACK)

    # Start / Stop buttons
    cx_, cy_ = cursor_at(t)
    for rect_def, label, enabled in ((BTN_START, "Start Scan", not st["running"]), (BTN_STOP, "Stop", st["running"])):
        bx, by, bw, bh = rect_def
        r = [fx(bx), fy(by), fx(bx + bw), fy(by + bh)]
        hover = enabled and r[0] <= cx_ <= r[2] and r[1] <= cy_ <= r[3]
        fill = (229, 241, 251) if hover else (225, 225, 225)
        edge = (0, 120, 215) if hover else (173, 173, 173)
        d.rectangle(r, fill=fill if enabled else (204, 204, 204), outline=edge if enabled else (191, 191, 191))
        centered(d, (r[0] + r[2]) / 2, r[1] + 6, label, font("regular", 15),
                 (20, 20, 20) if enabled else (150, 150, 150))


def scene_app(t, dur):
    img = background()
    st = app_state(t)
    d = ImageDraw.Draw(img)
    d.text((60, 42), "WALKTHROUGH", font=font("semibold", 16), fill=BLUE)
    d.text((60, 66), st["caption"], font=font("bold", 30), fill=TEXT)

    draw_window(img, st, t)
    d = ImageDraw.Draw(img)

    # event log under the window
    ly0 = WY + TB + CH * S + 22
    d.rounded_rectangle([WX, ly0, WX + CW * S, H - 24], radius=10, fill=PANEL, outline=PANEL_EDGE)
    d.text((WX + 16, ly0 + 10), "EVENTS", font=font("semibold", 13), fill=MUTED)
    lines = st["log"][-4:]
    for k, (ts, line) in enumerate(lines):
        age = t - ts
        col = TEXT if age < 1.2 else MUTED
        if "NO MATCH" in line:
            col = RED if age < 1.5 else mix(RED, MUTED, 0.5)
        elif "MATCH" in line:
            col = GREEN if age < 1.5 else mix(GREEN, MUTED, 0.5)
        d.text((WX + 16, ly0 + 34 + k * 22), line, font=font("mono", 16), fill=col)

    # cursor + click ripple
    cx, cy = cursor_at(t)
    for c in CLICKS:
        if 0 <= t - c < 0.45:
            r = 8 + 40 * (t - c)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(BLUE, BG, (t - c) / 0.45), width=3)
    cursor(d, cx, cy)
    return img


# ---------------------------------------------------------------- scene: end card
def scene_end(t, dur):
    img = background()
    d = ImageDraw.Draw(img)
    centered(d, W / 2, 270, PROJECT_NAME, font("bold", 56), mix(BG, TEXT, appear(t, 0.1)))
    centered(d, W / 2, 352, REPO_URL, font("mono", 24), mix(BG, BLUE, appear(t, 0.5)))
    centered(d, W / 2, 405, "C#  ·  .NET 8  ·  WinForms  ·  System.IO.Ports  ·  TCP sockets",
             font("regular", 20), mix(BG, MUTED, appear(t, 0.9)))
    return img


# ---------------------------------------------------------------- render
def render(scenes, mp4_path):
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bg = background()
    total = sum(int(dur * FPS) for dur, _ in scenes)
    done = 0
    for dur, fn in scenes:
        for f in range(int(dur * FPS)):
            t = f / FPS
            frame = fn(t, dur)
            fade = ease(min(t / FADE, (dur - t) / FADE, 1.0))
            if fade < 1:
                frame = Image.blend(bg, frame, fade)
            proc.stdin.write(frame.tobytes())
            done += 1
            if done % FPS == 0:
                print(f"\r  rendering {done * 100 // total:3d}%", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print("\r  rendering 100%")
    if proc.returncode != 0:
        sys.exit("ffmpeg failed while writing the MP4.")


def make_gif(mp4_path, gif_path, width=800, fps=10):
    vf = (f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];"
          "[a]palettegen=max_colors=128:stats_mode=diff[p];"
          "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(mp4_path), "-vf", vf, "-loop", "0", str(gif_path)],
                   check=True)


def main():
    out = Path(__file__).parent
    scenes = [
        (4.0, scene_title),
        (6.5, scene_architecture),
        (APP_DUR, scene_app),
        (3.5, scene_end),
    ]
    mp4 = out / "demo.mp4"
    print(f"Writing {mp4}")
    render(scenes, mp4)
    scene_title(3.0, 4.0).save(out / "poster.png")
    gif = out / "demo.gif"
    print(f"Writing {gif}")
    make_gif(mp4, gif)
    for f in (mp4, gif, out / "poster.png"):
        print(f"  {f}  {f.stat().st_size / 1_048_576:.1f} MB")
    print("Done. Keep each file under 10 MB for GitHub uploads on a free plan.")


if __name__ == "__main__":
    main()
