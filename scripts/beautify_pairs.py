#!/usr/bin/env python3
"""
Beautify the 2026 Long-Short Pairs into a professional pair trade layout.
SHORT on the LEFT (red), LONG on the RIGHT (green), one row per pair.

Usage:
  python scripts/beautify_pairs.py
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT    = Path(__file__).parent.parent
SRC     = ROOT / "data" / "2026_Long_Short_Pairs_Updated.xlsx"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY        = "1B2A4A"
TEAL_HDR    = "1D6FA4"
CRIMSON_HDR = "8B1A1A"    # SHORT column header
FOREST_HDR  = "1A5C2A"    # LONG column header
RED_BG      = "FEF0F0"    # SHORT cell background
GREEN_BG    = "F0FEF0"    # LONG cell background
RED_TXT     = "8B1A1A"
GREEN_TXT   = "1A5C2A"
RED_BORDER  = "C0392B"
GREEN_BORDER= "27AE60"
WARN_BG     = "FFFBEC"    # ⚠ risk highlight
WARN_TXT    = "7D5A00"
DUPE_BG     = "F3EEFF"    # duplicate-pair row tint
ALT_A       = "F7F9FC"
ALT_B       = "FFFFFF"
GREY_HDR    = "2C3E50"
NOTE_BG     = "F5F5F5"

def _fill(hex_c):
    return PatternFill("solid", fgColor=hex_c)

def _side(color="D0D7DE", style="thin"):
    return Side(style=style, color=color)

def _border(left_color=None, left_style="medium"):
    t = _side()
    l = _side(left_color, left_style) if left_color else t
    return Border(left=l, right=t, top=t, bottom=t)

def _font(bold=False, color="1A1A1A", size=9, italic=False):
    return Font(bold=bold, color=color, size=size, name="Calibri", italic=italic)

def _align(h="left", v="top", wrap=True):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def write_cell(ws, r, c, val, fg="1A1A1A", bg=None, bold=False, size=9,
               italic=False, h="left", v="top", left_border=None, left_style="medium"):
    cell = ws.cell(row=r, column=c, value=val if val != "nan" else "")
    cell.font      = _font(bold=bold, color=fg, size=size, italic=italic)
    cell.alignment = _align(h=h, v=v)
    if bg:
        cell.fill = _fill(bg)
    cell.border = _border(left_color=left_border, left_style=left_style)
    return cell

def estimate_row_height(texts_widths):
    """Rough row-height estimate: chars / col_width * line_height_pt."""
    max_lines = 2
    for text, cw in texts_widths:
        if not isinstance(text, str) or text in ("nan", ""):
            continue
        # Chinese chars count double
        char_w = sum(2 if ord(ch) > 127 else 1 for ch in text) / 2
        lines  = (char_w / max(cw, 1)) + text.count("\n") * 2 + 1
        max_lines = max(max_lines, lines)
    return max(55, min(int(max_lines * 13.5), 240))

# ── Load data ─────────────────────────────────────────────────────────────────
df_all = pd.read_excel(SRC, header=0).fillna("")

# Separate the trailing notes row (starts with "注：")
mask_notes = df_all["板块"].astype(str).str.startswith("注：")
df_notes   = df_all[mask_notes]
df         = df_all[~mask_notes & (df_all["板块"] != "")].reset_index(drop=True)

TODAY       = datetime.today().strftime("%Y-%m-%d")
TODAY_SLUG  = datetime.today().strftime("%Y%m%d")
NUM_PAIRS   = len(df)

# ── Workbook ──────────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "2026 Long-Short Pairs"

ws.page_setup.orientation  = "landscape"
ws.page_setup.paperSize    = 9      # A4
ws.page_setup.fitToPage    = True
ws.page_setup.fitToWidth   = 1
ws.page_setup.fitToHeight  = 0
ws.print_options.gridLines = False

# Column layout: A=No, B=Sector, C=SHORT, D=LONG, E=Thesis, F=Catalyst, G=Risk, H=Earnings
COL_WIDTHS = [4, 11, 21, 20, 52, 34, 40, 46]
for i, w in enumerate(COL_WIDTHS, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

# ── Banner ────────────────────────────────────────────────────────────────────
ws.merge_cells("A1:H1")
ws.merge_cells("A2:H2")

c1 = ws.cell(row=1, column=1,
             value="2026 Long-Short Pair Trade Book  ·  A股量化多空组合")
c1.fill      = _fill(NAVY)
c1.font      = Font(bold=True, color="FFFFFF", size=14, name="Calibri")
c1.alignment = _align(h="center", v="center")
ws.row_dimensions[1].height = 30

c2 = ws.cell(row=2, column=1,
             value=(f"做空(SHORT ◀) 在左  |  做多(LONG ▶) 在右  |  共 {NUM_PAIRS} 组配对  "
                    f"|  更新日期: {TODAY}  |  ⚠ 行 = 需重点确认  |  紫色 = 重复/待调整"))
c2.fill      = _fill(TEAL_HDR)
c2.font      = Font(color="FFFFFF", size=8.5, name="Calibri")
c2.alignment = _align(h="center", v="center")
ws.row_dimensions[2].height = 16

# ── Column headers ─────────────────────────────────────────────────────────────
HEADERS = [
    ("No.",                   GREY_HDR, "FFFFFF", "center"),
    ("板块\nSector",           GREY_HDR, "FFFFFF", "center"),
    ("◀  SHORT 做空",          CRIMSON_HDR, "FFFFFF", "center"),
    ("LONG 做多  ▶",           FOREST_HDR, "FFFFFF", "center"),
    ("2026投资逻辑 / Edge",    GREY_HDR, "FFFFFF", "left"),
    ("后续催化剂\nCatalysts",   GREY_HDR, "FFFFFF", "left"),
    ("⚠  主要风险 / 对冲薄弱点", GREY_HDR, "FFFFFF", "left"),
    ("26Q1实际  &  26Q2/H1展望", GREY_HDR, "FFFFFF", "left"),
]
ws.row_dimensions[3].height = 28
for col, (label, bg, fg, h) in enumerate(HEADERS, 1):
    c = ws.cell(row=3, column=col, value=label)
    c.fill      = _fill(bg)
    c.font      = Font(bold=True, color=fg, size=9, name="Calibri")
    c.alignment = _align(h=h, v="center")
    t = _side("6A7F99")
    c.border    = Border(left=t, right=t, top=t, bottom=t)

ws.freeze_panes = "A4"

# ── Data rows ─────────────────────────────────────────────────────────────────
COLS = ["板块", "Short", "Long", "2026边际变化（投资逻辑）",
        "后续催化剂", "主要风险 / 对冲薄弱点", "26Q1实际 & 26Q2/H1业绩（多 / 空腿）"]

for i, row in df.iterrows():
    r       = i + 4
    sector  = str(row["板块"])
    short_  = str(row["Short"])
    long_   = str(row["Long"])
    thesis  = str(row["2026边际变化（投资逻辑）"])
    catalyst= str(row["后续催化剂"])
    risk    = str(row["主要风险 / 对冲薄弱点"])
    earnings= str(row["26Q1实际 & 26Q2/H1业绩（多 / 空腿）"])

    is_warn = "⚠" in risk
    is_dupe = "重复" in thesis or "国产AI芯片" == sector

    row_bg = DUPE_BG if is_dupe else (ALT_A if i % 2 == 0 else ALT_B)

    # Estimate row height
    h = estimate_row_height([
        (short_,   20), (long_,    18), (thesis,  48),
        (catalyst, 30), (risk,     36), (earnings,42),
    ])
    ws.row_dimensions[r].height = h

    # A — No.
    write_cell(ws, r, 1, str(i + 1), bg=row_bg, bold=True, h="center")

    # B — Sector (bold, sector colour stripe)
    c = write_cell(ws, r, 2, sector, bg=row_bg, bold=True, size=9.5)

    # C — SHORT (red box, thick left border)
    write_cell(ws, r, 3, short_,   fg=RED_TXT,   bg=RED_BG,
               left_border=RED_BORDER, left_style="thick")

    # D — LONG (green box, thick left border)
    write_cell(ws, r, 4, long_,    fg=GREEN_TXT, bg=GREEN_BG,
               left_border=GREEN_BORDER, left_style="thick")

    # E — Thesis
    thesis_bg = DUPE_BG if is_dupe else row_bg
    write_cell(ws, r, 5, thesis, bg=thesis_bg, size=8,
               fg=WARN_TXT if is_dupe else "1A1A1A")

    # F — Catalysts
    write_cell(ws, r, 6, catalyst, bg=row_bg, size=8)

    # G — Risk (amber tint when ⚠ present)
    write_cell(ws, r, 7, risk, bg=WARN_BG if is_warn else row_bg,
               fg=WARN_TXT if is_warn else "1A1A1A", size=8)

    # H — Earnings
    write_cell(ws, r, 8, earnings, bg=row_bg, size=8)

# ── Notes row ─────────────────────────────────────────────────────────────────
if not df_notes.empty:
    nr = NUM_PAIRS + 5
    ws.merge_cells(f"A{nr}:H{nr}")
    note_text = str(df_notes.iloc[0, 0])
    c = ws.cell(row=nr, column=1, value=note_text)
    c.fill      = _fill(NOTE_BG)
    c.font      = Font(italic=True, color="666666", size=7.5, name="Calibri")
    c.alignment = _align(h="left", v="top")
    t = _side("CCCCCC")
    c.border    = Border(left=t, right=t, top=_side("AAAAAA", "medium"), bottom=t)
    ws.row_dimensions[nr].height = 90

# ── Legend row ────────────────────────────────────────────────────────────────
lr = NUM_PAIRS + 7
ws.merge_cells(f"A{lr}:H{lr}")
legend = ws.cell(row=lr, column=1,
                 value="图例 LEGEND:  🔴 RED = SHORT 做空    🟢 GREEN = LONG 做多    "
                       "🟡 AMBER = ⚠ 风险提示    🟣 PURPLE = 重复/待调整组")
legend.font      = Font(bold=False, color="555555", size=8, name="Calibri")
legend.alignment = _align(h="left", v="center")
legend.fill      = _fill("FAFAFA")
ws.row_dimensions[lr].height = 16

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = OUT_DIR / f"pair_trades_{TODAY_SLUG}.xlsx"
wb.save(out_path)
print(f"✅  Saved → {out_path}")
