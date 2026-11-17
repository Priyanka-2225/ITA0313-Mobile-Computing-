"""Runs every task program, stores its console output (output.txt) and renders a
terminal-style screenshot of the run (screenshot_output.png).  The programs
themselves save their result graphs (screenshot_graph*.png).

Usage:  python3 generate_all.py        (needs: Python 3, numpy, matplotlib, Pillow)
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS = [
    ("Task01_02_Strategies", "task01_02_strategies.py"),
    ("Task03_Analytical_Model", "task03_analytical.py"),
    ("Task04_05_Behaviour_Scaling", "task04_05_scaling.py"),
    ("Task06_07_Cell_Splitting", "task06_07_splitting.py"),
    ("Task08_09_10_Simulator", "task08_09_10_simulator.py"),
    ("Task11_12_Final_Design_Event", "task11_12_design_event.py"),
]
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
if not os.path.exists(MONO):                       # fall back to Pillow's default font on other systems
    MONO = MONO_B = None


def font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def terminal_png(cmd, text, path):
    f, fb = font(MONO, 15), font(MONO_B, 15)
    lines = text.rstrip("\n").split("\n")
    cw, lh, pad, bar = f.getlength("M"), 21, 18, 34
    w = int(max(len(l) for l in lines + ["$ python3 " + cmd]) * cw + 2 * pad)
    h = bar + pad * 2 + lh * (len(lines) + 2)
    img = Image.new("RGB", (w, h), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, bar], fill=(58, 58, 58))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((w // 2 - 130, 8), "Terminal - " + cmd, font=f, fill=(200, 200, 200))
    y = bar + pad
    d.text((pad, y), "$ python3 " + cmd, font=fb, fill=(120, 220, 120))
    y += lh
    for l in lines:
        col = (235, 235, 235)
        if l.startswith(("TASK", "STRATEGY", "SIMULATOR", "Base case", "3.", "Extended", "Blocking probability")):
            col = (120, 190, 255)
        d.text((pad, y), l, font=f, fill=col)
        y += lh
    d.text((pad, y + 4), "$ _", font=fb, fill=(120, 220, 120))
    img.save(path)


for folder, script in JOBS:
    d = os.path.join(ROOT, folder)
    out = subprocess.run([sys.executable, script], cwd=d, capture_output=True, text=True, check=True).stdout
    open(os.path.join(d, "output.txt"), "w", encoding="utf-8").write(out)
    terminal_png(script, out, os.path.join(d, "screenshot_output.png"))
    print("done", folder)
