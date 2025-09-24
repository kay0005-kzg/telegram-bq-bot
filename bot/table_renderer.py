from telegram import Update
from telegram.constants import ParseMode
from textwrap import wrap
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import time

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

# Inline-code helper: no newlines allowed inside
def inline_code_line(s: str) -> str:
    return f"`s`"

def count_separators(s: str) -> int:
    return s.count("-") + s.count(",")

current_time, _ = get_date_range_header()

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
        _d = count_separators(d)
        _n = count_separators(n)
        _f = count_separators(f)
        _s = count_separators(s)
        _t = count_separators(t)
        print(d, n, f, s, t)
        return " ".join([
            replace_spacing(d.ljust(w0), x0, _d),
            replace_spacing(n.rjust(w1), x1, _n),
            replace_spacing(f.rjust(w2), x2, _f),
            replace_spacing(s.rjust(w3), x3, _s),
            replace_spacing(t.rjust(w4), x4, _t),
        ])

    header = fmt_row("Date", "NAR", "FTD", "STD", "TTD")
    sep = "-".join(["-" * w0, "-" * w1, "-" * w2, "-" * w3, "-" * w4])

    # --- build output ---
    current_time, date_range = get_date_range_header()

    if not brand:
        title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")

        if list(brand_groups.keys())[0] == "TOTAL":
            subtitle = "\n" + escape_md_v2(f"Acquisition Summary by Country \n(up to {current_time} GMT+7)")
        else:
            subtitle = "\n" + escape_md_v2(f"Acquisition Summary by Group \n(up to {current_time} GMT+7)")

        title_line = title + subtitle
        parts = [title_line]

        # Show separator + header ONCE (above first brand)
        # parts.append(inline_code_line(sep))
        parts.append(wrap_separators(inline_code_line(header)))
        # parts.append(inline_code_line(sep))
    else:
        if (country == "BD") or (country == "PK"):
            parts = [wrap_separators(inline_code_line(header))]
        else:
            parts = []

    # Then each brand with only its rows

        # Sort brands by TTD (DESC)

    first = True
    for brand_name, items in sorted(brand_groups.items()):
        if not first:
            parts.append("")  # blank line between brands
        first = False
        print(country, brand)
        # if ((country != "BD") & (country != "PK")) & (brand == False):
            # print("SUCCESS", country, brand)
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

    # 3) BRAND breakdown (your function already groups by brand inside)
    brands_block = render_apf_table_v2(country, group_rows, max_width=max_width, brand = True)

    if (country != "BD") & (country != "PK"):
        group_block = render_apf_table_v2(country, group_summary_rows, max_width=max_width)
        # 2) Separator
        sep_line = "—" * 10

        return "\n".join([group_block,sep_line, brands_block])
    
    flag = FLAGS.get(country, "")
    title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
    subtitle = "\n" + escape_md_v2(f"Acquisition Summary by Group \n(up to {current_time} GMT+7)")

    title_line = title + subtitle
    parts = [title_line, brands_block]
    return "\n".join(parts)

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

        print(f"Country {country} has {len(rows)} rows in {len(groups_sorted)} groups.")

        # one message per GROUP
        for gname, g_rows in groups_sorted:
            msg = render_group_then_brands(country, gname, g_rows, max_width=max_width)
            
            for chunk in split_table_text_customize(msg, first_len=1000):
                # safe_chunk = escape_md_v2(chunk)
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=False
                )

        # --- country GRAND TOTAL by date (all groups/brands) ---
        total_msg = render_country_total(country, rows, max_width=max_width)
        for chunk in split_table_text_customize(total_msg, first_len=1000):
            # safe_chunk = escape_md_v2(chunk)
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )

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

FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
CURRENCIES = {"PH":"PHP","TH":"THB","BD":"BDT","PK":"PKR","ID":"IDR"}

def render_channel_distribution(country: str, rows: list[dict], topn: int = 5) -> str:
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
    channels = [str(r.get("method",""))
                .replace("-bd","").replace("-id","").replace("-pk","")
                .replace("native","nat").replace("bank-transfer","bank")
                .replace("-ph","").replace("qr-code","qr").replace("direct","dir")
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
    x1 = max(count_separators("Cnt"), *(count_separators(x) for x in counts or ["0"]))

    w_vol = max(len("Vol"), *(len(x) for x in vols   or ["0"]))
    x2 = max(count_separators("Vol"), *(count_separators(x) for x in vols   or ["0"]))

    w_avg = max(len("Avg"), *(len(x) for x in avgs   or ["0"]))
    x3 = max(count_separators("Avg"), *(count_separators(x) for x in avgs   or ["0"]))

    w_pct = max(len("%"),   *(len(x) for x in ratios or ["0"]))
    # replace_spacing
    headerA = "  ".join([
        "#".rjust(w_idx),
        replace_spacing("Cnt".rjust(w_cnt), x1, 0),
        replace_spacing("Vol".rjust(w_vol), x2, 0),
        replace_spacing("Avg".rjust(w_avg), x3, 0),
        "%".rjust(w_pct),
    ])
    # sepA = r"\\" + (r"-" * len(headerA))

    # --- Inline-code each line so Telegram preserves spacing ---
    def inline_code_line(s: str) -> str:
        return f"`{s.replace('`','ˋ')}`"
    
    # --- Build Table A: one line per row ---
    def inline_code(s: str) -> str:
        return f"`{s}`"
    # headerA = [wrap_separators(inline_code(headerA))]

    linesA = []
    for i in range(len(rows)):
        _count = count_separators(counts[i])
        _vols = count_separators(vols[i])
        _avgs = count_separators(avgs[i])
        
        linesA.append("  ".join([
            str(i+1).rjust(w_idx),
            replace_spacing(counts[i].rjust(w_cnt), x1, _count),
            replace_spacing(vols[i].rjust(w_vol), x2, _vols),
            replace_spacing(avgs[i].rjust(w_avg), x3, _avgs),
            ratios[i].rjust(w_pct),
        ]))

    # --- Build Table B: index → channel mapping ---
    headerB = f"{'#'.rjust(w_idx)}  Channel"

    # sublinesB = [headerB]
    linesB = []
    for i, frags in enumerate(chan_wrapped, start=1):
        linesB.append(f"{str(i).rjust(w_idx)}  {frags[0]}")
        for frag in frags[1:]:
            linesB.append(f"{'   ' * w_idx}  {frag}")

    codeA = [wrap_separators(inline_code_line(l)) for l in linesA]

    codeB = [escape_md_v2(l) for l in linesB]
    halfB = f"`{"\n".join([*codeB])}`"

    print("\n".join([title, *codeA]))
    return "\n".join([title,*codeA, "", halfB])
    # return "\n".join([title, *headerA, *codeA, "", *sublinesB, *codeB])

async def send_channel_distribution(update: Update, country_groups: dict[str, list[dict]], max_width: int = 35):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution(country, rows)
        # fancy = stylize(text, style = "mono")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False)
        
        # await update.message.reply_text(textB, parse_mode=ParseMode.MARKDOWN_V2,
        #     disable_web_page_preview=False)
        
async def send_channel_distribution_v2(update: Update, country_groups: dict[str, list[dict]], max_width: int = 35):
    for country, rows in sorted(country_groups.items()):
        text = render_channel_distribution(country, rows)
        # fancy = stylize(text, style = "mono")
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False)

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
    # def replace_spacing(s: str, max_sep: int, cur_sep: int):
    #     if cur_sep < max_sep:
    #         dif = max_sep - cur_sep
    #         return s.replace(f"`{" "*dif}`")
    #     else:
    #         return s
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
    flag = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")
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

            num_sep_a = count_separators(a)
            num_sep_t = count_separators(t)
            print(num_sep_a, a, replace_spacing(a.rjust(w1), max_sep=x1, cur_sep=num_sep_a))
            
            parts.append(wrap_separators(inline_code_line(fmt_row(
            d.ljust(w0),
            replace_spacing(a.rjust(w1), max_sep=x1, cur_sep=num_sep_a),
            replace_spacing(t.rjust(w2), max_sep=x2, cur_sep=num_sep_t),
            w.rjust(w3)))))

    print(parts)
    return "\n".join(parts)

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

def render_dpf_table_v2(country, rows, max_width=72, brand=False):
    # --- helpers used here are assumed to exist in your env:
    # escape_md_v2, stylize, inline_code_line, wrap_separators, backtick_with_trailing_spaces
    # _num_to_float, _fmt_commas0, _fmt_pct_int, _shrink_date, _sum_field,
    # count_separators, get_date_range_header

    FLAGS = {"TH":"🇹🇭","PH":"🇵🇭","BD":"🇧🇩","PK":"🇵🇰","ID":"🇮🇩"}
    CURRENCIES = {"TH":"THB","PH":"PHP","BD":"BDT","PK":"PKR","ID":"IDR"}
    flag     = FLAGS.get(country, "")
    currency = CURRENCIES.get(country, "")

    import pandas as pd

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
    list_separators = [x0 + x1, x2, x3, 0]
    print("LIST SEPERATORS:", x0, x1, x2, x3)
    # plain-space aligned row (no figure spaces)
    def fmt_row(d, a, t, w):
        d = str(d); a = str(a); t = str(t); w = str(w)
        _a = count_separators(a)
        _t = count_separators(t)

        return " ".join([
            d.ljust(w0),
            replace_spacing(a.rjust(w1), max_sep=x1, cur_sep=_a),
            replace_spacing(t.rjust(w2), max_sep=x2, cur_sep=_t),
            w.rjust(w3),
        ])
    
    def fmt_header_row(d, a, t, w):
        d = str(d); a = str(a); t = str(t); w = str(w)
        _d = count_separators(d)
        _a = count_separators(a)
        _t = count_separators(t)
        return " ".join([
            replace_spacing(d.ljust(w0), max_sep=x0, cur_sep=_d),
            replace_spacing(a.rjust(w1), max_sep=x1, cur_sep=_a),
            replace_spacing(t.rjust(w2), max_sep=x2, cur_sep=_t),
            w.rjust(w3),
        ])
    
    # header + horizontal sep built from real widths
    header = fmt_header_row("Date", "Avg", "Total", "%")
    sep    = "-".join(["-" * w0, "-" * w1, "-" * w2, "-" * w3])

    # --- build output (APF style) ---
    current_time, _ = get_date_range_header()
    title    = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag} ({currency})')}*", style="sans_bold")
    print("BRAND GROUPS", brand_groups)
    print(list(brand_groups.keys()))
    
    if list(brand_groups.keys())[0] == "TOTAL":
        subtitle = "\n" + escape_md_v2(f"Deposit Performance by Country \n(up to {current_time} GMT+7)")
    else:
        subtitle = "\n" + escape_md_v2(f"Deposit Performance by Group \n(up to {current_time} GMT+7)")

    parts = []
    
    if not brand:
        parts.append(title + subtitle)
        # parts.append(inline_code_line(sep))
        parts.append(wrap_separators(inline_code_line(header)))
        # parts.append(inline_code_line(sep))

    # sort brands by TotalDeposit DESC
    brands_sorted = sorted(
        brand_groups.items(),
        key=lambda kv: _sum_field(kv[1], "TotalDeposit"),
        reverse=True
        )
    
    if brand:
        if (country == "BD") | (country == "PK"):
            parts = [wrap_separators(inline_code_line(header))]
        else:
            parts = []

    first = True
    for brand_name, _ in brands_sorted:
        if not first:
            parts.append("")  # blank line between brands
        first = False

        # if brand == False:
            # parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))

        # if brand == True:
        parts.append(stylize(f"*{escape_md_v2(str(brand_name))}*", style="sans_bold"))
        
        # rows for this brand (already collapsed in prepped)
        for r in filter(lambda x: x["brand"] == brand_name, prepped):
 
            d, a, t, w = _row_strs(r)
            line = fmt_row(d, escape_md_v2(a), escape_md_v2(t), escape_md_v2(w))

            print(line)
            parts.append(wrap_separators(inline_code_line(line)))

    print(parts)

    return "\n".join(parts)

def replace_spacing(s: str, max_sep: int, cur_sep: int):
    print(cur_sep, max_sep, s)
    if cur_sep < max_sep:
        dif = max_sep - cur_sep
        print(s.replace(" "*dif, f"`{" "*dif}`"), 1)
        return s.replace(" "*dif, f"{":"*dif}", 1)
    else:
        return s
    
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

       # 3) BRAND breakdown (your function already groups by brand inside)
    brands_block = render_dpf_table_v2(country, group_rows, max_width=max_width, brand = True)

    if (country != "BD") & (country != "PK"):
        group_block = render_dpf_table_v2(country, group_summary_rows, max_width=max_width)
        # 2) Separator
        sep_line = "—" * 10

        return "\n".join([group_block,sep_line, brands_block])
    
    flag = FLAGS.get(country, "")
    title = stylize(f"*{escape_md_v2(f'COUNTRY: {country} {flag}')}*", style="sans_bold")
    subtitle = "\n" + escape_md_v2(f"Deposit Summary by Group \n(up to {current_time} GMT+7)")

    title_line = title + subtitle
    parts = [title_line, brands_block]

    return "\n".join(parts)

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
            for chunk in split_table_text_customize(msg, first_len=1020):
                await update.message.reply_text(
                chunk, 
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
                )

        # final country GRAND TOTAL by date
        total_msg = render_dpf_country_total(country, rows, max_width=max_width)
        for chunk in split_table_text_customize(total_msg, first_len=800):
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
            result.append("`,`")
            i += 1
        elif ch == ":":
            result.append("` `")
            # i += 1
            # if i == count_:
                # result.append(f"`{" "*i}`")
        else:
            result.append(ch)

    final_result= "".join(result)
    # print("RESULT:", final_result)
    final_result = final_result.replace("` `` `", " ")
    print("RESULT:", final_result)
    return final_result

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
