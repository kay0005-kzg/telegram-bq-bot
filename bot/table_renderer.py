from telegram import Update
from telegram.constants import ParseMode
import html
from textwrap import wrap
from math import ceil

# ---------- TableFormatter (auto-fit + wrapping) ----------
class TableFormatter:
    """
    Pretty box-drawing tables for Telegram (monospace).
    - Auto-computes column widths
    - Optional max_width to auto-wrap cells so the whole table fits
    - Right-aligns numeric columns, left-aligns text
    """

    def __init__(self, headers, rows, pad=1, min_col_width=3):
        self.headers = [str(h) for h in headers]
        self.rows = [[("" if c is None else str(c)) for c in r] for r in rows]
        self.pad = pad
        self.min_col_width = max(1, min_col_width)

    def format(self, max_width=None):
        widths = self._natural_widths()
        if max_width:
            widths = self._shrink_to_fit(widths, max_width)

        lines = []
        top = self._hline("┌", "┬", "┐", widths)
        mid = self._hline("├", "┼", "┤", widths)
        bot = self._hline("└", "┴", "┘", widths)

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

    def _hline(self, left, mid, right, widths):
        segs = [("─" * (w + 2 * self.pad)) for w in widths]
        return left + mid.join(segs) + right

    def _is_numeric(self, s: str) -> bool:
        s = s.strip()
        if not s:
            return False
        return all(ch.isdigit() or ch in "+-., " for ch in s) and any(ch.isdigit() for ch in s)

    def _wrap_cell(self, text, width):
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
            lines.append("│" + "│".join(parts) + "│")
        return lines

# ---------- Helpers ----------
def _fmt_number(x):
    # Safe, compact formatting for ints/floats/strings
    try:
        if isinstance(x, str) and x.strip() == "":
            return ""
        n = float(x)
        if n.is_integer():
            return f"{int(n):,}"
        return f"{n:,.2f}"
    except Exception:
        return str(x)
    
def _fmt_pct(x):
    try:
        n = float(x) * 100.0
        # Hiển thị 2 chữ số thập phân, ví dụ 12.34%
        return f"{n:.2f}%"
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

# ---------- Rendering using TableFormatter ----------
def render_apf_table(country, rows, max_width=72):
    """
    Build a wrapped box-drawing table for a single country.
    rows: list of dicts with keys: date, brand, NAR, FTD, STD, TTD
    max_width: max characters allowed for the table width (including borders)
    """
    headers = ["Date", "Brand", "NAR", "FTD", "STD", "TTD"]
    data_rows = []
    for r in rows:
        data_rows.append([
            str(r.get("date", "")),
            str(r.get("brand", "")),
            _fmt_number(r.get("NAR", 0)),
            _fmt_number(r.get("FTD", 0)),
            _fmt_number(r.get("STD", 0)),
            _fmt_number(r.get("TTD", 0)),
        ])

    table = TableFormatter(headers, data_rows).format(max_width=max_width)
    title = f"Country: {country}"
    return f"{title}\n{table}"

# ---------- Telegram send ----------
async def send_apf_tables(update: Update, country_groups, max_width=72):
    """
    Send one table per country.
    - max_width controls wrapping to fit mobile/desktop (e.g., 48 for narrow mobile, 72 default).
    """
    for country, rows in sorted(country_groups.items()):
        table_text = render_apf_table(country, rows, max_width=max_width)

        # Escape for HTML parse mode (inside <pre> keep monospaced)
        safe_text = html.escape(table_text)
        # If very long (unlikely per country), split into multiple messages
        for chunk in split_table_text(safe_text, max_length=4000):
            await update.message.reply_text(
                f"<pre>{chunk}</pre>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )


def render_channel_distribution(country: str, rows: list[dict], max_width: int = 72) -> str:
    if country == "PH":
        currency = "PHP"
    elif country == "TH":
        currency = "THB"
    elif country == "BD":
        currency = "BDT"
    elif country == "PK":
        currency = "PKR"
    elif country == "ID":
        currency = "IDR"

    headers = [
        "Channel Name",
        "Deposit Counts",
        f"Deposit Volume ({currency})",
        f"Average Deposit ({currency})",
        "% Total",
    ]

    data_rows = []
    for r in rows:
        data_rows.append([
            str(r.get("method", "")),
            _fmt_number(r.get("deposit_tnx_count")),
            _fmt_number(r.get("total_deposit_amount_native")),
            _fmt_number(r.get("average_deposit_amount_native")),
            _fmt_number(r.get("pct_of_country_total_native")),
        ])
    table = TableFormatter(headers, data_rows).format(max_width=max_width)

    title = f"Country: {country}"
    return f"{title}\n{table}"


async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    """
    Send per-country channel distribution tables (one message per country).
    """
    for country, rows in sorted(country_groups.items()):
        table_text = render_channel_distribution(country, rows, max_width=max_width)
        safe_text = html.escape(table_text)
        # split if ever needed
        chunks = split_table_text(safe_text, max_length=4000)
        for chunk in chunks:
            await update.message.reply_text(
                f"<pre>{chunk}</pre>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

def render_dpf_table(country: str, rows: list[dict], max_width: int = 72) -> str:
    """
    DPF table (per country): Date, Deposits, Volume (USD), Average (USD)
    rows must contain: date, deposit_tnx_count, total_deposit_amount_usd, average_deposit_amount_usd
    """
    headers = ["Date", "Average Deposit (USD)", "Total Deposit (USD)", "Weightage"]
    data_rows = []
    for r in rows:
        data_rows.append([
            str(r.get("date", "")),
            _fmt_number(r.get("AverageDeposit", 0)),
            _fmt_number(r.get("TotalDeposit", 0)),
            _fmt_pct(r.get("Weightage", 0)),
        ])
    table = TableFormatter(headers, data_rows).format(max_width=max_width)
    title = f"Country: {country}"
    return f"{title}\n{table}"

async def send_dpf_tables(update: Update, country_groups: dict[str, list[dict]], max_width: int = 72):
    """Send one DPF table per country."""
    for country, rows in sorted(country_groups.items()):
        table_text = render_dpf_table(country, rows, max_width=max_width)
        safe_text = html.escape(table_text)
        for chunk in split_table_text(safe_text, max_length=4000):
            await update.message.reply_text(
                f"<pre>{chunk}</pre>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )