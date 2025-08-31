import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from html import escape

from google.cloud import bigquery
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from dotenv import load_dotenv

load_dotenv()

# ---------------- Config ----------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BQ_PROJECT = os.environ.get("BQ_PROJECT")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "asia-southeast1")

ALLOWED_COUNTRIES = {"TH", "PH", "BD", "PK", "ID"}

with open("deposit_report.sql", "r", encoding="utf-8") as f:
    SQL_TEXT = f.read()

bq_client = bigquery.Client(project=BQ_PROJECT, location=BQ_LOCATION)

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# ---------------- Helpers (render) ----------------
def _format_int(x):
    try:
        return f"{int(float(x)):,}"
    except Exception:
        return str(x)

def _render_country_table_text(rows_for_country) -> str:
    """Return plain text table (no HTML); caller wraps with <pre> and escapes it."""
    headers = [
        "Channel Name",
        "Deposit Counts",
        "Deposit Volume (USD)",
        "Average Deposit (USD)",
        "% of Total Volume (USD)",
    ]

    data = []
    for r in rows_for_country:
        data.append([
            (r.get("method") or ""),
            _format_int(r.get("deposit_tnx_count", 0)),
            _format_int(r.get("total_deposit_amount_usd", 0)),
            _format_int(r.get("average_deposit_amount_usd", 0)),
            (r.get("pct_of_country_total_usd") or ""),
        ])

    cols = list(zip(*([headers] + data))) if data else [headers]
    widths = [max(len(str(cell)) for cell in col) for col in cols]

    def _line(cells):
        return "  ".join(str(cells[i]).ljust(widths[i]) for i in range(len(headers)))

    lines = []
    lines.append(_line(headers))
    lines.append("  ".join("-" * w for w in widths))
    for row in data:
        lines.append(_line(row))

    return "\n".join(lines)


def build_country_sections(all_rows):
    """Return list of (title_html, table_text_plain)."""
    groups = defaultdict(list)
    for r in all_rows:
        groups[r.get("country") or ""].append(r)

    sections = []
    for country in sorted(groups.keys()):
        title_html = f"<b>{escape(country)}</b>\n\n" if country else ""
        table_text = _render_country_table_text(groups[country])
        sections.append((title_html, table_text))
    return sections

async def send_sections_html(reply_fn, sections, header_html=""):
    """
    Send each (title_html, table_text) section as one or more HTML messages,
    wrapping table_text in <pre> with proper escaping. Avoid splitting inside tags.
    """
    MAX = 3900  # safety margin under Telegram's ~4096 hard limit

    if header_html:
        await reply_fn(header_html)

    for (title_html, table_text) in sections:
        # try to fit in one message first
        block = title_html + "<pre>" + escape(table_text) + "</pre>"
        if len(block) <= MAX:
            await reply_fn(block)
            continue

        # otherwise split by lines and send multiple <pre> blocks
        lines = table_text.splitlines()
        cur_lines = []
        cur_len = len(title_html) + len("<pre></pre>")  # constant overhead

        for ln in lines:
            ln_len = len(ln) + 1  # include newline
            if cur_len + ln_len > MAX:
                # flush current
                piece = "\n".join(cur_lines)
                await reply_fn(title_html + "<pre>" + escape(piece) + "</pre>")
                # next chunks won't repeat the title
                title_html = ""
                cur_lines, cur_len = [ln], len("<pre></pre>") + ln_len
            else:
                cur_lines.append(ln)
                cur_len += ln_len

        if cur_lines:
            piece = "\n".join(cur_lines)
            await reply_fn(title_html + "<pre>" + escape(piece) + "</pre>")

# ---------------- Commands ----------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Usage:\n"
        "<code>/dist a &lt;YYYYMMDD&gt;</code> → Show ALL countries\n"
        "<code>/dist &lt;COUNTRY&gt; &lt;YYYYMMDD&gt;</code> → Show ONE country (TH, PH, BD, PK, ID)\n\n"
        "Examples:\n"
        "<code>/dist a 20250821</code>\n"
        "<code>/dist BD 20250821</code>\n\n"
        "Cutoff time is the moment you send the command (your local time)."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def dist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Validate args
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: <code>/dist a &lt;YYYYMMDD&gt;</code> or <code>/dist &lt;COUNTRY&gt; &lt;YYYYMMDD&gt;</code>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return

        selector = context.args[0].upper()  # "A" for all, or country code
        date_str = context.args[1]           # YYYYMMDD

        # Parse date
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Use <code>YYYYMMDD</code> (e.g., <code>20250821</code>).",
                parse_mode=ParseMode.HTML,
            )
            return

        # Cutoff = that date at current local time (Asia/Ho_Chi_Minh)
        now_local = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        cutoff_ts = datetime.combine(date_obj.date(), now_local.time(), tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

        # Country filter
        if selector == "A":
            selected_country_value = None
            target_label = "all countries"
        else:
            if selector not in ALLOWED_COUNTRIES:
                await update.message.reply_text(
                    f"❌ Unsupported country <code>{escape(selector)}</code>. "
                    f"Allowed: {', '.join(sorted(ALLOWED_COUNTRIES))}",
                    parse_mode=ParseMode.HTML,
                )
                return
            selected_country_value = selector
            target_label = selector

        # Build query with BOTH params present every time
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cutoff_ts", "TIMESTAMP", cutoff_ts.isoformat()),
                bigquery.ScalarQueryParameter("selected_country", "STRING", selected_country_value),
            ]
        )

        # Run query
        query_job = bq_client.query(SQL_TEXT, job_config=job_config)
        rows = [dict(r.items()) for r in query_job.result()]

        if not rows:
            await update.message.reply_text(
                f"No results for {escape(target_label)} up till {escape(cutoff_ts.isoformat())}",
                parse_mode=ParseMode.HTML,
            )
            return

        # ---------------- No FX conversion here: USD fields come from BigQuery ----------------

        # Header (HTML)
        header_html = (
            f"<b>Summarized deposit volume for deposit channels up till "
            f"{escape(cutoff_ts.strftime('%Y-%m-%d %H:%M:%S'))}</b>"
        )

        # Build sections and send
        sections = build_country_sections(rows)

        async def _reply(msg_html: str):
            return await update.message.reply_text(
                msg_html, parse_mode=ParseMode.HTML, disable_web_page_preview=True
            )

        await send_sections_html(_reply, sections, header_html=header_html)

    except Exception as e:
        logger.exception("Error in /dist")
        await update.message.reply_text(
            f"<b>Error:</b> <code>{escape(str(e))}</code>\n\nLocation: {escape(BQ_LOCATION)}",
            parse_mode=ParseMode.HTML,
        )

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler(["help", "start"], help_cmd))
    app.add_handler(CommandHandler("dist", dist_cmd))
    app.run_polling(poll_interval=2.0, timeout=50)

if __name__ == "__main__":
    main()
