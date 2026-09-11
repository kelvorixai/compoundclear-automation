"""
CompoundClear branded slide rendering.

Generic primitives so future episodes (any topic) can be authored as data
(content/episodes/*.json) instead of new Python code:
  - statement_slide(text)               -- big centered serif statement
  - chart_slide(headline, sub, points, mark)  -- line chart w/ one highlighted point
  - bars_slide(headline, labels, values)      -- bar chart
  - closing_slide(lines)                -- content payoff line w/ logo mark
  - intro_slide()                       -- channel-branded cold open (every episode)
  - outro_slide()                       -- channel-branded subscribe CTA (every episode)
"""
import os
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = (23, 19, 32)
INK = (239, 234, 245)
INK_SOFT = (180, 172, 196)
PEACH = (240, 163, 120)
VIOLET = (143, 117, 208)
BGf = tuple(c / 255 for c in BG)
INKf = tuple(c / 255 for c in INK)
PEACHf = tuple(c / 255 for c in PEACH)
VIOLETf = tuple(c / 255 for c in VIOLET)

FONT_DIR = "/usr/share/fonts/truetype/liberation"
SERIF_BOLD = f"{FONT_DIR}/LiberationSerif-Bold.ttf"
SANS = f"{FONT_DIR}/LiberationSans-Regular.ttf"
SANS_BOLD = f"{FONT_DIR}/LiberationSans-Bold.ttf"

W, H = 1920, 1080
WORDMARK = "COMPOUNDCLEAR"
BRAND = "CompoundClear"
TAGLINE = "Plain-English guides to how money actually works"


def base_canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def draw_wordmark(draw, y=60):
    f = ImageFont.truetype(SANS_BOLD, 30)
    draw.text((70, y), WORDMARK, font=f, fill=INK_SOFT)


def statement_slide(text, path):
    img, d = base_canvas()
    draw_wordmark(d)
    font = ImageFont.truetype(SERIF_BOLD, 78)
    lines = wrap_text(d, text, font, W - 320)
    total_h = len(lines) * 96
    y = (H - total_h) // 2
    for line in lines:
        w_ = d.textlength(line, font=font)
        d.text(((W - w_) // 2, y), line, font=font, fill=INK)
        y += 96
    img.save(path)


def _finish_chart_canvas(fig, path, headline, sub):
    tmp = path + ".tmp.png"
    fig.savefig(tmp, facecolor=BGf)
    plt.close(fig)
    chart_img = Image.open(tmp).convert("RGB")
    os.remove(tmp)

    img, d = base_canvas()
    draw_wordmark(d)
    cw, ch = chart_img.size
    scale = min((W - 160) / cw, (H * 0.62) / ch)
    cw2, ch2 = int(cw * scale), int(ch * scale)
    chart_img = chart_img.resize((cw2, ch2))
    img.paste(chart_img, ((W - cw2) // 2, int(H * 0.30)))
    d = ImageDraw.Draw(img)

    if headline:
        hfont = ImageFont.truetype(SERIF_BOLD, 60)
        w_ = d.textlength(headline, font=hfont)
        d.text(((W - w_) // 2, 150), headline, font=hfont, fill=INK)
    if sub:
        sfont = ImageFont.truetype(SANS, 32)
        w_ = d.textlength(sub, font=sfont)
        d.text(((W - w_) // 2, 232), sub, font=sfont, fill=PEACH)

    img.save(path)


def chart_slide(path, headline, sub, points, mark=None, y_max=None, x_label="", y_label=""):
    """points: list of [x, y]. mark: optional [x, y] highlighted dot."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor(BGf)
    ax.set_facecolor(BGf)
    ax.plot(xs, ys, color=PEACHf, linewidth=5, solid_capstyle="round")
    if mark:
        ax.scatter([mark[0]], [mark[1]], color=INKf, s=140, zorder=5)
    ax.set_xlim(min(xs), max(xs))
    if y_max:
        ax.set_ylim(0, y_max)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=(0.7, 0.67, 0.76), labelsize=14)
    if x_label:
        ax.set_xlabel(x_label, color=(0.7, 0.67, 0.76), fontsize=16)
    if y_label:
        ax.set_ylabel(y_label, color=(0.7, 0.67, 0.76), fontsize=16)
    ax.grid(True, color=(1, 1, 1), alpha=0.06)
    plt.tight_layout(rect=[0.03, 0.28, 0.97, 0.97])
    _finish_chart_canvas(fig, path, headline, sub)


def bars_slide(path, headline, labels, values, y_max=None, colors=None):
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor(BGf)
    ax.set_facecolor(BGf)
    bar_colors = colors or [PEACHf if i < len(values) / 2 else VIOLETf for i in range(len(values))]
    bars = ax.bar(labels, values, color=bar_colors, width=0.55)
    top = y_max or (max(values) * 1.2)
    for rect, v in zip(bars, values):
        ax.text(rect.get_x() + rect.get_width() / 2, v + top * 0.02, f"${v:,.0f}",
                ha="center", color=INKf, fontsize=20, fontweight="bold")
    ax.set_ylim(0, top)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=(0.7, 0.67, 0.76), labelsize=18)
    ax.get_yaxis().set_visible(False)
    plt.tight_layout(rect=[0.03, 0.28, 0.97, 0.97])
    _finish_chart_canvas(fig, path, headline, None)


def draw_logo_mark(d, cx, cy, r_o=46, r_i=28, dot_r=11):
    """The CompoundClear ring mark -- a peach-to-violet gradient arc with a
    solid center dot, evoking a compounding curve looping back on itself."""
    th = r_o - r_i
    steps = 100
    start_deg, end_deg = 55, 305
    for i in range(steps):
        t0 = start_deg + (end_deg - start_deg) * (i / steps)
        t1 = start_deg + (end_deg - start_deg) * ((i + 1) / steps)
        t = i / steps
        color = tuple(int(PEACH[k] + (VIOLET[k] - PEACH[k]) * t) for k in range(3))
        bbox = [cx - r_o, cy - r_o, cx + r_o, cy + r_o]
        d.arc(bbox, t0, t1, fill=color, width=th)
    d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=INK)


def closing_slide(path, lines):
    img, d = base_canvas()
    font = ImageFont.truetype(SERIF_BOLD, 66)
    total_h = len(lines) * 90
    y = (H - total_h) // 2 - 60
    for line in lines:
        w_ = d.textlength(line, font=font)
        d.text(((W - w_) // 2, y), line, font=font, fill=INK)
        y += 90

    cx, cy = W // 2, int(H * 0.74)
    draw_logo_mark(d, cx, cy, r_o=46, r_i=28, dot_r=11)

    f2 = ImageFont.truetype(SANS_BOLD, 40)
    w_ = d.textlength(BRAND, font=f2)
    d.text(((W - w_) // 2, cy + 70), BRAND, font=f2, fill=INK)

    f3 = ImageFont.truetype(SANS, 26)
    w_ = d.textlength(TAGLINE, font=f3)
    d.text(((W - w_) // 2, cy + 126), TAGLINE, font=f3, fill=INK_SOFT)

    img.save(path)


def intro_slide(path):
    """Channel-branded cold open, shown first on every episode."""
    img, d = base_canvas()
    cx, cy = W // 2, int(H * 0.44)
    draw_logo_mark(d, cx, cy, r_o=70, r_i=44, dot_r=16)

    f2 = ImageFont.truetype(SANS_BOLD, 64)
    w_ = d.textlength(BRAND, font=f2)
    d.text(((W - w_) // 2, cy + 110), BRAND, font=f2, fill=INK)

    f3 = ImageFont.truetype(SANS, 30)
    w_ = d.textlength(TAGLINE, font=f3)
    d.text(((W - w_) // 2, cy + 190), TAGLINE, font=f3, fill=INK_SOFT)

    img.save(path)


def outro_slide(path):
    """Channel-branded subscribe CTA, shown last on every episode."""
    img, d = base_canvas()
    cx, cy = W // 2, int(H * 0.38)
    draw_logo_mark(d, cx, cy, r_o=60, r_i=38, dot_r=14)

    f2 = ImageFont.truetype(SANS_BOLD, 56)
    w_ = d.textlength(BRAND, font=f2)
    d.text(((W - w_) // 2, cy + 100), BRAND, font=f2, fill=INK)

    f3 = ImageFont.truetype(SANS, 28)
    w_ = d.textlength(TAGLINE, font=f3)
    d.text(((W - w_) // 2, cy + 168), TAGLINE, font=f3, fill=INK_SOFT)

    f4 = ImageFont.truetype(SANS_BOLD, 40)
    cta = "Subscribe for more"
    w_ = d.textlength(cta, font=f4)
    d.text(((W - w_) // 2, cy + 240), cta, font=f4, fill=PEACH)

    img.save(path)
