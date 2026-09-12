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
  - thumbnail_slide(big_text, kicker)   -- 1280x720 clickable thumbnail (custom, not
                                            an auto-picked video frame)
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

# Charts are rendered at one of these fixed figure sizes, then scaled to
# fit whatever the current canvas is -- see _finish_chart_canvas. A wide
# canvas (landscape) gets a wide chart; a tall one (vertical/Shorts) gets a
# squarer chart, so the chart actually uses the available height instead of
# sitting small in the middle of a lot of empty space below it.
CHART_FIG_LANDSCAPE = (12, 7)
CHART_FIG_VERTICAL = (9, 8)

def chart_figsize():
    return CHART_FIG_VERTICAL if H > W else CHART_FIG_LANDSCAPE

def set_dimensions(w, h):
    """Switch the canvas size used by every slide function below. Call this
    once per episode, before rendering any of its slides, based on the
    episode's own "format" field (see build_video.build): "vertical" for a
    9:16 YouTube Shorts canvas (1080x1920), anything else (or absent) for
    the default 16:9 landscape canvas (1920x1080). All the layout math in
    this module works off the W/H globals, so nothing else needs to change
    per-orientation."""
    global W, H
    W, H = w, h

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
    area_top, area_bottom = 280, H - 80
    scale = min((W - 160) / cw, (area_bottom - area_top) / ch)
    cw2, ch2 = int(cw * scale), int(ch * scale)
    chart_img = chart_img.resize((cw2, ch2))
    paste_y = area_top + (area_bottom - area_top - ch2) // 2
    img.paste(chart_img, ((W - cw2) // 2, paste_y))
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
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=chart_figsize(), dpi=100)
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
    fig, ax = plt.subplots(figsize=chart_figsize(), dpi=100)
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

def intro_slide(path, hook=None):
    """Channel-branded cold open, shown first on every episode.

    If `hook` is given (the episode's own punchy one-line tease, spoken as
    the very first thing in the video -- see build_video.INTRO_TEXT), it is
    rendered big and first, with the brand mark small underneath instead of
    dominating the frame. This is the pattern-interrupt: a viewer who has
    just clicked in from a thumbnail should see the specific hook they
    clicked for immediately, not three seconds of an unfamiliar logo. With
    no hook (legacy episodes), falls back to the original logo-first frame.
    """
    img, d = base_canvas()
    if hook:
        font = ImageFont.truetype(SERIF_BOLD, 72)
        lines = wrap_text(d, hook, font, W - 280)
        total_h = len(lines) * 92
        y = (H - total_h) // 2 - 60
        for line in lines:
            w_ = d.textlength(line, font=font)
            d.text(((W - w_) // 2, y), line, font=font, fill=INK)
            y += 92

        cx, cy = W // 2, int(H * 0.82)
        draw_logo_mark(d, cx, cy, r_o=30, r_i=18, dot_r=7)
        f2 = ImageFont.truetype(SANS_BOLD, 26)
        w_ = d.textlength(BRAND, font=f2)
        d.text((cx + 46, cy - 13), BRAND, font=f2, fill=INK_SOFT)
    else:
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

def thumbnail_slide(path, big_text, kicker=None):
    """Custom 1280x720 clickable thumbnail (YouTube's required min size,
    used regardless of the episode's own vertical/landscape canvas). Built
    independently of the W/H globals so calling this never disturbs
    whatever canvas size the rest of the episode is using.

    Without this, YouTube auto-picks a frame from the finished video as the
    thumbnail -- almost always a flat, low-contrast slide with no hook,
    which is one of the biggest drags on click-through for a new channel.

    `big_text`: the punchy few-word hook, e.g. "10 YEARS BEATS 30" or
    "$421K vs $365K" -- keep it under ~5 words / 24 characters so it reads
    at small size in a feed. `kicker`: optional short line above it in the
    accent color, e.g. "SAME $300/MONTH".
    """
    TW, TH = 1280, 720
    img = Image.new("RGB", (TW, TH), BG)
    d = ImageDraw.Draw(img)

    # Subtle corner glow using the brand gradient so it doesn't read as a
    # flat/generic card, without competing with the text for attention.
    for i in range(3):
        r = 520 - i * 90
        alpha_color = tuple(int(BG[k] + (VIOLET[k] - BG[k]) * (0.10 - i * 0.03)) for k in range(3))
        d.ellipse([TW - r * 0.7, -r * 0.6, TW + r * 0.3, r * 0.6], fill=alpha_color)

    max_w = TW - 140

    def fit_font(text, start_size, min_size=64):
        size = start_size
        while size > min_size:
            f = ImageFont.truetype(SANS_BOLD, size)
            if d.textlength(text, font=f) <= max_w:
                return f, size
            size -= 4
        return ImageFont.truetype(SANS_BOLD, min_size), min_size

    lines = []
    if len(big_text) > 15 and " " in big_text:
        words = big_text.split()
        mid = len(words) // 2
        # Prefer breaking near the middle at a word boundary so both lines
        # are visually balanced rather than one long + one short.
        best = min(range(1, len(words)), key=lambda i: abs(i - mid))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    else:
        lines = [big_text]

    font, size = fit_font(max(lines, key=len), 148)
    line_h = int(size * 1.18)
    total_h = line_h * len(lines)

    y0 = (TH - total_h) // 2
    if kicker:
        y0 += 34  # make room for the kicker line above without recentering everything

    y = y0
    for i, line in enumerate(lines):
        f = font
        w_ = d.textlength(line, font=f)
        # Highlight the last line in peach so there's one clear accent
        # color in the frame, not flat white-on-dark throughout.
        color = PEACH if i == len(lines) - 1 else INK
        # Simple 1-2px dark outline for legibility over the glow/background
        # at small feed sizes, without needing an image filter pass.
        ox, oy = (TW - w_) // 2, y
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            d.text((ox + dx, oy + dy), line, font=f, fill=(12, 10, 16))
        d.text((ox, oy), line, font=f, fill=color)
        y += line_h

    if kicker:
        kf = ImageFont.truetype(SANS_BOLD, 34)
        kw = d.textlength(kicker.upper(), font=kf)
        d.text(((TW - kw) // 2, y0 - 34), kicker.upper(), font=kf, fill=INK_SOFT)

    # Small wordmark bottom-left so the brand is still identifiable in a
    # feed without stealing attention from the hook text.
    wf = ImageFont.truetype(SANS_BOLD, 24)
    d.text((36, TH - 56), WORDMARK, font=wf, fill=INK_SOFT)

    img.save(path)
