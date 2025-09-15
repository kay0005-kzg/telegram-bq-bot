from telegram import Update
from telegram.constants import ParseMode
# import html
from textwrap import wrap

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import time

# from math import ceil
# from collections import defaultdict
# from prettytable import PrettyTable
# ---------- TableFormatter (auto-fit + wrapping) ----------
# class TableFormatter:
#     """
#     Pretty box-drawing tables for Telegram (monospace).
#     - Auto-computes column widths
#     - Optional max_width to auto-wrap cells so the whole table fits
#     - Right-aligns numeric columns, left-aligns text
#     """

#     def __init__(self, headers, rows, pad=1, min_col_width=3, fixed_widths=None):
#         self.headers = [str(h) for h in headers]
#         self.rows = [[("" if c is None else str(c)) for c in r] for r in rows]
#         self.pad = pad
#         self.min_col_width = max(1, min_col_width)
#         self.fixed_widths = fixed_widths  # <= NEW # e.g. [20, None, 8, 12, 10, 8]

#     def format(self, max_width=None):
#         widths = self._natural_widths()

#         if self.fixed_widths:
#             widths = [
#                 max(self.min_col_width, fw) if isinstance(fw, int) else w
#                 for w, fw in zip(widths, self.fixed_widths)
#             ]
        
#         if max_width:
#             widths = self._shrink_to_fit(widths, max_width)

#         lines = []
#         top = self._hline("┌", "┬", "┐", widths)
#         mid = self._hline("├", "┼", "┤", widths)
#         bot = self._hline("└", "┴", "┘", widths)

#         lines.append(top)
#         lines.extend(self._render_row(self.headers, widths, header=True))
#         lines.append(mid)
#         for r in self.rows:
#             lines.extend(self._render_row(r, widths))
#         lines.append(bot)
#         return "\n".join(lines)

#     # ---- internal helpers ----
#     def _natural_widths(self):
#         n = len(self.headers)
#         widths = [len(self.headers[i]) for i in range(n)]
#         for row in self.rows:
#             for i, cell in enumerate(row):
#                 widths[i] = max(widths[i], *(len(s) for s in cell.splitlines()))
#         return widths

#     def _table_width(self, col_widths):
#         n = len(col_widths)
#         return (n + 1) + sum(w + 2 * self.pad for w in col_widths)

#     def _shrink_to_fit(self, widths, max_width):
#         widths = widths[:]
#         if self._table_width(widths) <= max_width:
#             return widths
#         while self._table_width(widths) > max_width:
#             candidates = [i for i, w in enumerate(widths) if w > self.min_col_width]
#             if not candidates:
#                 break
#             i = max(candidates, key=lambda j: widths[j])
#             widths[i] -= 1
#         return widths

#     def _hline(self, left, mid, right, widths):
#         segs = [("─" * (w + 2 * self.pad)) for w in widths]
#         return left + mid.join(segs) + right

#     def _is_numeric(self, s: str) -> bool:
#         s = s.strip()
#         if not s:
#             return False
#         return all(ch.isdigit() or ch in "+-., " for ch in s) and any(ch.isdigit() for ch in s)

#     def _wrap_cell(self, text, width):
#         width = max(1, width)
#         lines = []
#         for block in text.splitlines() or [""]:
#             wrapped = wrap(block, width=width, replace_whitespace=False, drop_whitespace=False,
#                            break_long_words=True, break_on_hyphens=True)
#             lines.extend(wrapped or [""])
#         return lines or [""]

#     def _render_row(self, cells, widths, header=False):
#         wrapped_cols = [self._wrap_cell(cells[i], widths[i]) for i in range(len(widths))]
#         height = max(len(col) for col in wrapped_cols)

#         lines = []
#         for row_line in range(height):
#             parts = []
#             for i, col in enumerate(wrapped_cols):
#                 segment = col[row_line] if row_line < len(col) else ""
#                 if header:
#                     segment = segment.center(widths[i])
#                 elif self._is_numeric(cells[i]):
#                     segment = segment.rjust(widths[i])
#                 else:
#                     segment = segment.ljust(widths[i])
#                 parts.append(" " * self.pad + segment + " " * self.pad)
#             lines.append("│" + "│".join(parts) + "│")
#         return lines
# ---- unicode "font" converter ----
STYLES = {
    "mono":          {"A":0x1D670, "a":0x1D68A, "0":0x1D7F6},  # Mathematical Monospace
    "sans":          {"A":0x1D5A0, "a":0x1D5BA, "0":0x1D7E2},  # Sans-serif
    "sans_bold":     {"A":0x1D5D4, "a":0x1D5EE, "0":0x1D7EC},  # Sans-serif Bold
    "serif_bold":    {"A":0x1D400, "a":0x1D41A, "0":0x1D7CE},  # Bold
    "serif_italic":  {"A":0x1D434, "a":0x1D44E, "0":None},     # Italic (no special digits)
    "serif_bi":      {"A":0x1D468, "a":0x1D482, "0":None},     # Bold Italic
    "fullwidth":     {"A":0xFF21,  "a":0xFF41,  "0":0xFF10, "space":0x3000},  # Ｆｕｌｌｗｉｄｔｈ
}

def stylize(text: str, style: str = "mono") -> str:
    spec = STYLES.get(style)
    if not spec:
        raise ValueError(f"Unknown style '{style}'. Try: {', '.join(STYLES)}")

    out = []
    for ch in text:
        o = ch
        if "A" <= ch <= "Z" and spec.get("A") is not None:
            o = chr(spec["A"] + (ord(ch) - ord("A")))
        elif "a" <= ch <= "z" and spec.get("a") is not None:
            o = chr(spec["a"] + (ord(ch) - ord("a")))
        elif "0" <= ch <= "9" and spec.get("0") is not None:
            o = chr(spec["0"] + (ord(ch) - ord("0")))
        elif ch == " " and style == "fullwidth" and "space" in spec:
            o = chr(spec["space"])  # optional fullwidth space
        out.append(o)
    return "".join(out)

def get_date_range_header():
    """Get the current time and date range for the header."""
    now_bkk = datetime.now(ZoneInfo("Asia/Bangkok"))
    current_time = now_bkk.strftime("%H:%M")
    current_date = now_bkk.strftime("%Y-%m-%d")
    
    dates = [
        current_date,
        (now_bkk - timedelta(days=1)).strftime("%Y-%m-%d"),
        (now_bkk - timedelta(days=2)).strftime("%Y-%m-%d")
    ]
    return current_time, dates

class TableFormatter:
    """
    Pretty tables for Telegram (monospace).
    - Auto-computes column widths
    - Optional max_width to auto-wrap cells so the whole table fits
    - Right-aligns numeric columns, left-aligns text
    - Styles: 'unicode' (default) or 'ascii' (with optional dashed horizontals)
    """

    def __init__(self, headers, rows, pad=1, min_col_width=3, fixed_widths=None,
                 style="unicode", dashed=False):
        self.headers = [str(h) for h in headers]
        self.rows = [[("" if c is None else str(c)) for c in r] for r in rows]
        self.pad = pad
        self.min_col_width = max(1, min_col_width)
        self.fixed_widths = fixed_widths
        self._set_style(style, dashed)

    def _set_style(self, style, dashed):
        if style == "ascii":
            h = "- " if dashed else "-"
            self.chars = {
                "tl": "+", "tm": "+", "tr": "+",
                "ml": "+", "mm": "+", "mr": "+",
                "bl": "+", "bm": "+", "br": "+",
                "v":  "|", "h":  h
            }
        else:  # unicode (default)
            self.chars = {
                "tl": "┌", "tm": "┬", "tr": "┐",
                "ml": "├", "mm": "┼", "mr": "┤",
                "bl": "└", "bm": "┴", "br": "┘",
                "v":  "│", "h":  "─"
            }

    def format(self, max_width=None):
        widths = self._natural_widths()

        if self.fixed_widths:
            widths = [
                max(self.min_col_width, fw) if isinstance(fw, int) else w
                for w, fw in zip(widths, self.fixed_widths)
            ]

        if max_width:
            widths = self._shrink_to_fit(widths, max_width)

        lines = []
        top = self._hline(self.chars["tl"], self.chars["tm"], self.chars["tr"], widths, self.chars["h"])
        mid = self._hline(self.chars["ml"], self.chars["mm"], self.chars["mr"], widths, self.chars["h"])
        bot = self._hline(self.chars["bl"], self.chars["bm"], self.chars["br"], widths, self.chars["h"])

        lines.append(top)
        lines.extend(self._render_row(self.headers, widths, header=True))
        lines.append(mid)
        for r in self.rows:
            lines.extend(self._render_row(r, widths))
        lines.append(bot)
        return "\n".join(lines)

    # ---- internal helpers ----
    def _natural_widths(self):
        n = len(self.headers)
        widths = [len(self.headers[i]) for i in range(n)]
        for row in self.rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], *(len(s) for s in cell.splitlines()))
        return widths

    def _table_width(self, col_widths):
        n = len(col_widths)
        return (n + 1) + sum(w + 2 * self.pad for w in col_widths)

    def _shrink_to_fit(self, widths, max_width):
        widths = widths[:]
        if self._table_width(widths) <= max_width:
            return widths
        while self._table_width(widths) > max_width:
            candidates = [i for i, w in enumerate(widths) if w > self.min_col_width]
            if not candidates:
                break
            i = max(candidates, key=lambda j: widths[j])
            widths[i] -= 1
        return widths

    def _repeat_to_len(self, pattern: str, length: int) -> str:
        """Repeat pattern to exact length (supports ' -' dashed patterns)."""
        if len(pattern) == 1:
            return pattern * length
        # multi-char pattern (e.g., '- ')
        need = (length // len(pattern)) + 2
        s = (pattern * need)[:length]
        return s

    def _hline(self, left, mid, right, widths, horiz):
        segs = [self._repeat_to_len(horiz, (w + 2 * self.pad)) for w in widths]
        return left + mid.join(segs) + right

    def _is_numeric(self, s: str) -> bool:
        s = s.strip()
        if not s:
            return False
        return all(ch.isdigit() or ch in "+-., " for ch in s) and any(ch.isdigit() for ch in s)

    def _wrap_cell(self, text, width):
        from textwrap import wrap
        width = max(1, width)
        lines = []
        for block in text.splitlines() or [""]:
            wrapped = wrap(block, width=width, replace_whitespace=False, drop_whitespace=False,
                           break_long_words=True, break_on_hyphens=True)
            lines.extend(wrapped or [""])
        return lines or [""]

    def _render_row(self, cells, widths, header=False):
        wrapped_cols = [self._wrap_cell(cells[i], widths[i]) for i in range(len(widths))]
        height = max(len(col) for col in wrapped_cols)

        lines = []
        for row_line in range(height):
            parts = []
            for i, col in enumerate(wrapped_cols):
                segment = col[row_line] if row_line < len(col) else ""
                if header:
                    segment = segment.center(widths[i])
                elif self._is_numeric(cells[i]):
                    segment = segment.rjust(widths[i])
                else:
                    segment = segment.ljust(widths[i])
                parts.append(" " * self.pad + segment + " " * self.pad)
            lines.append(self.chars["v"] + self.chars["v"].join(parts) + self.chars["v"])
        return lines
    
# ---------- Helpers ----------
def escape_md_v2(text: str) -> str:
    escape_chars = r"_*[]()~>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, "\\" + ch)
    return text

def _fmt_number(x, default= 0):
    # Safe, compact formatting for ints/floats/strings
    try:
        if isinstance(x, str) and x.strip() == "":
            return ""
        n = float(x)
        if n.is_integer():
            return f"{int(n):,}"
        if default == 0:
            return f"{n:,.0f}"
        elif default == 2:
            return f"{n:,.2f}"
    except Exception:
        return str(x)
    
def fmt_pct(val, decimals=1) -> str:
    try:
        v = float(val) * 100.0
        return f"{v:.{decimals}f}%"
    except Exception:
        return str(val)
    
def split_table_text(text, max_length=4000):
    """Split table text into chunks that fit Telegram's message limit."""
    lines = text.split("\n")
    chunks, current, length = [], [], 0
    for line in lines:
        if length + len(line) + 1 > max_length and current:
            chunks.append("\n".join(current))
            current, length = [line], len(line) + 1
        else:
            current.append(line)
            length += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks

def split_table_text_customize(text: str, first_len: int = 1400, max_len: int = 4000):
    """
    Split table text into chunks that fit Telegram's message limit.
    - first_len: length limit for the first chunk
    - max_len: length limit for subsequent chunks
    """
    lines = text.split("\n")
    chunks, current, length = [], [], 0
    current_limit = first_len  # first chunk has special limit

    for line in lines:
        if length + len(line) + 1 > current_limit and current:
            chunks.append("\n".join(current))
            current, length = [line], len(line) + 1
            current_limit = max_len  # after the first chunk, switch to full limit
        else:
            current.append(line)
            length += len(line) + 1

    if current:
        chunks.append("\n".join(current))
    return chunks

# ---------- Rendering using TableFormatter ----------
# from prettytable import PrettyTable
from telegram.constants import ParseMode
from collections import defaultdict

# Inline-code helper: no newlines allowed inside
def inline_code_line(s: str) -> str:
    return f"`{s.replace('`','ˋ')}`"

# def inline_code_line_num(s: str) -> str:
#     """
#     Turn "2025-08-09 1,357" into "`2025`-`08`-`09` `1`,`357`"
#     """
#     if s is None:
#         return ""

#     out = []
#     buf = []

#     def flush_buf():
#         if buf:
#             token = "".join(buf).replace("`", "ˋ")
#             out.append(f"`{token}`")
#             buf.clear()

#     for ch in str(s):
#         if ch in ",":
#             flush_buf()
#             out.append(r"\,")  # separator itself, outside backticks
#         elif ch.isspace():
#             flush_buf()
#             out.append(" ")
#         else:
#             buf.append(ch)

#     flush_buf()
#     return "".join(out)

def count_separators(s: str) -> int:
    return s.count("-") + s.count(",")

def render_apf_table_v2(country, rows, max_width=72, brand=False):
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    flag = FLAGS.get(country, "")

    # --- group by brand ---
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    # widths computed from what you'll actually print
    dates_all = [str(r.get("date","")) for r in rows]
    nars_all  = [str(_fmt_number(r.get("NAR", 0))) for r in rows]
    ftds_all  = [str(_fmt_number(r.get("FTD", 0))) for r in rows]
    stds_all  = [str(_fmt_number(r.get("STD", 0))) for r in rows]
    ttds_all  = [str(_fmt_number(r.get("TTD", 0))) for r in rows]

    w0 = max(len("Date"), *(len(x) for x in dates_all)) if dates_all else len("Date")
    x0 = max(count_separators("Date"), *(count_separators(x) for x in dates_all)) if dates_all else count_separators("Date")

    w1 = max(len("NAR"), *(len(x) for x in nars_all)) if nars_all else len("NAR")
    x1 = max(count_separators("NAR"), *(count_separators(x) for x in nars_all)) if nars_all else count_separators("NAR")

    w2 = max(len("FTD"), *(len(x) for x in ftds_all)) if ftds_all else len("FTD")
    x2 = max(count_separators("FTD"), *(count_separators(x) for x in ftds_all)) if ftds_all else count_separators("FTD")

    w3 = max(len("STD"), *(len(x) for x in stds_all)) if stds_all else len("STD")
    x3 = max(count_separators("STD"), *(count_separators(x) for x in stds_all)) if stds_all else count_separators("STD")

    w4 = max(len("TTD"), *(len(x) for x in ttds_all)) if ttds_all else len("TTD")
    x4 = max(count_separators("TTD"), *(count_separators(x) for x in ttds_all)) if ttds_all else count_separators("TTD")

    list_seperators = [x0 + x1, x2, x3, x4, 0]
    print(list_seperators)

    def fmt_row(d, n, f, s, t):
        d = str(d)
        n = str(n)
        f = str(f)
        s = str(s)
        t = str(t)
        print(d, n, f, s, t)
        return " ".join([
            d.ljust(w0),
            n.rjust(w1),
            f.rjust(w2),
            s.rjust(w3),
            t.rjust(w4),
        ])

    header = fmt_row("Date", "NAR", "FTD", "STD", "TTD")
    sep = "-".join(["-" * w0, "-" * w1, "-" * w2, "-" * w3, "-" * w4])

    # --- build output ---
    current_time, date_range = get_date_range_header()

    if not brand:
        title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
        subtitle = "\n" + escape_md_v2(f"Acquisition Summary (up to {current_time} GMT+7)")
        title_line = title + subtitle
        parts = [title_line]

        # Show separator + header ONCE (above first brand)
        parts.append(inline_code_line(sep))
        parts.append(backtick_with_trailing_spaces(inline_code_line(header), list_seperators))
        parts.append(inline_code_line(sep))
    else:
        parts = []

    # Then each brand with only its rows
    first = True
    for brand_name, items in sorted(brand_groups.items()):
        if not first:
            parts.append("")  # blank line between brands
        first = False

        parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))

        for r in items:
            parts.append(
                wrap_separators(
                    inline_code_line(
                        fmt_row(
                            r.get("date", ""),
                            _fmt_number(r.get("NAR", 0)),
                            _fmt_number(r.get("FTD", 0)),
                            _fmt_number(r.get("STD", 0)),
                            _fmt_number(r.get("TTD", 0)),
                        )
                    )
                )
            )

    print(parts)
    return "\n".join(parts)
    
def render_apf_table(country, rows, max_width=72, brand=False):
    from collections import defaultdict
    def fmt_row_normal(d, a, t, w, z, widths, list_seps):
            w0, w1, w2, w3, w4 = widths
            x0, x1, x2, x3, x4 = list_seps
            # Use normal spaces between columns; inside cells use figure spaces for padding.
            return "  ".join([
                pad_with_figspace(d, w0, x0, "left"),
                pad_with_figspace(a, w1, x1, "right"),
                pad_with_figspace(t, w2, x2, "right"),
                pad_with_figspace(w, w3, x3, "right"),
                pad_with_figspace(z, w4, x4, "right")
            ])

    def fmt_row_header(d, a, t, w, z, widths, list_seps):
        w0, w1, w2, w3, w4 = widths
        x0, x1, x2, x3, x4 = list_seps
        # Use normal spaces between columns; inside cells use figure spaces for padding.
        return "  ".join([
            pad_with_figspace(f"`{d}`", w0, x0, "left"),
            pad_with_figspace(f"`{a}`", w1, x1, "right"),
            pad_with_figspace(f"`{t}`", w2, x2, "right"),
            pad_with_figspace(f"`{w}`", w3, x3, "right"),
            pad_with_figspace(f"`{z}`", w4, x4, "right"),
        ])

    FLAGS = {"TH": "🇹🇭", "PH": "🇵🇭", "BD": "🇧🇩", "PK": "🇵🇰", "ID": "🇮🇩"}
    flag = FLAGS.get(country, "")

    # --- group by brand ---
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    # helpers
    def _to_str_date(x): return str(x if x is not None else "")
    # def _to_str_num(x):  return str(_fmt_number(x if x is not None else 0))
    def _sum_ttd(items): return sum(_num_to_float(i.get("NAR", 0)) for i in items)

    # widths computed from what you'll actually print
    dates_all = [_to_str_date(r.get("date","")) for r in rows]
    nars_all  = [_fmt_commas0(r.get("NAR", 0))   for r in rows]
    ftds_all  = [_fmt_commas0(r.get("FTD", 0))   for r in rows]
    stds_all  = [_fmt_commas0(r.get("STD", 0))   for r in rows]
    ttds_all  = [_fmt_commas0(r.get("TTD", 0))   for r in rows]

    w0 = max(len("Date"), *(len(x) for x in dates_all)) if dates_all else len("Date")
    w1 = max(len("NAR"),  *(len(x) for x in nars_all))  if nars_all  else len("NAR")
    w2 = max(len("FTD"),  *(len(x) for x in ftds_all))  if ftds_all  else len("FTD")
    w3 = max(len("STD"),  *(len(x) for x in stds_all))  if stds_all  else len("STD")
    w4 = max(len("TTD"),  *(len(x) for x in ttds_all))  if ttds_all  else len("TTD")

    # for aligning thousands separators
    x0 = max(count_separators("Date"), *(count_separators(x) for x in dates_all)) if dates_all else count_separators("Date")
    x1 = max(count_separators("NAR"),  *(count_separators(x) for x in nars_all))  if nars_all  else count_separators("NAR")
    x2 = max(count_separators("FTD"),  *(count_separators(x) for x in ftds_all))  if ftds_all  else count_separators("FTD")
    x3 = max(count_separators("STD"),  *(count_separators(x) for x in stds_all))  if stds_all  else count_separators("STD")
    x4 = max(count_separators("TTD"),  *(count_separators(x) for x in ttds_all))  if ttds_all  else count_separators("TTD")

    num_seps = (x0, x1, x2, x3, x4)
    widths = (w0, w1, w2, w3, w4)
    print("widths:", widths, "num_seps:", num_seps)

    header = fmt_row_header("Date", "NAR", "FTD", "STD", "TTD", widths= widths, list_seps= num_seps)
    sep_line = "—" * 20   # same as in DPF

    # --- build output ---
    current_time, _ = get_date_range_header()
    if brand is False:
        title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
        subtitle = "\n" + escape_md_v2(f"Acquisition Summary (up to {current_time} GMT+7)")
        parts = [title + subtitle, "",header, sep_line]
    else:
        parts = []

    # Sort brands by TTD (DESC)
    brands_sorted = sorted(brand_groups.items(), key=lambda kv: _sum_ttd(kv[1]), reverse=True)

    first = True
    for brand_name, items in brands_sorted:
        if not first:
            parts.append("")  # blank line between brands
        first = False

        if brand is False:
            parts.append(f"*{stylize(str(brand_name), style= "sans_bold")}*")
        else:
            parts.append(stylize(str(brand_name), style="serif_bold"))

        # sort within brand by date DESC
        items_sorted = sorted(items, key=lambda r: str(r.get("date","")), reverse=True)

        for r in items_sorted:
            parts.append(fmt_row_normal(
                escape_md_v2(str(r.get("date", ""))),
                escape_md_v2(_fmt_commas0(r.get("NAR", 0))),
                escape_md_v2(_fmt_commas0(r.get("FTD", 0))),
                escape_md_v2(_fmt_commas0(r.get("STD", 0))),
                escape_md_v2(_fmt_commas0(r.get("TTD", 0)))
            , widths= widths, list_seps=num_seps))

    print(parts)
    return "\n".join(parts)


# ------- TESTING APF TABLE with GROUP and BRAND -------
from collections import defaultdict
from telegram.constants import ParseMode

def _aggregate_by_date_for_group(rows, group_label):
    """
    Collapse brand rows into a per-date total block so we can render the
    group summary as a single 'pseudo-brand'. (Layout only; keeps your format.)
    """
    by_date = {}
    for r in rows:
        d = r.get("date")
        if d not in by_date:
            by_date[d] = {"date": d, "brand": group_label, "country": r.get("country"),
                          "NAR": 0, "FTD": 0, "STD": 0, "TTD": 0}
        by_date[d]["NAR"] += int(r.get("NAR", 0) or 0)
        by_date[d]["FTD"] += int(r.get("FTD", 0) or 0)
        by_date[d]["STD"] += int(r.get("STD", 0) or 0)
        by_date[d]["TTD"] += int(r.get("TTD", 0) or 0)
    # newest first
    return sorted(by_date.values(), key=lambda x: str(x["date"]), reverse=True)

def render_group_then_brands(country: str, group_name: str, group_rows: list[dict], max_width=72) -> str:
    """
    Layout only:
      1) Group summary (as one compact 'pseudo-brand' block)
      2) Separator line
      3) All brands of this group (your existing brand-grouped table)
    """
    # 1) GROUP summary as a pseudo-brand (so it prints as one block)
    group_label = f"{group_name.upper()}"
    group_summary_rows = _aggregate_by_date_for_group(group_rows, group_label)
    group_block = render_apf_table_v2(country, group_summary_rows, max_width=max_width)

    # 2) Separator
    sep_line = "—" * 10

    # 3) BRAND breakdown (your function already groups by brand inside)
    brands_block = render_apf_table_v2(country, group_rows, max_width=max_width, brand = True)

    return "\n".join([group_block,sep_line, brands_block])

def _aggregate_by_date_all(rows, brand_label="ALL GROUPS TOTAL"):
    """
    Collapse ALL rows (every group/brand) into per-date totals so it prints
    as a single pseudo-brand block.
    """
    by_date = {}
    for r in rows:
        d = r.get("date")
        if d not in by_date:
            by_date[d] = {
                "date": d, "brand": brand_label, "country": r.get("country"),
                "NAR": 0, "FTD": 0, "STD": 0, "TTD": 0
            }
        by_date[d]["NAR"] += int(r.get("NAR", 0) or 0)
        by_date[d]["FTD"] += int(r.get("FTD", 0) or 0)
        by_date[d]["STD"] += int(r.get("STD", 0) or 0)
        by_date[d]["TTD"] += int(r.get("TTD", 0) or 0)
    # newest first
    return sorted(by_date.values(), key=lambda x: str(x["date"]), reverse=True)

def render_country_total(country: str, rows: list[dict], max_width=72) -> str:
    """
    One compact summary message per country: totals by date across ALL groups/brands.
    """
    total_rows = _aggregate_by_date_all(rows, brand_label="TOTAL")
    # header ON (brand=False default) so it has the country title + table header
    return render_apf_table_v2(country, total_rows, max_width=max_width)

# ---------- Summation helpers ----------
def _sum_field(rows, field="NAR"):
    s = 0
    for r in rows:
        v = r.get(field, 0)
        try:
            s += int(v)
        except Exception:
            s += int(float(v or 0))
    return s

# ---------- Telegram send ----------
async def send_apf_tables(update: Update, country_groups, max_width=72, max_length=4000):
    # country_groups: { "TH": rows_th, "PH": rows_ph, ... } where each row has keys: date, country, group, brand, NAR/FTD/STD/TTD
    for country, rows in sorted(
        ((c, r) for c, r in country_groups.items() if c is not None),
        key=lambda x: x[0]
    ):
        
   

        # split rows by GROUP within this country
        groups = defaultdict(list)
        for r in rows:
            g = r.get("group") or r.get("`group`") or "Unknown"
            groups[g].append(r)

        # order groups by total NAR DESC
        groups_sorted = sorted(groups.items(), key=lambda kv: _sum_field(kv[1], "NAR"), reverse=True)

        # one message per GROUP
        for gname, g_rows in groups_sorted:
            msg = render_group_then_brands(country, gname, g_rows, max_width=max_width)
            
            for chunk in split_table_text_customize(msg, first_len=max_length):
                # safe_chunk = escape_md_v2(chunk)
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=False
                )

        # --- country GRAND TOTAL by date (all groups/brands) ---
        total_msg = render_country_total(country, rows, max_width=max_width)
        for chunk in split_table_text_customize(total_msg, first_len=max_length):
            # safe_chunk = escape_md_v2(chunk)
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )

# # ---------- Telegram send ----------
# async def send_apf_tables(update: Update, country_groups, max_width=72, max_length=4000):
#     for country, rows in sorted(
#         ((c, r) for c, r in country_groups.items() if c is not None),
#         key=lambda x: x[0]
#     ):
#         table_text = render_apf_table(country, rows, max_width=max_width)
#         chunks = split_table_text_customize(table_text, first_len=max_length)

#         for chunk in chunks:
#             await update.message.reply_text(
#                 chunk,
#                 parse_mode=ParseMode.MARKDOWN_V   ,
#                 disable_web_page_preview=True
#             )

# ---------- Channel distribution rendering ----------
def _to_percent_number(val) -> float:
    """
    Convert val to a percent *number* (e.g., 171.8 for 171.8%).
    - Accepts "171.8%", "171.8", "0.718", 0.718, etc.
    - If input has '%', treat as already percent.
    - Else: if <= 1.5 (heuristic), treat as fraction and x100; otherwise already percent.
    """
    if val is None:
        return 0.0
    s = str(val).strip()
    had_pct = ("%" in s) or ("％" in s)
    s = s.replace("%", "").replace("％", "").replace(",", "")  # remove symbols
    try:
        x = float(s)
    except Exception:
        return 0.0
    if had_pct:
        return x
    # Heuristic: values like 0.12 → 12%; values like 171.8 → already percent
    return x * 100.0 if x <= 1.5 else x

from textwrap import wrap

def _to_percent_number(val) -> float:
    if val is None:
        return 0.0
    s = str(val).strip()
    had_pct = ("%" in s) or ("％" in s)
    s = s.replace("%", "").replace("％", "").replace(",", "")
    try:
        x = float(s)
    except Exception:
        return 0.0
    return x if had_pct else (x * 100.0 if x <= 1.5 else x)

def render_channel_distribution_v1(country: str, rows: list[dict], topn: int = 5) -> str:
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}
    flag = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    def escape_md_v2(text: str) -> str:
        for ch in r"_*[]()~`>#+-=|{}.!":
            text = text.replace(ch, "\\"+ch)
        return text

    raw_title = f"COUNTRY: {country} {flag} - ({currency})"
    title = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

    # --- Prepare strings ---
    channels = [str(r.get("method","")).replace("-", ".")
                .replace(".bd","").replace(".id","").replace(".pk","")
                .replace("native","nat").replace("bank.transfer","bank")
                .replace(".ph.nat","").replace("qr.code","qr").replace("direct","dir").replace("pay","p")
                # .replace(".", "")  # keep your normalization
                for r in rows]
    counts  = [str(_fmt_number(r.get("deposit_tnx_count"))).replace(",","") for r in rows]
    vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
    avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))).replace(",","") for r in rows]
    ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native',0)):.0f}" for r in rows]

    # --- Wrap the first column instead of cutting ---
    MAX_CHANNEL = 11  # width before wrapping to next line(s)
    chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels]

    # --- Column widths ---
    w0 = max(len("Channel"), MAX_CHANNEL)
    w1 = max(len("Cnt"), *(len(x) for x in counts))
    w2 = max(len("Vol"), *(len(x) for x in vols))
    w3 = max(len("Avg"), *(len(x) for x in avgs))
    w4 = max(len("%"),   *(len(x) for x in ratios))

    header = " ".join([
        "Channel".ljust(w0),
        "Cnt".rjust(w1),
        "Vol".rjust(w2),
        "Avg".rjust(w3),
        "%".rjust(w4),
    ])
    sep = "-" * len(header)

    # Build plain lines
    lines = [sep, header, sep]
    for i in range(len(rows)):
        # first visual line: channel + metrics
        lines.append(" ".join([
            chan_wrapped[i][0].ljust(w0),
            counts[i].rjust(w1),
            vols[i].rjust(w2),
            avgs[i].rjust(w3),
            ratios[i].rjust(w4),
        ]))
        # continuation lines: channel only
        blanks = [" " * w1, " " * w2, " " * w3, " " * w4]
        for frag in chan_wrapped[i][1:]:
            lines.append(" ".join([frag.ljust(w0), *blanks]))
    # 🔹 Inline-code each line (no triple ``` block)
    # Inside inline code, only the backtick is special — make it safe:
    def inline_code_line(s: str) -> str:
        return f"`{s.replace('`','ˋ')}`"

    code_lines = [inline_code_line(l) for l in lines]

    return "\n".join([title, *code_lines])

from textwrap import wrap

def render_channel_distribution_v100(country: str, rows: list[dict], topn: int = 5) -> str:
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}
    flag = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    def escape_md_v2(text: str) -> str:
        for ch in r"_*[]()~`>#+-=|{}.!":
            text = text.replace(ch, "\\"+ch)
        return text

    raw_title = f"COUNTRY: {country} {flag} - ({currency})"
    title = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

    # --- Prepare strings ---
    channels = [str(r.get("method","")).replace("-", ".")
                .replace(".bd","").replace(".id","").replace(".pk","")
                .replace("native","nat").replace("bank.transfer","bank")
                .replace(".ph","").replace("qr.code","qr").replace("direct","dir")
                for r in rows]
    counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
    vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
    avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
    ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native',0)):.0f}" for r in rows]

    # --- Wrap channel names (for mapping table) ---
    MAX_CHANNEL = 25
    chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels]

    # --- Column widths for Table A (metrics) ---
    w_idx = max(len("#"), len(str(len(rows))))
    w_cnt = max(len("Cnt"), *(len(x) for x in counts or ["0"]))
    w_vol = max(len("Vol"), *(len(x) for x in vols   or ["0"]))
    w_avg = max(len("Avg"), *(len(x) for x in avgs   or ["0"]))
    w_pct = max(len("%"),   *(len(x) for x in ratios or ["0"]))

    headerA = " ".join([
        "#".rjust(w_idx),
        "Cnt".rjust(w_cnt),
        "Vol".rjust(w_vol),
        "Avg".rjust(w_avg),
        "%".rjust(w_pct),
    ])
    sepA = "-" * len(headerA)

    # --- Build Table A: one line per row ---
    linesA = [sepA, headerA, sepA]
    for i in range(len(rows)):
        linesA.append(" ".join([
            str(i+1).rjust(w_idx),
            counts[i].rjust(w_cnt),
            vols[i].rjust(w_vol),
            avgs[i].rjust(w_avg),
            ratios[i].rjust(w_pct),
        ]))

    # --- Build Table B: index → channel mapping ---
    headerB = f"{'#'.rjust(w_idx)}  Channel"
    sepB = "-" * max(len(headerB), w_idx + 2 + MAX_CHANNEL)

    linesB = [sepB, headerB, sepB]
    for i, frags in enumerate(chan_wrapped, start=1):
        linesB.append(f"{str(i).rjust(w_idx)}  {frags[0]}")
        for frag in frags[1:]:
            linesB.append(f"{' ' * w_idx}  {frag}")

    # --- Inline-code each line so Telegram preserves spacing ---
    def inline_code_line(s: str) -> str:
        return f"`{s.replace('`','ˋ')}`"

    codeA = [inline_code_line(l) for l in linesA]
    codeB = [inline_code_line(l) for l in linesB]

    # Final output
    return "\n".join([title, *codeA, "", *codeB])

# def render_channel_distribution_v2(country: str, rows: list[dict], topn: int = 5) -> str:
#     from textwrap import wrap

#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}
#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     def escape_md_v2(text: str) -> str:
#         for ch in r"_*[]()~`>#+-=|{}.!":
#             text = text.replace(ch, "\\"+ch)
#         return text

#     # --- Title (same style as your existing function) ---
#     raw_title = f"COUNTRY: {country} {flag} - ({currency})"
#     title = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

#     # --- Prepare/normalize strings ---
#     channels = [
#         str(r.get("method","")).replace("-", ".")
#                                .replace(".bd","").replace(".id","").replace(".pk","").replace(".ph","")
#                                .replace("native","nat").replace("bank.transfer","bank")
#                                .replace("qr.code","qr").replace("direct","dir")
#         for r in rows
#     ]
#     counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
#     vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
#     avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
#     ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native', 0)):.0f}" for r in rows]

#     # apply topn to both tables
#     n = min(topn if isinstance(topn, int) and topn > 0 else len(rows), len(rows))
#     channels_disp = channels[:n]
#     counts_disp   = counts[:n]
#     vols_disp     = vols[:n]
#     avgs_disp     = avgs[:n]
#     ratios_disp   = ratios[:n]

#     # ---------- TABLE A (metrics) ----------
#     # widths from rendered strings we will print
#     w_idx = max(len("#"), len(str(n)))
#     w_cnt = max(len("Cnt"), *(len(x) for x in (counts_disp or ["0"])))
#     w_vol = max(len("Vol"), *(len(x) for x in (vols_disp   or ["0"])))
#     w_avg = max(len("Avg"), *(len(x) for x in (avgs_disp   or ["0"])))
#     w_pct = max(len("%"),   *(len(x) for x in (ratios_disp or ["0"])))

#     # thousands-separator counts for in-cell figspace padding
#     x_idx = max(count_separators("#"), *(count_separators(str(i+1)) for i in range(n))) if n else count_separators("#")
#     x_cnt = max(count_separators("Cnt"), *(count_separators(x) for x in counts_disp))   if n else count_separators("Cnt")
#     x_vol = max(count_separators("Vol"), *(count_separators(x) for x in vols_disp))     if n else count_separators("Vol")
#     x_avg = max(count_separators("Avg"), *(count_separators(x) for x in avgs_disp))     if n else count_separators("Avg")
#     x_pct = max(count_separators("%"),   *(count_separators(x) for x in ratios_disp))   if n else count_separators("%")

#     widths_A = (w_idx, w_cnt, w_vol, w_avg, w_pct)
#     seps_A   = (x_idx, x_cnt, x_vol, x_avg, x_pct)
#     sep_line = "—" * 20

#     def fmt_row_A(i_str, cnt, vol, avg, pct, widths, seps):
#         wi, wc, wv, wa, wp = widths
#         xi, xc, xv, xa, xp = seps
#         return "  ".join([
#             inline_code_line(i_str, wi, xi, "right"),
#             inline_code_line(cnt,   wc, xc, "right"),
#             inline_code_line(vol,   wv, xv, "right"),
#             inline_code_line(avg,   wa, xa, "right"),
#             inline_code_line(pct,   wp, xp, "right"),
#         ])

#     def fmt_header_A(widths, seps):
#         return fmt_row_A("#", "Cnt", "Vol", "Avg", "%", widths, seps)

#     headerA = fmt_header_A(widths_A, seps_A)

#     linesA = [headerA, sep_line]
#     for i in range(n):
#         linesA.append(fmt_row_A(
#             escape_md_v2(str(i+1)),
#             escape_md_v2(counts_disp[i]),
#             escape_md_v2(vols_disp[i]),
#             escape_md_v2(avgs_disp[i]),
#             escape_md_v2(ratios_disp[i]),
#             widths_A, seps_A
#         ))

#     # ---------- TABLE B (# → Channel mapping) ----------
#     MAX_CHANNEL = 25
#     chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels_disp]

#     def fmt_row_B_first(i_str, ch_first, w_idx, x_idx):
#         return "  ".join([
#             pad_with_figspace(i_str, w_idx, x_idx, "right"),
#             escape_md_v2(ch_first),
#         ])

#     def fmt_row_B_cont(w_idx):
#         return " " * w_idx + "  "  # indent under the Channel column

#     headerB = "  ".join([
#         pad_with_figspace("#", w_idx, x_idx, "right"),
#         "Channel"
#     ])

#     linesB = [headerB, sep_line]
#     for i, frags in enumerate(chan_wrapped, start=1):
#         if not frags:
#             frags = [""]
#         linesB.append(fmt_row_B_first(escape_md_v2(str(i)), frags[0], w_idx, x_idx))
#         prefix = fmt_row_B_cont(w_idx)
#         for frag in frags[1:]:
#             linesB.append(prefix + escape_md_v2(frag))

#     # Final output (normal text, no inline-code lines)
#     return "\n".join([title, "", *linesA, "", *linesB])

# def render_channel_distribution_v3(country: str, rows: list[dict], topn: int = 5) -> str:
#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}
#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     def escape_md_v2(text: str) -> str:
#         for ch in r"_*[]()~`>#+-=|{}.!":
#             text = text.replace(ch, "\\"+ch)
#         return text

#     raw_title = f"COUNTRY: {country} {flag} - ({currency})"
#     title = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

#     # --- Prepare strings ---
#     channels = [str(r.get("method","")).replace("-", ".")
#                 .replace(".bd","").replace(".id","").replace(".pk","")
#                 .replace("bank.transfer","bank")
#                 .replace(".ph.nat","").replace("qr.code","qr").replace("direct","dir")
#                 for r in rows]
#     counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
#     vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
#     avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
#     ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native',0)):.0f}" for r in rows]

#     # --- Wrap channel names if too long ---
#     MAX_CHANNEL = 20
#     chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels]

#     # --- Column widths ---
#     w1 = max(len("Cnt"), *(len(x) for x in counts))
#     w2 = max(len("Vol"), *(len(x) for x in vols))
#     w3 = max(len("Avg"), *(len(x) for x in avgs))
#     w4 = max(len("%"),   *(len(x) for x in ratios))

#     header = " ".join([
#         "Cnt".rjust(w1),
#         "Vol".rjust(w2),
#         "Avg".rjust(w3),
#         "%".rjust(w4),
#     ])
#     sep = "-" * len(header)

#     lines = [sep, header, sep]
#     for i in range(len(rows)):
#         # Channel line(s)
#         for frag in chan_wrapped[i]:
#             lines.append(frag)
#         # Numbers line
#         lines.append(" ".join([
#             counts[i].rjust(w1),
#             vols[i].rjust(w2),
#             avgs[i].rjust(w3),
#             ratios[i].rjust(w4),
#         ]))

#     # Inline-code each line so Telegram preserves spacing
#     def inline_code_line(s: str) -> str:
#         return f"`{s.replace('`','ˋ')}`"

#     code_lines = [inline_code_line(l) for l in lines]
#     return "\n".join([title, *code_lines])

# def render_channel_distribution_v0(country: str, rows: list[dict], topn: int = 5) -> str:

#     def pad_with_figspace_(s: str, width: int, num_seps: int, align: str = "left") -> str:
#         inline_count = len("" if s is None else str(s).strip().replace("`","").replace(",","").replace("-",""))
#         sep_count = count_separators(s)

#         # how many figure spaces needed? => Max width trừ cho width of s

#         # num of figure spaces = pad - num_seps (if any)
#         num_inlines = max(0, width - num_seps - inline_count)
#         num_seps = max(0, num_seps - sep_count)
#         string_inlines = "" if num_inlines == 0 else f"`{num_inlines*' '}`"
        
#         convert_pads = string_inlines + num_seps*" "
        
#         print(f"Len: {len(s)}, Num inlines: {num_inlines}, Num seps: {num_seps}, String: '{s}' -> '{convert_pads + s if align=='right' else s + convert_pads}'")

#         return (convert_pads + s) if align == "right" else (s + convert_pads)

#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}
#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     # --- Title (same style as APF/DPF) ---
#     raw_title = f"COUNTRY: {country} {flag} - ({currency})"
#     title = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

#     # --- Prepare strings (compact channel names like before) ---
#     channels = [
#         str(r.get("method","")).replace("-bd","").replace("-id","").replace("-pk","")
#                                .replace("native","nat").replace("bank-transfer","bank")
#                                .replace("-ph","").replace("qr-code","qr").replace("direct","dir")
#         for r in rows
#     ]
#     counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
#     vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
#     avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
#     ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native',0)):.0f}" for r in rows]

#     # ---------- TABLE A (metrics) ----------
#     # Compute widths from what we'll actually print
#     w_idx = max(len("No"), len(str(len(rows))))
#     w_cnt = max(len("Count"), *(len(x) for x in counts or ["0"]))
#     w_vol = max(len("Volume"), *(len(x) for x in vols   or ["0"]))
#     w_avg = max(len("Avg"), *(len(x) for x in avgs   or ["0"]))
#     w_pct = max(len("%"),   *(len(x) for x in ratios or ["0"]))

#     # Max thousands-separator counts per column for figspace padding
#     x_idx = max(count_separators("No"), *(count_separators(str(i+1)) for i in range(len(rows)))) if rows else count_separators("No")
#     x_cnt = max(count_separators("Count"), *(count_separators(x) for x in counts or [])) if rows else count_separators("Cnt")
#     x_vol = max(count_separators("Volume"), *(count_separators(x) for x in vols   or [])) if rows else count_separators("Vol")
#     x_avg = max(count_separators("Avg"), *(count_separators(x) for x in avgs   or [])) if rows else count_separators("Avg")
#     x_pct = max(count_separators("%"),   *(count_separators(x) for x in ratios or [])) if rows else count_separators("%")

#     widths_A = (w_idx, w_cnt, w_vol, w_avg, w_pct)
#     seps_A   = (x_idx, x_cnt, x_vol, x_avg, x_pct)
#     print("Table A widths:", widths_A, "seps:", seps_A)

#     def fmt_row_A(i_str, cnt, vol, avg, pct, widths, seps):
#         wi, wc, wv, wa, wp = widths
#         xi, xc, xv, xa, xp = seps
#         # Use normal spaces between columns; inside cells use figure spaces.
#         return "  ".join([
#             pad_with_figspace_(i_str, wi, xi, "left"),
#             pad_with_figspace_(cnt,   wc, xc, "right"),
#             pad_with_figspace_(vol,   wv, xv, "right"),
#             pad_with_figspace_(avg,   wa, xa, "right"),
#             pad_with_figspace_(pct,   wp, xp, "right"),
#         ])

#     def fmt_header_A(widths, seps):
#         wi, wc, wv, wa, wp = widths
#         xi, xc, xv, xa, xp = seps
#         # Backticks around header labels (like APF), but NOT inline-code wrapping.
#         return "  ".join([
#             pad_with_figspace_("`No`",   wi, xi, "left"),
#             pad_with_figspace_("`Count`", wc, xc, "right"),
#             pad_with_figspace_("`Volume`", wv, xv, "right"),
#             pad_with_figspace_("`Avg`", wa, xa, "right"),
#             pad_with_figspace_("`%`",   wp, xp, "right"),
#         ])
    
#     headerA  = fmt_header_A(widths_A, seps_A)
#     sep_line = "—" * 20  # match APF/DPF vibe

#     linesA = [headerA, sep_line]
#     for i in range(len(rows)):
#         linesA.append(fmt_row_A(
#             escape_md_v2(str(i+1)),
#             escape_md_v2(counts[i]),
#             escape_md_v2(vols[i]),
#             escape_md_v2(avgs[i]),
#             escape_md_v2(ratios[i]),
#             widths_A, seps_A
#         ))

#     # ---------- TABLE B (index → channel mapping) ----------
#     MAX_CHANNEL = 25
#     # wrap channel into fragments for multi-line display
#     chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels]

#     # For Table B we only need the index width & sep count
#     widths_B = (w_idx,)
#     seps_B   = (x_idx,)
#     print("Table B widths:", widths_B, "seps:", seps_B)

#     def fmt_row_B_first(i_str, ch_first, widths, seps):
#         (wi,), (xi,) = widths, seps
#         return "    ".join([
#             pad_with_figspace(i_str, wi, xi, "left"),
#             escape_md_v2(ch_first),
#         ])

#     def fmt_row_B_cont(widths):
#         (wi,) = widths
#         return " " * (wi) + "  "  # indent continuation lines under the Channel column

#     headerB = "    ".join([
#         pad_with_figspace("`No`", w_idx, x_idx, "left"),
#         "`Channel`"
#     ])

#     linesB = [headerB, sep_line]
#     for i, frags in enumerate(chan_wrapped, start=1):
#         if not frags:
#             frags = [""]
#         # first line with index + first fragment
#         linesB.append(fmt_row_B_first(escape_md_v2(str(i)), frags[0], widths_B, seps_B))
#         # continuation lines aligned under Channel
#         cont_prefix = fmt_row_B_cont(widths_B)
#         for frag in frags[1:]:
#             linesB.append(cont_prefix + escape_md_v2(frag))

#     # Final output (normal text, no inline-code lines)
#     return "\n".join([title, "", *linesA, "", *linesB])

async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 35):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution_v100(country, rows)
        # fancy = stylize(text, style = "mono")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False)
        
async def send_channel_distribution_v2(update: Update, country_groups: dict[str, list[dict]], max_width: int = 35):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution_v3(country, rows)
        # fancy = stylize(text, style = "mono")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False)
# # Ultra-compact version for very small screens
# def render_channel_distribution_minimal(country: str, rows: list[dict], topn: int = 5) -> str:
#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     flag = FLAGS.get(country, "")
    
#     def escape_md_v2(text: str) -> str:
#         escape_chars = r"_*[]()~`>#+-=|{}.!"
#         for ch in escape_chars:
#             text = text.replace(ch, "\\"+ch)
#         return text
    
#     # ---- Title outside block ----
#     title_line = f"*{escape_md_v2(f'{country} {flag} - Top {topn}')}*"
    
#     # ---- Prepare rows (top N) ----
#     rows = rows[:topn]
    
#     lines = []
#     for i, row in enumerate(rows, 1):
#         method = str(row.get("method", ""))[:10]  # Very short method name
#         pct = str(_fmt_pct(row.get("pct_of_country_total_native", 0), deno=1))
#         vol = str(_fmt_number(row.get("total_deposit_amount_native")))
        
#         line = f"{i}. {method} - {pct} ({vol})"
#         lines.append(line)
    
#     code_block = "```\n" + "\n".join(lines) + "\n```"
#     return "\n".join([title_line, code_block])

# async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
#     for country, rows in sorted(country_groups.items()):
#         text = render_channel_distribution(country, rows)
#         await update.message.reply_text(
#             text,
#             parse_mode=ParseMode.MARKDOWN_V2,
#             disable_web_page_preview=True
#         )

# def render_dpf_table(country: str, rows: list[dict], max_width: int = 72) -> str:
#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH": "PHP", "TH": "THB", "BD": "BDT", "PK": "PKR", "ID": "IDR"}

#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     def escape_md_v2(text: str) -> str:
#         escape_chars = r"_*[]()~`>#+-=|{}.!"
#         for ch in escape_chars:
#             text = text.replace(ch, "\\" + ch)
#         return text

#     # Title + column description (outside code block)
#     title_line   = f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*"
#     columns_line = escape_md_v2(f"Date | Avg Deposit ({currency}) | Total Deposit ({currency}) | Weightage")

#     # Build row strings
#     dates   = [str(r.get("date", "")) for r in rows]
#     avgs    = [str(_fmt_number(r.get("AverageDeposit", 0))) for r in rows]
#     totals  = [str(_fmt_number(r.get("TotalDeposit", 0))) for r in rows]
#     weights = [str(_fmt_pct(r.get("Weightage", 0), deno = 1)) for r in rows]

#     w0 = max((len(x) for x in dates),   default=0)
#     w1 = max((len(x) for x in avgs),    default=0)
#     w2 = max((len(x) for x in totals),  default=0)
#     w3 = max((len(x) for x in weights), default=0)

#     lines = []
#     for i in range(len(rows)):
#         line = " | ".join([
#             dates[i].ljust(w0),
#             avgs[i].rjust(w1),
#             totals[i].rjust(w2),
#             weights[i].rjust(w3),
#         ])
#         lines.append(line)

#     code_block = "```\n" + "\n".join(lines) + "\n```"

#     return "\n".join([title_line, columns_line, "", code_block])

# def render_dpf_table(country: str, rows: list[dict], max_width: int = 72) -> str:
#     FIGURE_SPACE = "\u2007"  # digit-width space
#     THIN_SPACE   = "\u2009" # thin space (narrower than normal space)

#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH": "PHP", "TH": "THB", "BD": "BDT", "PK": "PKR", "ID": "IDR"}

#     def comma_thin_space(s: str) -> str:
#         # ",\u2009" = comma + thin space (1 char width visually)
#         return s.replace(",", ",\u2009")
    
#     def fmt_num_commaspace(x) -> str:
#         # format with thousands separators, then make them comma+thin-space
#         return comma_thin_space(_fmt_number(x))
    

#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     def escape_md_v2(text: str) -> str:
#         escape_chars = r"_*[]()~`>#+-=|{}.!"
#         for ch in escape_chars:
#             text = text.replace(ch, "\\" + ch)
#         return text

#     # Title + description (MarkdownV2-safe)
#     title_line = f"*{escape_md_v2(f'COUNTRY: {country} {flag} - ({currency})')}*"
#     title_line = stylize(title_line, style="sans_bold")  # your helper
#     desc_text  = f"Date Average Total Weightage"
#     description_line = f"_{escape_md_v2(desc_text)}_"

#     parts = [title_line + "\n" + description_line]

#     # Build PrettyTable with column separators only
#     table = PrettyTable()
#     table.header = False       # no header row
#     table.border = False       # remove outer border
#     table.hrules = 0           # no horizontal rules
#     table.vrules = 1           # keep vertical separators

#     # Optional: slightly tighter padding (looks better in proportional fonts)
#     table.left_padding_width  = 0
#     table.right_padding_width = 1

#     for r in rows:
#         table.add_row([
#             str(r.get("date", "")),
#             str(fmt_num_commaspace(r.get("AverageDeposit", 0))),
#             str(fmt_num_commaspace(r.get("TotalDeposit", 0))),
#             str(_fmt_pct(r.get("Weightage", 0), deno=1)),
#         ])

#     table_text = escape_md_v2(str(table))
#     seperate = "———————————————"  # 15 em-dashes
#     parts.append(f"{seperate}\n{table_text}")

#     return "\n".join(parts)

# Constants
FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}

FIGURE_SPACE = "\u2007"  # digit-width space

def fmt_num_commas(x) -> str:
    # Use your own _fmt_number (adds commas), but no thin spaces
    return _fmt_number(x)

def fmt_pct(val, decimals=1) -> str:
    try:
        v = float(val) * 100.0
        return f"{v:.{decimals}f}%"
    except Exception:
        return str(val)



def right_pad_figspace(s: str, width: int) -> str:
    # Left-pad with FIGURE_SPACE so numbers right-align visually
    n = len(s)
    return (FIGURE_SPACE * max(0, width - n)) + s

from collections import defaultdict

# ------- small helpers -------
def _num_to_float(x):
    if x is None: return 0.0
    s = str(x).replace(",", "").replace(" ", "")
    try:
        return float(s)
    except Exception:
        return 0.0

def _shrink_date(d):
    # match APF visual: "2025-09-12" -> "25 0912" style; you used replace("202","2")
    # keep exactly your rule:
    return str(d)

def _fmt_commas0(x):
    try:
        return f"{_num_to_float(x):,.0f}"
    except Exception:
        return str(x)

def _fmt_pct_int(x):
    if x is None: return "0"
    try:
        return f"{_num_to_float(x)*100:.0f}"
    except Exception:
        return "0"

def inline_code_line(s: str) -> str:
    return f"`{str(s).replace('`','ˋ')}`"

# ------- DPF core table: mirrors render_apf_table -------
def render_dpf_table_official(country, rows, max_width=72, brand=False):
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"TH":"THB","PH":"PHP","BD":"BDT","PK":"PKR","ID":"IDR"}
    flag     = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    # group rows by brand
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    # ensure Weightage per brand if missing: vs latest date in that brand
    prepped = []
    for b, items in brand_groups.items():
        # aggregate by date within brand (guard duplicates)
        by_date = {}
        for r in items:
            d = str(r.get("date", ""))
            by_date.setdefault(d, {"date": d, "brand": b, "AverageDeposit": [], "TotalDeposit": 0.0})
            by_date[d]["TotalDeposit"] += _num_to_float(r.get("TotalDeposit", 0))
            avgv = r.get("AverageDeposit", None)
            if avgv is not None:
                by_date[d]["AverageDeposit"].append(_num_to_float(avgv))
        # collapse & sort desc
        collapsed = []
        for d, obj in by_date.items():
            avg_val = (sum(obj["AverageDeposit"])/len(obj["AverageDeposit"])) if obj["AverageDeposit"] else None
            collapsed.append({"date": d, "brand": b, "AverageDeposit": avg_val, "TotalDeposit": obj["TotalDeposit"]})
        collapsed.sort(key=lambda x: x["date"], reverse=True)
        # compute weight vs latest
        latest_total = collapsed[0]["TotalDeposit"] if collapsed else 0.0
        for r in collapsed:
            r["Weightage"] = (r["TotalDeposit"]/latest_total) if latest_total else None
        prepped.extend(collapsed)

    # widths from the exact strings we will render
    def _row_strs(r):
        return (
            _shrink_date(r["date"]),
            _fmt_commas0(r["AverageDeposit"]) if r["AverageDeposit"] is not None else "-",
            _fmt_commas0(r["TotalDeposit"]),
            _fmt_pct_int(r["Weightage"])  # just the integer (no % sign) to match your APF style
        )

    dates_all, avgs_all, totals_all, w_all = [], [], [], []
    for r in prepped:
        d, a, t, w = _row_strs(r)
        dates_all.append(d); avgs_all.append(a); totals_all.append(t); w_all.append(w)

    w0 = max(len("Date"),  *(len(s) for s in dates_all)) if dates_all else len("Date")
    x0 = max(count_separators("Date"), *(count_separators(x) for x in dates_all))

    w1 = max(len("Avg"),   *(len(s) for s in avgs_all))  if avgs_all else len("Avg")
    x1 = max(count_separators("Avg"), *(count_separators(x) for x in avgs_all))

    w2 = max(len("Total"), *(len(s) for s in totals_all))if totals_all else len("Total")
    x2 = max(count_separators("Total"), *(count_separators(x) for x in totals_all))

    w3 = max(len("%"),     *(len(s) for s in w_all))     if w_all     else len("%")
    x3 = max(count_separators("%"), *(count_separators(x) for x in w_all))

    list_seperators = [x0+x1, x2 , x3 , 0]

    def fmt_row(d, a, t, w):
        return " ".join([
            d.ljust(w0),
            a.rjust(w1),
            t.rjust(w2),
            w.rjust(w3),
        ])
    
    if brand == False:
        header = fmt_row("Date", "Avg", "Total", "%")
        sep    = "-" * len(header)
        
    # --- build output like APF ---
    current_time, _ = get_date_range_header()

    if brand == 0:  # show big country header + table header once
        title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag} - ({currency})')}*", style="sans_bold")
        subtitle = "\n" + escape_md_v2(f"Deposit Performance (up to {current_time} GMT+7)")
        parts = [title + subtitle, 
                 inline_code_line(sep), 
                 backtick_with_trailing_spaces(inline_code_line(header), list_seperators), 
                 inline_code_line(sep)]
    else:
        parts = []

    # then each brand with only its rows (exactly like APF)
    first = True
    # sort brands by total NAR DESC
    brands_sorted = sorted(
        brand_groups.items(),
        key=lambda kv: _sum_field(kv[1], "NAR"),
        reverse=True
    )
    # brands_sorted = sorted({r["brand"] for r in prepped})
    print(prepped)
    for brand_name in brands_sorted:
        if not first:
            parts.append("")  # blank line between brands
        first = False

        parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))
        for r in filter(lambda x: x["brand"] == brand_name, prepped):
            d, a, t, w = _row_strs(r)
            parts.append(wrap_separators(inline_code_line(fmt_row(
            d.ljust(w0),
            a.rjust(w1),
            t.rjust(w2),
            w.rjust(w3)))))

    print(parts)
    return "\n".join(parts)

# # ------- DPF group -> brands (mirrors APF render_group_then_brands) -------
# def _aggregate_dpf_by_date(rows: list[dict], pseudo_brand: str):
#     """Per-date totals across given rows; averages averaged; % vs latest date."""
#     by_date = {}
#     for r in rows:
#         d = str(r.get("date", ""))
#         by_date.setdefault(d, {"date": d, "brand": pseudo_brand, "TotalDeposit": 0.0, "AvgList": []})
#         by_date[d]["TotalDeposit"] += _num_to_float(r.get("TotalDeposit", 0))
#         if r.get("AverageDeposit") is not None:
#             by_date[d]["AvgList"].append(_num_to_float(r["AverageDeposit"]))
#     collapsed = []
#     for d, obj in by_date.items():
#         avg_val = (sum(obj["AvgList"])/len(obj["AvgList"])) if obj["AvgList"] else None
#         collapsed.append({"date": d, "brand": pseudo_brand, "AverageDeposit": avg_val, "TotalDeposit": obj["TotalDeposit"]})
#     collapsed.sort(key=lambda x: x["date"], reverse=True)
#     # weight vs latest date in this block
#     latest_total = collapsed[0]["TotalDeposit"] if collapsed else 0.0
#     for r in collapsed:
#         r["Weightage"] = (r["TotalDeposit"]/latest_total) if latest_total else None
#     return collapsed

# def render_dpf_group_then_brands(country: str, group_name: str, group_rows: list[dict], max_width=72) -> str:
#     # 1) GROUP summary (pseudo-brand)
#     group_summary_rows = _aggregate_dpf_by_date(group_rows, pseudo_brand=group_name.upper())
#     group_block = render_dpf_table(country, group_summary_rows, max_width=max_width, brand=False)
#     # 2) Separator
#     sep_line = inline_code_line("=" * 29)
#     # 3) BRAND breakdown (no big header again)
#     brands_block = render_dpf_table(country, group_rows, max_width=max_width, brand=True)
#     return "\n".join([group_block, sep_line, "", brands_block])

# # ------- DPF country GRAND TOTAL (mirrors APF render_country_total) -------
# def render_dpf_country_total(country: str, rows: list[dict], max_width=72) -> str:
#     total_rows = _aggregate_dpf_by_date(rows, pseudo_brand="TOTAL")
#     return render_dpf_table(country, total_rows, max_width=max_width, brand=False)

# async def send_dpf_tables(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
#     for country, rows in sorted(country_groups.items()):
#         # split by group
#         groups = defaultdict(list)
#         for r in rows:
#             g = r.get("group") or r.get("`group`") or "Unknown"
#             groups[g].append(r)

#         # one message per group (group summary + brands)
#         for gname, g_rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
#             msg = render_dpf_group_then_brands(country, gname, g_rows, max_width=max_width)
#             for chunk in split_table_text_customize(msg, first_len=1000):
#                 await update.message.reply_text(
#                     chunk, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
#                 )

#         # final country GRAND TOTAL by date
#         total_msg = render_dpf_country_total(country, rows, max_width=max_width)
#         for chunk in split_table_text_customize(total_msg, first_len=4000):
#             await update.message.reply_text(
#                 chunk, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
#             )
# ------- helpers (no inline tick, figure spaces instead) -------

# ---------- helpers for figure-space layout (no inline ticks) ----------

FIG = "` `"  # figure space: same width as digits in proportional fonts

def pad_with_figspace(s: str, width: int, num_seps: int, align: str = "left") -> str:
    s_count = "" if s is None else str(s).strip().replace("`","")
    # how many figure spaces needed? => Max width trừ cho width of s
    pad = max(0, width - len(s_count))

    # num of figure spaces = pad - num_seps (if any)
    num_inlines = max(0, pad - num_seps)
    num_seps = 0 if pad == 0 else num_seps

    string_inlines = "" if num_inlines == 0 else f"{num_inlines*' '}"
    
    convert_pads = string_inlines + f"`{num_seps*" "}`"
    
    print(f"Len: {len(s)}, Num inlines: {num_inlines}, Num seps: {num_seps}, String: '{s}' -> '{convert_pads + s if align=='right' else s + convert_pads}'")

    return (convert_pads + s) if align == "right" else (s + convert_pads)



def _sum_field(rows, field="TotalDeposit"):
    s = 0.0
    for r in rows:
        v = r.get(field, 0)  # raw rows (group/brand split) contain TotalDeposit
        try:
            s += float(v or 0)
        except Exception:
            pass
    return s
import re

def escape_md_v2(text: str) -> str:
    if not text:
        return text
    # escape backslash first
    text = text.replace("\\", "\\\\")
    # escape the full Telegram set
    return re.sub(r"([_*[\]()~`>#+\-=\|{}\.!])", r"\\\1", text)

# def render_dpf_table_old(country, rows, max_width=72, brand=False):
#     def fmt_row_normal(d, a, t, w, widths, list_seps):
#         w0, w1, w2, w3 = widths
#         x0, x1, x2, x3 = list_seps
#         # Use normal spaces between columns; inside cells use figure spaces for padding.
#         return "  ".join([
#             pad_with_figspace(d, w0, x0, "left"),
#             pad_with_figspace(a, w1, x1, "right"),
#             pad_with_figspace(t, w2, x2, "right"),
#             pad_with_figspace(w, w3, x3, "right"),
#         ])

#     def fmt_row_header(d, a, t, w, widths, list_seps):
#         w0, w1, w2, w3 = widths
#         x0, x1, x2, x3 = list_seps
#         # Use normal spaces between columns; inside cells use figure spaces for padding.
#         return "  ".join([
#             pad_with_figspace(f"`{d}`", w0, x0, "left"),
#             pad_with_figspace(f"`{a}`", w1, x1, "right"),
#             pad_with_figspace(f"`{t}`", w2, x2, "right"),
#             pad_with_figspace(f"`{w}`", w3, x3, "right"),
#         ])

#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"TH":"THB","PH":"PHP","BD":"BDT","PK":"PKR","ID":"IDR"}
#     flag     = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     # group by brand
#     brand_groups = defaultdict(list)
#     for r in rows:
#         brand_groups[r.get("brand", "Unknown")].append(r)

#     # ensure Weightage
#     prepped = []
#     for b, items in brand_groups.items():
#         by_date = {}
#         for r in items:
#             d = str(r.get("date", ""))
#             by_date.setdefault(d, {"date": d, "brand": b, "AverageDeposit": [], "TotalDeposit": 0.0})
#             by_date[d]["TotalDeposit"] += _num_to_float(r.get("TotalDeposit", 0))
#             if r.get("AverageDeposit") is not None:
#                 by_date[d]["AverageDeposit"].append(_num_to_float(r["AverageDeposit"]))
#         collapsed = []
#         for d, obj in by_date.items():
#             avg_val = sum(obj["AverageDeposit"])/len(obj["AverageDeposit"]) if obj["AverageDeposit"] else None
#             collapsed.append({"date": d, "brand": b, "AverageDeposit": avg_val, "TotalDeposit": obj["TotalDeposit"]})
#         collapsed.sort(key=lambda x: x["date"], reverse=True)
#         latest_total = collapsed[0]["TotalDeposit"] if collapsed else 0.0
#         for rr in collapsed:
#             rr["Weightage"] = (rr["TotalDeposit"]/latest_total) if latest_total else None
#         prepped.extend(collapsed)

#     # prepare strings
#     def _row_strs(r):
#         return (
#             _shrink_date(r["date"]),
#             _fmt_commas0(r["AverageDeposit"]) if r["AverageDeposit"] is not None else "-",
#             _fmt_commas0(r["TotalDeposit"]),
#             _fmt_pct_int(r["Weightage"])
#         )

#     dates_all, avgs_all, totals_all, w_all = [], [], [], []
#     for r in prepped:
#         d, a, t, w = _row_strs(r)
#         dates_all.append(d); avgs_all.append(a); totals_all.append(t); w_all.append(w)

#     w0 = max(len("Date"),  *(len(s) for s in dates_all)) if dates_all else len("Date")
#     w1 = max(len("Avg"),   *(len(s) for s in avgs_all))  if avgs_all else len("Avg")
#     w2 = max(len("Total"), *(len(s) for s in totals_all))if totals_all else len("Total")
#     w3 = max(len("%"),     *(len(s) for s in w_all))     if w_all     else len("%")

#     x0 = max(count_separators("Date"), *(count_separators(x) for x in dates_all))
#     x1 = max(count_separators("Avg"), *(count_separators(x) for x in avgs_all))
#     x2 = max(count_separators("Total"), *(count_separators(x) for x in totals_all))
#     x3 = max(count_separators("%"), *(count_separators(x) for x in w_all))

#     widths = (w0, w1, w2, w3)
#     num_seps = (x0, x1, x2, x3)
#     print("max widths:", widths, "max num_seps:", num_seps)

#     current_time, _ = get_date_range_header() 
#     title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag} ({currency})')}*", style="sans_bold")
#     subtitle = "\n" + escape_md_v2(f"Deposit Performance (up to {str(current_time)} GMT+7)")
#     print("Subtitle:", subtitle)
#     print("Title:", title)

#     sep_line = "—" * 20
#     if brand == False:
#         # --- build output like APF --
#         header = fmt_row_header("Date", "Avg", "Total", "%", widths, num_seps)
#         parts = [title + subtitle, "", header, sep_line]
#     else:
#         parts = []

#     # sort brands by TotalDeposit DESC
#     brands_sorted = sorted(
#         brand_groups.items(),
#         key=lambda kv: _sum_field(kv[1], "TotalDeposit"),
#         reverse=True
#     )
        
#     first = True
#     for brand_name, _ in brands_sorted:
#         if not first:
#             parts.append("")  # blank line between brands

#         first = False
#         if brand == False:
#             parts.append(f"*{stylize(str(brand_name), style= "sans_bold")}*")  # plain brand label
#         else:
#             parts.append(f"{stylize(str(brand_name), style= "serif_bold")}")
#         for r in filter(lambda x: x["brand"] == brand_name, prepped):
#             d, a, t, w = _row_strs(r)
#             parts.append(fmt_row_normal(escape_md_v2(d), escape_md_v2(a), escape_md_v2(t), escape_md_v2(w), widths, num_seps))
#     print(parts)
#     return "\n".join(parts)

# def render_dpf_table_v3(country, rows, max_width=72, brand=False):
#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     flag = FLAGS.get(country, "")

#     # --- group by brand ---
#     brand_groups = defaultdict(list)
#     for r in rows:
#         brand_groups[r.get("brand", "Unknown")].append(r)

#     # widths computed from what you'll actually print
#     dates_all = [str(r.get("date","")) for r in rows]
#     nars_all  = [str(_fmt_number(r.get("NAR", 0))) for r in rows]
#     ftds_all  = [str(_fmt_number(r.get("FTD", 0))) for r in rows]
#     stds_all  = [str(_fmt_number(r.get("STD", 0))) for r in rows]
#     ttds_all  = [str(_fmt_number(r.get("TTD", 0))) for r in rows]

#     w0 = max(len("Date"), *(len(x) for x in dates_all)) if dates_all else len("Date")
#     x0 = max(count_separators("Date"), *(count_separators(x) for x in dates_all)) if dates_all else count_separators("Date")

#     w1 = max(len("NAR"), *(len(x) for x in nars_all)) if nars_all else len("NAR")
#     x1 = max(count_separators("NAR"), *(count_separators(x) for x in nars_all)) if nars_all else count_separators("NAR")

#     w2 = max(len("FTD"), *(len(x) for x in ftds_all)) if ftds_all else len("FTD")
#     x2 = max(count_separators("FTD"), *(count_separators(x) for x in ftds_all)) if ftds_all else count_separators("FTD")

#     w3 = max(len("STD"), *(len(x) for x in stds_all)) if stds_all else len("STD")
#     x3 = max(count_separators("STD"), *(count_separators(x) for x in stds_all)) if stds_all else count_separators("STD")

#     w4 = max(len("TTD"), *(len(x) for x in ttds_all)) if ttds_all else len("TTD")
#     x4 = max(count_separators("TTD"), *(count_separators(x) for x in ttds_all)) if ttds_all else count_separators("TTD")

#     list_seperators = [x0 + x1, x2, x3, x4, 0]
#     print(list_seperators)

#     def fmt_row(d, n, f, s, t):
#         d = str(d)
#         n = str(n)
#         f = str(f)
#         s = str(s)
#         t = str(t)
#         print(d, n, f, s, t)
#         return " ".join([
#             d.ljust(w0),
#             n.rjust(w1),
#             f.rjust(w2),
#             s.rjust(w3),
#             t.rjust(w4),
#         ])

#     header = fmt_row("Date", "NAR", "FTD", "STD", "TTD")
#     sep = "-".join(["-" * w0, "-" * w1, "-" * w2, "-" * w3, "-" * w4])

#     # --- build output ---
#     current_time, date_range = get_date_range_header()

#     if not brand:
#         title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
#         subtitle = "\n" + escape_md_v2(f"Acquisition Summary (up to {current_time} GMT+7)")
#         title_line = title + subtitle
#         parts = [title_line]

#         # Show separator + header ONCE (above first brand)
#         parts.append(inline_code_line(sep))
#         parts.append(backtick_with_trailing_spaces(inline_code_line(header), list_seperators))
#         parts.append(inline_code_line(sep))
#     else:
#         parts = []

#     # Then each brand with only its rows
#     first = True
#     for brand_name, items in sorted(brand_groups.items()):
#         if not first:
#             parts.append("")  # blank line between brands
#         first = False

#         parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))

#         for r in items:
#             parts.append(
#                 wrap_separators(
#                     inline_code_line(
#                         fmt_row(
#                             r.get("date", ""),
#                             _fmt_number(r.get("NAR", 0)),
#                             _fmt_number(r.get("FTD", 0)),
#                             _fmt_number(r.get("STD", 0)),
#                             _fmt_number(r.get("TTD", 0)),
#                         )
#                     )
#                 )
#             )

#     print(parts)
#     return "\n".join(parts)

def render_dpf_table_v2(country, rows, max_width=72, brand=False):
    # --- helpers used here are assumed to exist in your env:
    # escape_md_v2, stylize, inline_code_line, wrap_separators, backtick_with_trailing_spaces
    # _num_to_float, _fmt_commas0, _fmt_pct_int, _shrink_date, _sum_field,
    # count_separators, get_date_range_header

    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"TH":"THB","PH":"PHP","BD":"BDT","PK":"PKR","ID":"IDR"}
    flag     = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    # group by brand
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    # collapse rows by date within each brand; compute Weightage vs latest day per brand
    prepped = []
    for b, items in brand_groups.items():
        by_date = {}
        for r in items:
            d = str(r.get("date", ""))
            obj = by_date.setdefault(d, {"date": d, "brand": b, "AverageDeposit": [], "TotalDeposit": 0.0})
            obj["TotalDeposit"] += _num_to_float(r.get("TotalDeposit", 0))
            if r.get("AverageDeposit") is not None:
                obj["AverageDeposit"].append(_num_to_float(r["AverageDeposit"]))

        collapsed = []
        for d, obj in by_date.items():
            avg_val = sum(obj["AverageDeposit"])/len(obj["AverageDeposit"]) if obj["AverageDeposit"] else None
            collapsed.append({
                "date": d,
                "brand": b,
                "AverageDeposit": avg_val,
                "TotalDeposit": obj["TotalDeposit"]
            })
        collapsed.sort(key=lambda x: x["date"], reverse=True)
        latest_total = collapsed[0]["TotalDeposit"] if collapsed else 0.0
        for rr in collapsed:
            rr["Weightage"] = (rr["TotalDeposit"]/latest_total) if latest_total else None
        prepped.extend(collapsed)

    # string render per row (already formatted)
    def _row_strs(r):
        return (
            str(r["date"]).replace("/",""),
            _fmt_commas0(r["AverageDeposit"]) if r["AverageDeposit"] is not None else "-",
            _fmt_commas0(r["TotalDeposit"]),
            _fmt_pct_int(r["Weightage"])
        )

    # collect for width + separator counts
    dates_all, avgs_all, totals_all, w_all = [], [], [], []
    for r in prepped:
        d, a, t, w = _row_strs(r)
        dates_all.append(d); avgs_all.append(a); totals_all.append(t); w_all.append(w)

    w0 = max(len("Date"),  *(len(s) for s in dates_all)) if dates_all else len("Date")
    w1 = max(len("Avg"),   *(len(s) for s in avgs_all))  if avgs_all else len("Avg")
    w2 = max(len("Total"), *(len(s) for s in totals_all))if totals_all else len("Total")
    w3 = max(len("%"),     *(len(s) for s in w_all))     if w_all     else len("%")

    x0 = max(count_separators("Date"),  *(count_separators(x) for x in dates_all))  if dates_all  else count_separators("Date")
    x1 = max(count_separators("Avg"),   *(count_separators(x) for x in avgs_all))   if avgs_all   else count_separators("Avg")
    x2 = max(count_separators("Total"), *(count_separators(x) for x in totals_all)) if totals_all else count_separators("Total")
    x3 = max(count_separators("%"),     *(count_separators(x) for x in w_all))      if w_all      else count_separators("%")

    # widths = (w0, w1, w2, w3)
    # num_seps = (x0, x1, x2, x3)
    # for header trailing-space trick: merge first two cols’ separators like APF
    list_separators = [x0 + x1, x2, x3, 0]

    # plain-space aligned row (no figure spaces)
    def fmt_row(d, a, t, w):
        d = str(d); a = str(a); t = str(t); w = str(w)
        return " ".join([
            d.ljust(w0),
            a.rjust(w1),
            t.rjust(w2),
            w.rjust(w3),
        ])

    # header + horizontal sep built from real widths
    header = fmt_row("Date", "Avg", "Total", "%")
    sep    = "-".join(["-" * w0, "-" * w1, "-" * w2, "-" * w3])

    # --- build output (APF style) ---
    current_time, _ = get_date_range_header()
    title    = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag} ({currency})')}*", style="sans_bold")
    subtitle = "\n" + escape_md_v2(f"Deposit Performance (up to {current_time} GMT+7)")

    parts = []
    if not brand:
        parts.append(title + subtitle)
        parts.append(inline_code_line(sep))
        parts.append(backtick_with_trailing_spaces(inline_code_line(header), list_separators))
        parts.append(inline_code_line(sep))

    # sort brands by TotalDeposit DESC
    brands_sorted = sorted(
        brand_groups.items(),
        key=lambda kv: _sum_field(kv[1], "TotalDeposit"),
        reverse=True
    )

    first = True
    for brand_name, _ in brands_sorted:
        if not first:
            parts.append("")  # blank line between brands
        first = False


        parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))

        # rows for this brand (already collapsed in prepped)
        for r in filter(lambda x: x["brand"] == brand_name, prepped):
            d, a, t, w = _row_strs(r)
            line = fmt_row(d, escape_md_v2(a), escape_md_v2(t), escape_md_v2(w))

            print(line)
            parts.append(wrap_separators(inline_code_line(line)))

    print(parts)

    return "\n".join(parts)


# ------- aggregate by date (used for group summary / country total) -------
def _aggregate_dpf_by_date(rows: list[dict], pseudo_brand: str):
    """Per-date totals across given rows; averages averaged; % vs latest date."""
    by_date = {}
    for r in rows:
        d = str(r.get("date", ""))
        by_date.setdefault(d, {"date": d, "brand": pseudo_brand, "TotalDeposit": 0.0, "AvgList": []})
        by_date[d]["TotalDeposit"] += _num_to_float(r.get("TotalDeposit", 0))
        if r.get("AverageDeposit") is not None:
            by_date[d]["AvgList"].append(_num_to_float(r["AverageDeposit"]))
    collapsed = []
    for d, obj in by_date.items():
        avg_val = (sum(obj["AvgList"])/len(obj["AvgList"])) if obj["AvgList"] else None
        collapsed.append({"date": d, "brand": pseudo_brand, "AverageDeposit": avg_val, "TotalDeposit": obj["TotalDeposit"]})
    collapsed.sort(key=lambda x: x["date"], reverse=True)
    latest_total = collapsed[0]["TotalDeposit"] if collapsed else 0.0
    for rr in collapsed:
        rr["Weightage"] = (rr["TotalDeposit"]/latest_total) if latest_total else None
    return collapsed

# ------- DPF group -> brands (no inline tick; figure spaces) -------
def render_dpf_group_then_brands(country: str, group_name: str, group_rows: list[dict], max_width=72) -> str:
    # 1) GROUP summary (pseudo-brand)
    group_summary_rows = _aggregate_dpf_by_date(group_rows, pseudo_brand=group_name.upper())
    group_block = render_dpf_table_v2(country, group_summary_rows, max_width=max_width, brand=False)

    # 2) Separator (normal text)
    sep_line = "—" * 10

    # 3) BRAND breakdown (no big header again)
    brands_block = render_dpf_table_v2(country, group_rows, max_width=max_width, brand=True)
    return "\n".join([group_block, f"{sep_line}", "", brands_block])

# ------- DPF country GRAND TOTAL (no inline tick; figure spaces) -------
def render_dpf_country_total(country: str, rows: list[dict], max_width=72) -> str:
    total_rows = _aggregate_dpf_by_date(rows, pseudo_brand="TOTAL")
    return render_dpf_table_v2(country, total_rows, max_width=max_width, brand=False)

# ------- sender (sort groups by TotalDeposit desc) -------
async def send_dpf_tables(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    # def escape_md_v2(text: str) -> str:
    #     for ch in r"=-,+":
    #         text = text.replace(ch, "\\"+ch)
    #     return text
      
    for country, rows in sorted(country_groups.items()):
        # split by group
        groups = defaultdict(list)
        for r in rows:
            g = r.get("group") or "Unknown"
            groups[g].append(r)

        # order groups by summed TotalDeposit desc
        groups_sorted = sorted(groups.items(), key=lambda kv: _sum_field(kv[1], "TotalDeposit"), reverse=True)

        # one message per group (group summary + brands)
        for gname, g_rows in groups_sorted:
            msg = render_dpf_group_then_brands(country, gname, g_rows, max_width=max_width)
            for chunk in split_table_text_customize(msg, first_len=4000):
                await update.message.reply_text(
                chunk, 
                parse_mode=ParseMode.MARKDOWN_V2, 
                disable_web_page_preview=True
                )

        # final country GRAND TOTAL by date
        total_msg = render_dpf_country_total(country, rows, max_width=max_width)
        for chunk in split_table_text_customize(total_msg, first_len=4000):
            await update.message.reply_text(
            chunk, 
            parse_mode=ParseMode.MARKDOWN_V2, 
            disable_web_page_preview=True
            )


# %%%
def wrap_separators(s: str) -> str:
    """
    Replace '-' and ',' in the string with MarkdownV2-safe backtick-wrapped versions.
    
    Example:
      '2025-09-12  2,832,000  6 1 0'
    →  '2025`\\-`09`\\-`12 2`\\,`832`\\,`000 6 1 0'
    """
    if not s:
        return s
    i = 0
    result = []
    for ch in s:
        if ch == "-":
            result.append("`\\-`")
            i += 1
        elif ch == ",":
            result.append("`\\,`")
            i += 1
        else:
            result.append(ch)
    return "".join(result)

import re

def backtick_with_trailing_spaces(line: str, spaces: list[int]) -> str:
    """
    Example:
      line   = "`Date           NAR   FTD   STD   TTD`"  # 12 spaces after Date
      spaces = [2, 1, 0, 0, 0]
      Output: `Date␠␠`␠␠␠␠␠␠␠␠␠␠`NAR␠` `FTD   STD   TTD`
              ^^^^^ inside      ^^^^^^^^^^^ remaining original spaces (12-2 = 10)
    """
    # strip global wrapping backticks if present
    src = line.strip()
    if src.startswith("`") and src.endswith("`"):
        src = src[1:-1]

    # Split into alternating [word][ws][word][ws]... preserving whitespace
    tokens = re.findall(r'\S+|\s+', src)
    # Build (word, following_ws) pairs
    pairs = []
    i = 0
    while i < len(tokens):
        word = tokens[i]
        ws = tokens[i+1] if i+1 < len(tokens) and tokens[i+1].isspace() else ""
        pairs.append((word, ws))
        i += 2 if ws else 1

    words = [w for w, _ in pairs]
    if len(words) != len(spaces):
        raise ValueError(f"Expected {len(words)} space counts, got {len(spaces)}")

    # last index where we split explicitly
    last_nonzero = max((idx for idx, n in enumerate(spaces) if n > 0), default=-1)

    out = []
    for idx, ((word, ws), n) in enumerate(zip(pairs, spaces)):
        if idx <= last_nonzero:
            # take n spaces inside backticks, keep the rest outside
            take = min(int(n), len(ws))
            outside = ws[:take]
            inside = ws[take:]
            out.append(f"`{word}{inside}`{outside}")
        else:
            # collapse the remainder (this word + its original trailing ws + the rest) into one backticked block
            # reconstruct remainder exactly from the original tokens
            # find the token position of this word
            # rebuild the exact tail string
            # (simpler: join this word+ws, plus all following pairs)
            tail_parts = [word + ws]
            for w2, ws2 in pairs[idx+1:]:
                tail_parts.append(w2 + ws2)
            tail = "".join(tail_parts)
            out.append(f"`{tail}`")
            break
    total = "".join(out)
    time.sleep(0.5) # Pause for half a second
    # Join WITHOUT adding extra spaces (we already preserved originals)
    return total
# %%
