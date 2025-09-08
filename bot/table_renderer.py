from telegram import Update
from telegram.constants import ParseMode
import html
from textwrap import wrap
from math import ceil
from collections import defaultdict
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
    
def _fmt_pct(x, deno = 2):
    try:
        n = float(x) * 100.0
        # Hiển thị 2 chữ số thập phân, ví dụ 12.34%
        if deno == 2:
            return f"{n:.2f}%"
        if deno == 1:
            return f"{n:.1f}%"
    except Exception:
        return "" if x in (None, "") else str(x)
    
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

def render_apf_table(country, rows, max_width=72):
    from collections import defaultdict
    brand_groups = defaultdict(list)
    for r in rows:
        brand_groups[r.get("brand", "Unknown")].append(r)

    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    flag = FLAGS.get(country, "")

    # Escape country line and columns line
    title_line   = f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*"
    columns_line = escape_md_v2("Date | NAR | FTD | STD | TTD")

    parts = [title_line, columns_line]

    for brand, items in sorted(brand_groups.items()):
        dates = [str(r.get("date", "")) for r in items]
        nars  = [str(_fmt_number(r.get("NAR", 0))) for r in items]
        ftds  = [str(_fmt_number(r.get("FTD", 0))) for r in items]
        stds  = [str(_fmt_number(r.get("STD", 0))) for r in items]
        ttds  = [str(_fmt_number(r.get("TTD", 0))) for r in items]

        w0 = max(len(x) for x in dates) if dates else 0
        w1 = max(len(x) for x in nars)  if nars  else 0
        w2 = max(len(x) for x in ftds)  if ftds  else 0
        w3 = max(len(x) for x in stds)  if stds  else 0
        w4 = max(len(x) for x in ttds)  if ttds  else 0

        lines = []
        for i in range(len(items)):
            line = " | ".join([
                dates[i].ljust(w0),
                nars[i].rjust(w1),
                ftds[i].rjust(w2),
                stds[i].rjust(w3),
                ttds[i].rjust(w4),
            ])
            lines.append(line)

        # Escape brand name (outside code block)
        brand_line = escape_md_v2(str(brand))

        # Table block inside code block (no escaping needed)
        table_block = "```\n" + "\n".join(lines) + "```"
        parts.append(f"{brand_line}\n{table_block}")

    return "\n\n".join(parts)

# ---------- Telegram send ----------
async def send_apf_tables(update: Update, country_groups, max_width=72, max_length=4000):
    for country, rows in sorted(
        ((c, r) for c, r in country_groups.items() if c is not None),
        key=lambda x: x[0]
    ):
        table_text = render_apf_table(country, rows, max_width=max_width)

        chunks = split_table_text_customize(table_text, first_len=4000)
        for chunk in chunks:
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
def escape_md_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, "\\" + ch)
    return text

def render_channel_distribution(country: str, rows: list[dict], max_width: int = 72) -> str:
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"PH": "PHP", "TH": "THB", "BD": "BDT", "PK": "PKR", "ID": "IDR"}

    flag = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    def escape_md_v2(text: str) -> str:
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        for ch in escape_chars:
            text = text.replace(ch, "\\" + ch)
        return text

    title_line   = f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*"
    columns_line = escape_md_v2(f"Count | Volume ({currency}) | Avg ({currency}) | Ratio (%)")

    counts  = [str(_fmt_number(r.get("deposit_tnx_count"))) for r in rows]
    volumes = [str(_fmt_number(r.get("total_deposit_amount_native"))) for r in rows]
    avgs    = [str(_fmt_number(r.get("average_deposit_amount_native"))) for r in rows]
    pcts    = [str(_fmt_pct(r.get("pct_of_country_total_native", 0), deno=2)) for r in rows]

    w1 = max((len(x) for x in counts),  default=0)
    w2 = max((len(x) for x in volumes), default=0)
    w3 = max((len(x) for x in avgs),    default=0)
    w4 = max((len(x) for x in pcts),    default=0)

    block_lines = []
    for i, r in enumerate(rows):
        method = escape_md_v2(str(r.get("method", "")))
        num_line = " | ".join([
            counts[i].rjust(w1),
            volumes[i].rjust(w2),
            avgs[i].rjust(w3),
            pcts[i].rjust(w4),
        ])
        # 👉 no extra blank line
        block_lines.append(f"{method}\n {num_line}")

    code_block = "```\n" + "\n".join(block_lines) + "\n```"

    return "\n".join([title_line, columns_line, "", code_block])

async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution(country, rows, max_width=max_width)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

def render_dpf_table(country: str, rows: list[dict], max_width: int = 72) -> str:
    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"PH": "PHP", "TH": "THB", "BD": "BDT", "PK": "PKR", "ID": "IDR"}

    flag = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    def escape_md_v2(text: str) -> str:
        escape_chars = r"_*[]()~`>#+-=|{}.!"
        for ch in escape_chars:
            text = text.replace(ch, "\\" + ch)
        return text

    # Title + column description (outside code block)
    title_line   = f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*"
    columns_line = escape_md_v2(f"Date | Avg Deposit ({currency}) | Total Deposit ({currency}) | Weightage")

    # Build row strings
    dates   = [str(r.get("date", "")) for r in rows]
    avgs    = [str(_fmt_number(r.get("AverageDeposit", 0))) for r in rows]
    totals  = [str(_fmt_number(r.get("TotalDeposit", 0))) for r in rows]
    weights = [str(_fmt_pct(r.get("Weightage", 0), deno = 1)) for r in rows]

    w0 = max((len(x) for x in dates),   default=0)
    w1 = max((len(x) for x in avgs),    default=0)
    w2 = max((len(x) for x in totals),  default=0)
    w3 = max((len(x) for x in weights), default=0)

    lines = []
    for i in range(len(rows)):
        line = " | ".join([
            dates[i].ljust(w0),
            avgs[i].rjust(w1),
            totals[i].rjust(w2),
            weights[i].rjust(w3),
        ])
        lines.append(line)

    code_block = "```\n" + "\n".join(lines) + "\n```"

    return "\n".join([title_line, columns_line, "", code_block])

async def send_dpf_tables(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    """Send one DPF table per country."""
    # for country, rows in sorted(country_groups.items()):
    #     table_text = render_dpf_table(country, rows, max_width=max_width)
    #     safe_text = html.escape(table_text)
    #     for chunk in split_table_text(safe_text, max_length=4000):
    #         await update.message.reply_text(
    #             f"<pre>{chunk}</pre>",
    #             parse_mode=ParseMode.HTML,
    #             disable_web_page_preview=True
    #         )
    for country, rows in sorted(country_groups.items()):
        text = render_dpf_table(country, rows, max_width=max_width)
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )