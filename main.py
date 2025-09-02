import os
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

from bot.config import Config
from bot.bq_client import BigQueryClient
from bot.table_renderer import send_apf_tables, send_channel_distribution, send_dpf_tables

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

def _parse_target_date(date_str: str):
    """Parse YYYYMMDD -> 'YYYY-MM-DD' string; raise on invalid."""
    dt = datetime.strptime(date_str, "%Y%m%d")  # will raise ValueError if bad
    return dt.strftime("%Y-%m-%d")

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

class RealTimeBot:
    def __init__(self):
        self.config = Config()
        self.bq_client = BigQueryClient(self.config)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = """🤖 **Realtime Report Bot**

*Deposit Channel Distribution* (Specific date)
• `/dist a <YYYYMMDD>`: Distribution for all countries
• `/dist <COUNTRY> <YYYYMMDD>`: Distribution for one country (e.g., `/dist TH 20250901`)

*Acquisition Performance* (Rolling 3 days)
• `/apf a`: Acquisition data for all countries
• `/apf <COUNTRY>`: Data for a specific country (e.g., `/apf TH`)

*Deposit Performance* (Rolling 3 days)
• `/dpf a`: Deposit data for all countries
• `/dpf <COUNTRY>`: Data for a specific country (e.g., `/dpf PH`)

*📍 Supported Countries:* TH, PH, BD, PK, ID

*ℹ️ Data Scope:*
• *Timezone:* Asia/Bangkok (UTC+7)
• *Update Frequency:* Near real-time"""
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    async def apf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                return await update.message.reply_text(
                    "Please type the correct function: `/apf a` or `/apf <COUNTRY>` (TH, PH, BD, PK, ID)",
                    parse_mode=ParseMode.MARKDOWN,
                )

            sel = context.args[0].upper().strip()
            if sel == "A":
                selected_country = None
                scope_label = "all countries"
            else:
                if sel not in self.config.APF_ALLOWED:
                    return await update.message.reply_text(
                        f"❌ Unsupported country `{sel}`. Allowed: {', '.join(sorted(self.config.APF_ALLOWED))}"
                    )
                selected_country = sel
                scope_label = sel

            rows = await self.bq_client.execute_apf_query(selected_country)
            if not rows:
                return await update.message.reply_text(f"No data for {scope_label}.")

            country_groups = {}
            for row in rows:
                country = row.get("country", "Unknown")
                if country not in country_groups:
                    country_groups[country] = []
                country_groups[country].append(row)

            current_time, date_range = get_date_range_header()
            header_text = (
                f"📊 *Acquisition Summary* \n"
                f"⏰ Daily Data Cutoff: Data up to {current_time} (BKK) for each day \n"
                f"📅 Date range: {date_range[2]} → {date_range[0]}"
            )
            await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            await send_apf_tables(update, country_groups, max_width=52)

        except Exception as e:
            logger.exception("Error in /apf")
            await update.message.reply_text(
                f"Error: `{e}`\nLocation: {self.config.BQ_LOCATION}", 
                parse_mode=ParseMode.MARKDOWN
            )

    async def dist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /dist: exact-date distribution in NATIVE currency.
        Usage:
          /dist a 20250901
          /dist TH 20250901
        """
        try:
            if len(context.args) < 2:
                return await update.message.reply_text(
                    "Usage: `/dist a <YYYYMMDD>` or `/dist <COUNTRY> <YYYYMMDD>`",
                    parse_mode=ParseMode.MARKDOWN
                )

            selector = context.args[0].upper().strip()
            date_str = context.args[1].strip()

            # Parse target date
            try:
                target_date = _parse_target_date(date_str)  # 'YYYY-MM-DD'
            except ValueError:
                return await update.message.reply_text(
                    "❌ Invalid date format. Use `YYYYMMDD` (e.g., `20250901`).",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Country filter
            if selector == "A":
                selected_country_value = None
                target_label = "all countries"
            else:
                if selector not in self.config.APF_ALLOWED:
                    return await update.message.reply_text(
                        f"❌ Unsupported country `{selector}`. "
                        f"Allowed: {', '.join(sorted(self.config.APF_ALLOWED))}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                selected_country_value = selector
                target_label = selector

            # Query BQ: exact date + native currency
            rows = await self.bq_client.execute_dist_query(target_date, selected_country_value)

            if not rows:
                return await update.message.reply_text(
                    f"No results for {target_label} on {target_date}.",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Group rows by country
            country_groups: dict[str, list[dict]] = {}
            for r in rows:
                c = (r.get("country") or "") or "Unknown"
                country_groups.setdefault(c, []).append(r)

            # Header
            header_text = (
                f"📊 *Deposit Channel Distribution* \n"
                f"⏰ Date: {target_date}\n"
            )
            await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            # Render (table_renderer handles native currency keys)
            await send_channel_distribution(update, country_groups, max_width=72)

        except Exception as e:
            logging.exception("Error in /dist")
            await update.message.reply_text(
                f"Error: `{e}`\nLocation: {self.config.BQ_LOCATION}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def dpf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                return await update.message.reply_text(
                    "Usage: `/dpf a` or `/dpf <COUNTRY>` (TH, PH, BD, PK, ID)",
                    parse_mode=ParseMode.MARKDOWN,
                )

            sel = context.args[0].upper().strip()
            if sel == "A":
                selected_country = None
                scope_label = "all countries"
            else:
                if sel not in self.config.APF_ALLOWED:
                    return await update.message.reply_text(
                        f"❌ Unsupported country `{sel}`. Allowed: {', '.join(sorted(self.config.APF_ALLOWED))}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                selected_country = sel
                scope_label = sel

            rows = await self.bq_client.execute_dpf_query(selected_country)
            if not rows:
                return await update.message.reply_text(f"No deposit data for {scope_label}.")

            country_groups: dict[str, list[dict]] = {}
            for r in rows:
                c = (r.get("country") or "") or "Unknown"
                country_groups.setdefault(c, []).append(r)

            current_time, date_range = get_date_range_header()
            header_text = (
                f"💸 *Deposit Performance* \n"
                f"⏰ Daily Data Cutoff: Data up to {current_time} (BKK) for each day \n"
                f"📅 Date range: {date_range[2]} → {date_range[0]}"
            )
            await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            await send_dpf_tables(update, country_groups, max_width=52)

        except Exception as e:
            logger.exception("Error in /dpf")
            await update.message.reply_text(
                f"Error: `{e}`\nLocation: {self.config.BQ_LOCATION}",
                parse_mode=ParseMode.MARKDOWN
            )

    def run(self):
        application = ApplicationBuilder().token(self.config.TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler(["help", "start"], self.help_command))
        application.add_handler(CommandHandler("apf", self.apf_command))
        application.add_handler(CommandHandler("dist", self.dist_command))
        application.add_handler(CommandHandler("dpf", self.dpf_command))
        application.run_polling(poll_interval=2.0, timeout=50)

if __name__ == "__main__":
    bot = RealTimeBot()
    bot.run()