#!/usr/bin/env python3
"""Generate SVG renders of the statusline at various context percentages."""

import subprocess, json, os, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, 'statusline-command.sh')
OUT_DIR = os.path.join(SCRIPT_DIR, 'images')

SCENARIOS = [
    (30,  "30%  · clean"),
    (55,  "55%  · threshold"),
    (60,  "60%  · it begins"),
    (65,  "65%  · aggressive"),
    (80,  "80%  · deteriorating"),
    (95,  "95%  · critical"),
    (100, "100% · consumed"),
]


def make_payload(pct):
    now = int(time.time())
    return json.dumps({
        "model": {"display_name": "Claude Opus 4.6", "id": "claude-opus-4-6-20250414"},
        "context_window": {"used_percentage": pct, "context_window_size": 1000000},
        "cwd": "D:/ClauDe/tools/claude-statusline",
        "rate_limits": {
            "five_hour":  {"used_percentage": 42, "resets_at": str(now + 7200)},
            "seven_day":  {"used_percentage": 18, "resets_at": str(now + 86400 * 3)},
        }
    })


def get_ansi_output(pct):
    result = subprocess.run(
        ['bash', SCRIPT],
        input=make_payload(pct).encode('utf-8'),
        capture_output=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    return result.stdout.decode('utf-8')


# ── 256-color → RGB ─────────────────────────────────────────────────────────

def color256(n):
    if n < 16:
        t = [(0,0,0),(187,0,0),(0,187,0),(187,187,0),(0,0,187),(187,0,187),
             (0,187,187),(187,187,187),(85,85,85),(255,85,85),(85,255,85),
             (255,255,85),(85,85,255),(255,85,255),(85,255,255),(255,255,255)]
        return t[n]
    if n < 232:
        n -= 16
        v = [0, 95, 135, 175, 215, 255]
        return (v[n // 36], v[(n % 36) // 6], v[n % 6])
    g = 8 + (n - 232) * 10
    return (g, g, g)


# ── ANSI parser ─────────────────────────────────────────────────────────────

DEFAULT_FG = (187, 187, 187)
TERM_BG    = (13, 17, 23)      # #0d1117

def parse_ansi(raw):
    """Return [(char, fg_rgb, bg_rgb|None, bold)]."""
    out = []
    fg, bg = DEFAULT_FG, None
    bold = dim = reverse = False

    i = 0
    while i < len(raw):
        if raw[i] == '\033' and i + 1 < len(raw) and raw[i+1] == '[':
            j = i + 2
            while j < len(raw) and raw[j] != 'm':
                j += 1
            codes = []
            for p in raw[i+2:j].split(';'):
                try:    codes.append(int(p))
                except: codes.append(0)
            k = 0
            while k < len(codes):
                c = codes[k]
                if   c == 0:  fg, bg = DEFAULT_FG, None; bold = dim = reverse = False
                elif c == 1:  bold = True
                elif c == 2:  dim = True
                elif c == 5:  pass                          # blink → ignore
                elif c == 7:  reverse = True
                elif c == 9:  pass                          # strike → ignore
                elif c == 38 and k+2 < len(codes) and codes[k+1] == 5:
                    fg = color256(codes[k+2]); k += 2
                elif c == 48 and k+2 < len(codes) and codes[k+1] == 5:
                    bg = color256(codes[k+2]); k += 2
                k += 1
            i = j + 1
        else:
            ef = tuple(max(0, int(c * 0.5)) for c in fg) if dim else fg
            eb = bg
            if reverse:
                ef, eb = (eb or TERM_BG), ef
            out.append((raw[i], ef, eb, bold))
            i += 1
    return out


# ── SVG renderer ────────────────────────────────────────────────────────────

def xml(ch):
    return {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;'}.get(ch, ch)

FONT = "JetBrains Mono, Cascadia Code, Consolas, monospace"

def render_stacked_svg(rows, cw=8.4, rh=28, fs=14, pad=16, lw=170):
    """rows: [(label, chars)] — one per scenario."""
    max_ch = max(len(ch) for _, ch in rows)
    w = lw + max_ch * cw + pad * 2
    title_h = 28
    h = title_h + len(rows) * rh + pad * 2

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">',
        f'  <style>text {{ font-family: {FONT}; }}</style>',
        f'  <rect width="100%" height="100%" rx="8" fill="#0d1117"/>',
        f'  <text x="{pad}" y="{pad + 15}" font-size="13" fill="#8b949e" font-weight="bold">context window corruption</text>',
    ]

    for ri, (label, chars) in enumerate(rows):
        yb = pad + title_h + ri * rh
        yt = yb + rh * 0.7

        # Row separator line (subtle)
        if ri > 0:
            lines.append(f'  <line x1="{pad}" y1="{yb}" x2="{w - pad}" y2="{yb}" stroke="#21262d" stroke-width="1"/>')

        # Label
        lines.append(f'  <text x="{pad}" y="{yt:.1f}" font-size="11.5" fill="#8b949e">{xml(label)}</text>')

        # Statusline characters
        for ci, (ch, fg, bg, bld) in enumerate(chars):
            x = pad + lw + ci * cw
            if bg:
                lines.append(f'  <rect x="{x:.1f}" y="{yb}" width="{cw}" height="{rh}" fill="rgb({bg[0]},{bg[1]},{bg[2]})"/>')
            fill = f"rgb({fg[0]},{fg[1]},{fg[2]})"
            bw = ' font-weight="bold"' if bld else ''
            lines.append(f'  <text x="{x:.1f}" y="{yt:.1f}" font-size="{fs}"{bw} fill="{fill}">{xml(ch)}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def render_single_svg(chars, cw=8.4, rh=30, fs=14, pad=12):
    """Render a single statusline row as SVG (for hero image)."""
    w = len(chars) * cw + pad * 2
    h = rh + pad * 2

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">',
        f'  <style>text {{ font-family: {FONT}; }}</style>',
        f'  <rect width="100%" height="100%" rx="6" fill="#0d1117"/>',
    ]
    yt = pad + rh * 0.7
    for ci, (ch, fg, bg, bld) in enumerate(chars):
        x = pad + ci * cw
        if bg:
            lines.append(f'  <rect x="{x:.1f}" y="{pad}" width="{cw}" height="{rh}" fill="rgb({bg[0]},{bg[1]},{bg[2]})"/>')
        fill = f"rgb({fg[0]},{fg[1]},{fg[2]})"
        bw = ' font-weight="bold"' if bld else ''
        lines.append(f'  <text x="{x:.1f}" y="{yt:.1f}" font-size="{fs}"{bw} fill="{fill}">{xml(ch)}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for pct, label in SCENARIOS:
        raw = get_ansi_output(pct)
        chars = parse_ansi(raw)
        rows.append((label, chars))
        print(f"  {pct:3d}%  {len(chars)} visible chars")

    # Stacked progression image
    svg = render_stacked_svg(rows)
    p = os.path.join(OUT_DIR, 'corruption-progression.svg')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f"wrote {p}")

    # Hero image: clean 30% render
    hero = render_single_svg(rows[0][1])
    p = os.path.join(OUT_DIR, 'statusline-hero.svg')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(hero)
    print(f"wrote {p}")

    # Also save the clean single-row hero
    p2 = os.path.join(OUT_DIR, 'statusline-clean.svg')
    with open(p2, 'w', encoding='utf-8') as f:
        f.write(hero)
    print(f"wrote {p2}")


if __name__ == '__main__':
    main()
