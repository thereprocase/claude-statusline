#!/usr/bin/env bash
# Interactive status line configurator — theme picker + settings walkthrough.
# Run after install.sh, or standalone to reconfigure.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SL_DIR="${CLAUDE_DIR}/statusline"
THEME_FILE="${CLAUDE_DIR}/statusline-theme"
CONFIG_FILE="${CLAUDE_DIR}/statusline-config.json"

# ── Helpers ──────────────────────────────────────────────────────────────────
bold() { printf '\033[1m%s\033[0m' "$1"; }
dim()  { printf '\033[2m%s\033[0m' "$1"; }

# Resolve python: prefer python3, fall back to python
PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python

THEMES=()
for f in "${SCRIPT_DIR}/themes/"*.py; do
    name=$(basename "$f" .py)
    [[ "$name" == "core" || "$name" == "__init__" ]] && continue
    THEMES+=("$name")
done

CURRENT_THEME=""
[ -f "$THEME_FILE" ] && CURRENT_THEME=$(cat "$THEME_FILE" 2>/dev/null)

# Read current config
MODEL_FMT="short"
SHOW_USER="true"
DATE_FMT="short"
AUTO_HIDE="true"
if [ -f "$CONFIG_FILE" ]; then
    # Single python call reads all values; config path passed via env to avoid interpolation
    _cfg=$(CONFIG_PATH="$CONFIG_FILE" "$PYTHON" -c '
import json, os
p = os.environ["CONFIG_PATH"]
with open(p) as f:
    c = json.load(f)
print(c.get("model_format", "short"))
print(str(c.get("show_user", True)).lower())
print(c.get("date_format", "short"))
print(str(c.get("auto_hide_reset", True)).lower())
' 2>/dev/null) && {
        IFS=$'\n' read -rd '' MODEL_FMT SHOW_USER DATE_FMT AUTO_HIDE <<< "$_cfg" || true
    }
fi

# ── Sample data for previews ────────────────────────────────────────────────
SAMPLE='{"model":{"display_name":"Claude Opus 4.6","id":"claude-opus-4-6-20250415"},"context_window":{"used_percentage":42.0,"context_window_size":1000000},"cwd":"/home/user/projects/my-app","rate_limits":{"five_hour":{"used_percentage":38},"seven_day":{"used_percentage":15}},"session_id":"setup-preview"}'

show_sample() {
    local theme="$1"
    echo "$theme" > "$THEME_FILE"
    echo "$SAMPLE" | bash "${CLAUDE_DIR}/statusline-command.sh" 2>/dev/null || echo "  (preview unavailable)"
}

# ── Ensure files are installed ──────────────────────────────────────────────
if [ ! -d "$SL_DIR" ] || [ ! -f "${CLAUDE_DIR}/statusline-command.sh" ]; then
    echo "Installing status line files first..."
    "${SCRIPT_DIR}/install.sh" "${CURRENT_THEME:-buddy}"
    echo ""
fi

# ── Theme selection ─────────────────────────────────────────────────────────
echo ""
echo "$(bold 'Claude Code Status Line — Setup')"
echo ""
echo "Here are your theme options:"
echo ""

# Curated presentation order
TOP5=(buddy monochrome amber dracula lcars)
REST=(catppuccin rainbow outrun ibm3278 c64 win95 teletext matrix skittles)

declare -A DESCRIPTIONS
DESCRIPTIONS[buddy]="Claude's own colors. The /buddy sunset gradient. (default)"
DESCRIPTIONS[monochrome]="Grayscale. Clean, no color, no nonsense."
DESCRIPTIONS[amber]="Amber phosphor CRT. That warm golden terminal glow."
DESCRIPTIONS[dracula]="The beloved dark palette. Purple, pink, cyan, green."
DESCRIPTIONS[lcars]="Star Trek TNG. Solid colored pill chips, panel bars."
DESCRIPTIONS[catppuccin]="Catppuccin Mocha. Warm pastels, cozy vibes."
DESCRIPTIONS[rainbow]="The original. Smooth gradients, corruption glitch at high context."
DESCRIPTIONS[outrun]="Synthwave. Hot pink, electric cyan, chrome, neon purple."
DESCRIPTIONS[ibm3278]="Green phosphor CRT. Four intensity levels. Mainframe vibes."
DESCRIPTIONS[c64]="Commodore 64. Light blue on dark blue. READY."
DESCRIPTIONS[win95]="Windows 95. Teal title bars, silver bevels, that gray."
DESCRIPTIONS[teletext]="Ceefax/Oracle. Blocky colored headers. Page 100."
DESCRIPTIONS[matrix]="Digital rain. Green katakana code. There is no spoon."
DESCRIPTIONS[skittles]="Every character a different candy color. Unhinged."

show_theme_list() {
    local themes=("$@")
    for theme in "${themes[@]}"; do
        # Skip if theme file doesn't exist
        [ ! -f "${SCRIPT_DIR}/themes/${theme}.py" ] && continue
        current_marker=""
        [[ "$theme" == "$CURRENT_THEME" ]] && current_marker=" $(dim '(current)')"
        echo "  $(bold "$theme")${current_marker}"
        echo "  ${DESCRIPTIONS[$theme]:-No description.}"
        echo ""
    done
}

show_theme_list "${TOP5[@]}"
echo "  $(dim '... more themes available')"
echo ""

read -rp "Which theme, or 'more' to see all? [${CURRENT_THEME:-buddy}]: " THEME_CHOICE

if [[ "$THEME_CHOICE" == "more" ]]; then
    echo ""
    show_theme_list "${TOP5[@]}"
    echo "  $(bold '── more ──')"
    echo ""
    show_theme_list "${REST[@]}"

    read -rp "Which theme? [${CURRENT_THEME:-buddy}]: " THEME_CHOICE
fi

THEME_CHOICE="${THEME_CHOICE:-${CURRENT_THEME:-buddy}}"

# Validate
if [ ! -f "${SCRIPT_DIR}/themes/${THEME_CHOICE}.py" ]; then
    echo "Unknown theme: $THEME_CHOICE"
    exit 1
fi
echo "$THEME_CHOICE" > "$THEME_FILE"

read -rp "Want to see previews? (y/N): " PREVIEW
echo ""
if [[ "$PREVIEW" =~ [yY] ]]; then
    echo ""
    ORIG_THEME="$THEME_CHOICE"
    # Restore original theme if user Ctrl+C's during preview
    trap 'echo "$ORIG_THEME" > "$THEME_FILE"; echo; echo "Preview cancelled, restored $ORIG_THEME"; trap - INT; exit 0' INT
    for theme in "${TOP5[@]}" "${REST[@]}"; do
        [ ! -f "${SCRIPT_DIR}/themes/${theme}.py" ] && continue
        marker=""
        [[ "$theme" == "$THEME_CHOICE" ]] && marker=" <--"
        echo "  [${theme}]${marker}"
        show_sample "$theme"
        echo ""
    done
    trap - INT
    echo "$THEME_CHOICE" > "$THEME_FILE"
    read -rp "Stick with $(bold "$THEME_CHOICE"), or switch? [${THEME_CHOICE}]: " SWITCH
    SWITCH="${SWITCH:-$THEME_CHOICE}"
    if [ -f "${SCRIPT_DIR}/themes/${SWITCH}.py" ]; then
        THEME_CHOICE="$SWITCH"
        echo "$THEME_CHOICE" > "$THEME_FILE"
    fi
fi

echo ""
echo "Theme: $(bold "$THEME_CHOICE")"
echo ""

# ── Model format ────────────────────────────────────────────────────────────
echo "$(bold 'Model name format:')"
echo ""
echo "  short  →  Op46"
echo "  long   →  Opus 4.6"
echo "  full   →  Claude Opus 4.6"
echo ""
read -rp "Which format? [${MODEL_FMT}]: " MF
MF="${MF:-$MODEL_FMT}"
case "$MF" in
    short|long|full) MODEL_FMT="$MF" ;;
    *) echo "Invalid model format '$MF', keeping '${MODEL_FMT}'." ;;
esac
echo ""

# ── User initials ───────────────────────────────────────────────────────────
echo "$(bold 'User initials') (2-char chip at the start):"
echo ""
echo "  on   →  shows your account prefix"
echo "  off  →  hidden, saves space"
echo ""
read -rp "On or off? [$([ "$SHOW_USER" = "true" ] && echo "on" || echo "off")]: " SU
case "${SU:-$([ "$SHOW_USER" = "true" ] && echo "on" || echo "off")}" in
    on|yes|true) SHOW_USER="true" ;;
    *)           SHOW_USER="false" ;;
esac
echo ""

# ── Date format ─────────────────────────────────────────────────────────────
echo "$(bold 'Date/reset format:')"
echo ""
echo "  short  →  3p, th"
echo "  long   →  3:00pm, thu"
echo ""
read -rp "Short or long? [${DATE_FMT}]: " DF
DF="${DF:-$DATE_FMT}"
case "$DF" in
    short|long) DATE_FMT="$DF" ;;
    *) echo "Invalid date format '$DF', keeping '${DATE_FMT}'." ;;
esac
echo ""

# ── Auto-hide ───────────────────────────────────────────────────────────────
echo "$(bold 'Auto-hide reset times') when usage is low:"
echo ""
echo "  on   →  hides reset when 5H < 50% and 7D < 80%"
echo "  off  →  always shows reset time"
echo ""
read -rp "On or off? [$([ "$AUTO_HIDE" = "true" ] && echo "on" || echo "off")]: " AH
case "${AH:-$([ "$AUTO_HIDE" = "true" ] && echo "on" || echo "off")}" in
    on|yes|true) AUTO_HIDE="true" ;;
    *)           AUTO_HIDE="false" ;;
esac

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "$(bold 'Your config:')"
echo ""
echo "  Theme:       ${THEME_CHOICE}"
echo "  Model:       ${MODEL_FMT}"
echo "  Initials:    $([ "$SHOW_USER" = "true" ] && echo "on" || echo "off")"
echo "  Dates:       ${DATE_FMT}"
echo "  Auto-hide:   $([ "$AUTO_HIDE" = "true" ] && echo "on" || echo "off")"
echo ""

read -rp "Save as defaults? (Y/n): " SAVE
if [[ ! "$SAVE" =~ [nN] ]]; then
    # Pass all values via env; no shell interpolation enters Python source.
    # Atomic write (tempfile + os.replace) prevents partial settings on crash.
    CFG_PATH="$CONFIG_FILE" \
    CFG_MODEL_FMT="$MODEL_FMT" \
    CFG_SHOW_USER="$SHOW_USER" \
    CFG_DATE_FMT="$DATE_FMT" \
    CFG_AUTO_HIDE="$AUTO_HIDE" \
    "$PYTHON" -c '
import json, os, tempfile
path      = os.environ["CFG_PATH"]
model_fmt = os.environ["CFG_MODEL_FMT"]
show_user = os.environ["CFG_SHOW_USER"] == "true"
date_fmt  = os.environ["CFG_DATE_FMT"]
auto_hide = os.environ["CFG_AUTO_HIDE"] == "true"
cfg = {
    "model_format":    model_fmt,
    "show_user":       show_user,
    "date_format":     date_fmt,
    "auto_hide_reset": auto_hide,
}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w") as t:
        json.dump(cfg, t, indent=2)
    os.replace(tmp, path)
except Exception:
    os.unlink(tmp)
    raise
'
    echo "Saved to ${CONFIG_FILE}"
fi

echo ""
echo "Done. Changes take effect on the next Claude Code tool call."
