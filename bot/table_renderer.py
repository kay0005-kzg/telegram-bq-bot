from telegram import Update
from telegram.constants import ParseMode
# import html
from textwrap import wrap
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
    escape_chars = r"_*[]()~`>#+-=|{}.!"
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

# Inline-code helper: no newlines allowed inside
def inline_code_line(s: str) -> str:
    return f"`{s.replace('`','ˋ')}`"

def render_apf_table(country, rows, max_width=72):
    from collections import defaultdict

    def inline_code_line(s: str) -> str:
        # Inline code can't contain newlines; only backtick is special
        return f"`{s.replace('`','ˋ')}`"

    def esc(s: str) -> str:
        for ch in r"_*[]()~`>#+-=|{}.!":
            s = s.replace(ch, "\\" + ch)
        return s

    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    flag = FLAGS.get(country, "")

    # --- group by brand ---
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    # --- global widths so all brands align ---
    dates_all = [str(r.get("date", "")) for r in rows]
    nars_all  = [str(_fmt_number(r.get("NAR", 0))) for r in rows]
    ftds_all  = [str(_fmt_number(r.get("FTD", 0))) for r in rows]
    stds_all  = [str(_fmt_number(r.get("STD", 0))) for r in rows]
    ttds_all  = [str(_fmt_number(r.get("TTD", 0))) for r in rows]

    w0 = max(len("Date"), *(len(x) for x in dates_all))
    w1 = max(len("NAR"),  *(len(x) for x in nars_all))
    w2 = max(len("FTD"),  *(len(x) for x in ftds_all))
    w3 = max(len("STD"),  *(len(x) for x in stds_all))
    w4 = max(len("TTD"),  *(len(x) for x in ttds_all))

    def fmt_row(d, n, f, s, t):
        return " ".join([
            str(d).ljust(w0),
            str(n).rjust(w1),
            str(f).rjust(w2),
            str(s).rjust(w3),
            str(t).rjust(w4),
        ])

    header = fmt_row("Date", "NAR", "FTD", "STD", "TTD")
    sep = "-".join(["-"*w0, "-"*w1, "-"*w2, "-"*w3, "-"*w4])

    # --- build output ---
    title_line = stylize(f"*{esc(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
    parts = [title_line]

    # Show separator + header ONCE (above first brand)
    parts.append(inline_code_line(sep))
    parts.append(inline_code_line(header))
    parts.append(inline_code_line(sep))

    # Then each brand with only its rows
    for brand, items in sorted(brand_groups.items()):
        parts.append(stylize(esc(str(brand)), style="sans_bold"))
        for r in items:
            parts.append(inline_code_line(fmt_row(
                r.get("date", ""),
                _fmt_number(r.get("NAR", 0)),
                _fmt_number(r.get("FTD", 0)),
                _fmt_number(r.get("STD", 0)),
                _fmt_number(r.get("TTD", 0)),
            )))

    return "\n".join(parts)



# ---------- Telegram send ----------
async def send_apf_tables(update: Update, country_groups, max_width=72, max_length=4000):
    for country, rows in sorted(
        ((c, r) for c, r in country_groups.items() if c is not None),
        key=lambda x: x[0]
    ):
        table_text = render_apf_table(country, rows, max_width=max_width)
        chunks = split_table_text_customize(table_text, first_len=max_length)

        for chunk in chunks:
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )

# def render_channel_distribution(country: str, rows: list[dict], max_width: int = 72) -> str:
#     FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
#     CURRENCIES = {"PH": "PHP", "TH": "THB", "BD": "BDT", "PK": "PKR", "ID": "IDR"}

#     flag = FLAGS.get(country, "")
#     currency = CURRENCIES.get(country, "")

#     def escape_md_v2(text: str) -> str:
#         escape_chars = r"_*[]()~`>#+-=|{}.!"
#         for ch in escape_chars:
#             text = text.replace(ch, "\\" + ch)
#         return text

#     title_line   = f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*"
#     columns_line = escape_md_v2(f"Count | Volume ({currency}) | Avg ({currency}) | Ratio (%)")

#     methods = [str(r.get("method", "")).replace("native", "nat").replace("qr-code","qr").replace("direct", "dir").replace("bank-transfer", "bank").replace("-",".") for r in rows]
#     counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
#     volumes = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
#     avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
#     pcts    = [str(_fmt_pct(r.get("pct_of_country_total_native", 0), deno=2)) for r in rows]
    
#     w0 = max((len(x) for x in methods),  default=0)
#     w1 = max((len(x) for x in counts),  default=0)
#     w2 = max((len(x) for x in volumes), default=0)
#     w3 = max((len(x) for x in avgs),    default=0)
#     w4 = max((len(x) for x in pcts),    default=0)

#     # block_lines = []
#     # for i, r in enumerate(rows):
#     #     method = escape_md_v2(str(r.get("method", "")))
#     #     num_line = " | ".join([
#     #         counts[i].rjust(w1),
#     #         volumes[i].rjust(w2),
#     #         avgs[i].rjust(w3),
#     #         pcts[i].rjust(w4),
#     #     ])
#     #     # 👉 no extra blank line
#     #     block_lines.append(f"{method}\n {num_line}")

#     # code_block = "```\n" + "\n".join(block_lines) + "\n```"

#     # return "\n".join([title_line, columns_line, "", code_block])
    
#     block_lines = []
#     for i, r in enumerate(rows):
#         num_line = " ".join([methods[i].ljust(w0),
#             counts[i].rjust(w1),
#             volumes[i].rjust(w2),
#             avgs[i].rjust(w3),
#             pcts[i].rjust(w4),
#         ])

#         # 👉 no extra blank line
#         block_lines.append(f"{num_line}")

#     code_block = "```\n" + "\n".join(block_lines) + "\n```"

#     return "\n".join([title_line, columns_line, "", code_block])
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

def render_channel_distribution_v2(country: str, rows: list[dict], topn: int = 5) -> str:
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
                .replace(".ph.nat","").replace("qr.code","qr").replace("direct","dir")
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

    headerA = "  ".join([
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
        linesA.append("  ".join([
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


def render_channel_distribution_v3(country: str, rows: list[dict], topn: int = 5) -> str:
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
                .replace("bank.transfer","bank")
                .replace(".ph.nat","").replace("qr.code","qr").replace("direct","dir")
                for r in rows]
    counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
    vols    = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
    avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
    ratios  = [f"{_to_percent_number(r.get('pct_of_country_total_native',0)):.0f}" for r in rows]

    # --- Wrap channel names if too long ---
    MAX_CHANNEL = 20
    chan_wrapped = [wrap(ch, width=MAX_CHANNEL, break_long_words=True, break_on_hyphens=True) or [""] for ch in channels]

    # --- Column widths ---
    w1 = max(len("Cnt"), *(len(x) for x in counts))
    w2 = max(len("Vol"), *(len(x) for x in vols))
    w3 = max(len("Avg"), *(len(x) for x in avgs))
    w4 = max(len("%"),   *(len(x) for x in ratios))

    header = " ".join([
        "Cnt".rjust(w1),
        "Vol".rjust(w2),
        "Avg".rjust(w3),
        "%".rjust(w4),
    ])
    sep = "-" * len(header)

    lines = [sep, header, sep]
    for i in range(len(rows)):
        # Channel line(s)
        for frag in chan_wrapped[i]:
            lines.append(frag)
        # Numbers line
        lines.append(" ".join([
            counts[i].rjust(w1),
            vols[i].rjust(w2),
            avgs[i].rjust(w3),
            ratios[i].rjust(w4),
        ]))

    # Inline-code each line so Telegram preserves spacing
    def inline_code_line(s: str) -> str:
        return f"`{s.replace('`','ˋ')}`"

    code_lines = [inline_code_line(l) for l in lines]
    return "\n".join([title, *code_lines])

async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 35):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution_v2(country, rows)
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

def render_dpf_table(country: str, rows: list[dict], max_width: int = 72) -> str:
    flag     = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    # Title (outside code)
    raw_title = f"COUNTRY: {country} {flag} - ({currency})"
    title_line = stylize(f"*{escape_md_v2(raw_title)}*", style="sans_bold")

    # Pre-format values
    dates, avgs, totals, weights = [], [], [], []
    for r in rows:
        dates.append(str(r.get("date", "")))
        avgs.append(fmt_num_commas(r.get("AverageDeposit", 0)))
        totals.append(fmt_num_commas(r.get("TotalDeposit", 0)))
        # integer percentage (no dot => avoids extra escapes)
        weights.append(str(fmt_pct(r.get("Weightage", 0), decimals=0)).replace("%",""))

    # Column widths (include header labels so header aligns)
    w_date  = max(len("Date"), *(len(s) for s in dates)) if dates else len("Date")
    w_avg   = max(len("Avg"),  *(len(s) for s in avgs))  if avgs  else len("Avg")
    w_total = max(len("Total"),*(len(s) for s in totals))if totals else len("Total")
    w_wgt   = max(len("%"), *(len(s) for s in weights)) if weights else len("%")

    # Build header (plain text; we’ll wrap in inline code later)
    header_plain = " ".join([
        "Date".ljust(w_date),
        "Avg".rjust(w_avg),
        "Total".rjust(w_total),
        "%".rjust(w_wgt),
    ])
    sep_plain = "-" * len(header_plain)

    # Build rows (plain text)
    row_plains = []
    for i in range(len(rows)):
        row_plains.append(" ".join([
            dates[i].ljust(w_date),
            avgs[i].rjust(w_avg),
            totals[i].rjust(w_total),
            weights[i].rjust(w_wgt),
        ]))

    # Inline-code each line: only backtick is special inside inline code
    def inline_code(s: str) -> str:
        return f"`{s.replace('`', 'ˋ')}`"

    table_lines = [inline_code(sep_plain), inline_code(header_plain), inline_code(sep_plain)]
    table_lines.extend(inline_code(s) for s in row_plains)

    return "\n".join([title_line, *table_lines])


async def send_dpf_tables(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    """Send one DPF table per country."""
    for country, rows in sorted(country_groups.items()):
        text = render_dpf_table(country, rows, max_width=max_width)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )