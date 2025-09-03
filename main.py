import os
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

import json
from pathlib import Path

from bot.config import Config
from bot.bq_client import BigQueryClient
from bot.table_renderer import send_apf_tables, send_channel_distribution, send_dpf_tables

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import hmac, hashlib, base64, secrets, time  # add these
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

        base_dir = Path(__file__).resolve().parent

        self.logs_dir = base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.registered_file = self.logs_dir / "registered_users.json"
        self.registered_users = self._load_registered_users()
        
        # Initialize invite tokens
        self.tokens_file = self.logs_dir / "invite_tokens.json"
        self.invite_tokens = self._load_invite_tokens()
        self.register_secret = os.getenv("REGISTER_LINK_SECRET", "change_me_now")

        # Admins (comma-separated user IDs in env)
        raw_admins = os.getenv("ADMIN_USER_IDS", "")
        self.admin_user_ids = {int(x) for x in raw_admins.replace(" ", "").split(",") if x.strip().isdigit()}

    def _load_invite_tokens(self) -> dict:
        """Load invite tokens from logs/invite_tokens.json."""
        try:
            if self.tokens_file.exists():
                with self.tokens_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("tokens", {})
        except Exception:
            logger.exception("Failed to load invite_tokens.json; starting fresh")
        return {}

    def _save_invite_tokens(self) -> None:
        """Save invite tokens to logs/invite_tokens.json."""
        try:
            with self.tokens_file.open("w", encoding="utf-8") as f:
                json.dump({"tokens": self.invite_tokens}, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed to save invite_tokens.json")

    def validate_invite_token(self, token: str) -> tuple[bool, str, dict | None]:
        """
        Validate an invite token and return (is_valid, message, token_data).
        If valid, increments usage count and saves tokens.
        
        Returns:
            (True, "success", token_data) if valid
            (False, error_message, None) if invalid
        """
        try:
            # Decode the token
            def _b64url_decode(s: str) -> bytes:
                # Add padding if needed
                padding = 4 - (len(s) % 4)
                if padding != 4:
                    s += "=" * padding
                return base64.urlsafe_b64decode(s.encode())

            def _verify_signature(secret: str, msg: bytes, sig: str) -> bool:
                expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:16]
                return hmac.compare_digest(expected, sig)

            # Decode token
            try:
                raw = _b64url_decode(token)
                decoded = raw.decode()
            except Exception:
                return False, "Invalid token format", None

            # Parse token components
            parts = decoded.split(":")
            if len(parts) != 3:
                return False, "Malformed token", None

            invite_id, exp_str, sig = parts

            # Verify signature
            msg = f"{invite_id}:{exp_str}".encode()
            if not _verify_signature(self.register_secret, msg, sig):
                return False, "Invalid token signature", None

            # Check if token exists in our records
            if invite_id not in self.invite_tokens:
                return False, "Token not found", None

            token_data = self.invite_tokens[invite_id]

            # Check if revoked
            if token_data.get("revoked", False):
                return False, "Token has been revoked", None

            # Check expiry
            exp_time = int(exp_str)
            if time.time() > exp_time:
                return False, "Token has expired", None

            # Check usage limits
            max_uses = token_data.get("max_uses", -1)
            current_uses = token_data.get("uses", 0)
            
            if max_uses != -1 and current_uses >= max_uses:
                return False, "Token usage limit reached", None

            # Token is valid - increment usage
            token_data["uses"] = current_uses + 1
            self._save_invite_tokens()

            return True, "Valid token", token_data

        except Exception as e:
            logger.exception("Error validating invite token")
            return False, f"Token validation error: {str(e)}", None

    def create_invite_link(
        self,
        *,
        bot_username: str,
        ttl_seconds: int = 30 * 24 * 60 * 60,  # 1 month default
        max_uses: int = -1,                     # -1 = unlimited until expiry
        note: str | None = None
    ) -> str:
        """
        Create a signed deep-link invite usable at:
        https://t.me/<bot_username>?start=<token>

        Persists server-side state in logs/invite_tokens.json:
        {
            "tokens": {
            "<invite_id>": {
                "exp": <unix_ts>,
                "max_uses": -1|int,
                "uses": 0,
                "note": "...",
                "revoked": false,
                "created_at": "ISO-8601"
            },
            ...
            }
        }

        Return: the deep-link URL (string).
        """

        # ---- local helpers (no external deps required) ----
        def _b64url(b: bytes) -> str:
            return base64.urlsafe_b64encode(b).decode().rstrip("=")

        def _sign(secret: str, msg: bytes) -> str:
            return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:16]

        # ---- build signed token ----
        invite_id = secrets.token_hex(8)  # 16-hex id
        exp = int(time.time()) + int(ttl_seconds)
        msg = f"{invite_id}:{exp}".encode()
        sig = _sign(self.register_secret, msg)
        raw = f"{invite_id}:{exp}:{sig}".encode()
        token = _b64url(raw)

        # ---- persist server-side metadata ----
        self.invite_tokens[invite_id] = {
            "exp": int(exp),
            "max_uses": int(max_uses),
            "uses": 0,
            "note": note,
            "revoked": False,
            "created_at": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        }
        self._save_invite_tokens()

        # ---- return deep link ----
        return f"https://t.me/{bot_username}?start={token}"

    def _is_admin(self, update: Update) -> bool:
        u = update.effective_user
        return bool(u and int(u.id) in self.admin_user_ids)

    async def admin_create_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Guard: admin only
        logger.info("Admin create link requested by user_id=%s", update.effective_user.id if update.effective_user else "unknown")
        if not self._is_admin(update):
            return await update.message.reply_text("⚠️ You are not authorized to create invite links.")

        # Default: 24 hours, unlimited uses until expiry
        ttl_seconds = 30 * 24 * 60 * 60
        max_uses = -1  # -1 means unlimited uses until expiry

        # Optional: allow override via args, e.g. "/admin_create_link 24h 50 Finance batch"
        # Formats: 30m, 2h, 24h, 7d
        def _parse_ttl(s: str) -> int:
            s = s.lower().strip()
            if s.endswith("m"): return int(s[:-1]) * 60
            if s.endswith("h"): return int(s[:-1]) * 60 * 60
            if s.endswith("d"): return int(s[:-1]) * 24 * 60 * 60
            if s.endswith("mo"): return int(s[:-2]) * 30 * 24 * 60 * 60  # 1 mo = 30d
            return int(s)  # seconds

        note = None
        if context.args:
            # Try to parse TTL if present as first arg
            try:
                ttl_seconds = _parse_ttl(context.args[0])
                # If there is a second arg and it's an int, treat as max_uses
                if len(context.args) >= 2 and context.args[1].lstrip("-").isdigit():
                    max_uses = int(context.args[1])
                    if max_uses == 0:
                        max_uses = -1  # 0 makes no sense; normalize to unlimited
                # Remaining args form the note
                if len(context.args) >= 3:
                    note = " ".join(context.args[2:])
            except Exception:
                # If parsing fails, keep defaults and treat all args as note
                note = " ".join(context.args)

        # Create the invite deep link
        bot_username = context.bot.username
        link = self.create_invite_link(bot_username=bot_username, ttl_seconds=ttl_seconds, max_uses=max_uses, note=note)

        # Reply with the link
        return await update.message.reply_text(
            "🔗 Invite link created:\n"
            f"{link}\n\n"
            f"⏳ Expires in ~{ttl_seconds//3600}h\n"
            f"👥 Uses: {'unlimited' if max_uses == -1 else max_uses}\n"
            f"📝 {note or '(no note)'}"
        )

    def _load_registered_users(self) -> dict[int, dict]:
        """
        Load registered users from logs/registered_users.json.
        Supports old schema: {"user_ids": [int, ...]}
        New schema: {"users": [{"user_id": int, "username": str|None, "first_name": str|None,
                                "last_name": str|None, "ts": iso8601}, ...]}
        Returns in-memory mapping: { user_id: {username, first_name, last_name, ts} }
        """
        try:
            if self.registered_file.exists():
                with self.registered_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                # New schema
                if isinstance(data, dict) and "users" in data and isinstance(data["users"], list):
                    users = {}
                    for u in data["users"]:
                        uid = u.get("user_id")
                        if isinstance(uid, int):
                            users[uid] = {
                                "username":   u.get("username"),
                                "first_name": u.get("first_name"),
                                "last_name":  u.get("last_name"),
                                "ts":         u.get("ts"),
                            }
                    return users

                # Old schema (backward compatible): {"user_ids": [...]}
                if isinstance(data, dict) and "user_ids" in data and isinstance(data["user_ids"], list):
                    return {int(uid): {"username": None, "first_name": None, "last_name": None, "ts": None}
                            for uid in data["user_ids"]}

        except Exception:
            logger.exception("Failed to load registered_users.json")
        return {}

    def _save_registered_users(self) -> None:
        """
        Save in new schema: {"users": [ ... ]}, stable, human-readable ordering.
        """
        try:
            out = {
                "users": [
                    {
                        "user_id":   int(uid),
                        "username":  info.get("username"),
                        "first_name": info.get("first_name"),
                        "last_name":  info.get("last_name"),
                        "ts":         info.get("ts"),
                    }
                    for uid, info in sorted(self.registered_users.items(), key=lambda kv: kv[0])
                ]
            }
            with self.registered_file.open("w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed to save registered_users.json")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command with optional token parameter.
        If token is provided and valid, register the user automatically.
        """
        user = update.effective_user
        if not user:
            return await update.message.reply_text("⚠️ Could not identify user.")

        uid = int(user.id)
        
        # Check if user is already registered
        if uid in self.registered_users:
            # User already registered, just show help
            return await self.help_command(update, context)

        # Check if there's a token parameter
        if context.args and len(context.args) > 0:
            token = context.args[0]
            
            # Validate the token
            is_valid, message, token_data = self.validate_invite_token(token)
            
            if is_valid:
                # Token is valid - register the user
                self.registered_users[uid] = {
                    "username":   getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "last_name":  getattr(user, "last_name", None),
                    "ts":         datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
                    "registered_via": "invite_token",
                    "invite_note": token_data.get("note") if token_data else None,
                }
                self._save_registered_users()
                
                # Log the registration event
                self._log_event({
                    "event": "user_registered_via_token",
                    "user_id": uid,
                    "username": getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "invite_note": token_data.get("note") if token_data else None,
                })
                
                welcome_msg = (
                    f"🎉 Welcome, {user.first_name or 'User'}! \n"
                    f"You've been successfully registered via invite link.\n\n"
                )
                
                if token_data and token_data.get("note"):
                    welcome_msg += f"📝 Invite note: {token_data['note']}\n\n"
                
                welcome_msg += "Please get started by typing `/help` to see available commands."
                
                await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)
                
            else:
                # Invalid token
                await update.message.reply_text(
                    f"⚠️ Registration failed: {message}\n\n"
                    "Please contact an admin for a valid invite link.",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            # No token provided - user needs to register manually or get an invite
            await update.message.reply_text(
                "👋 Welcome to the Realtime Report Bot!\n\n"
                "🔐 This bot requires registration to use.\n"
                "Please contact an admin to get an invite link.\n\n"
                "If you have an invite link, click on it to register automatically.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def register_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual registration command (kept for backward compatibility)"""
        user = update.effective_user
        if not user:
            return await update.message.reply_text("⚠️ Could not identify user.")

        uid = int(user.id)
        if uid in self.registered_users:
            # Optional: refresh profile fields in case user changed username/name
            self.registered_users[uid].update({
                "username":   getattr(user, "username", None),
                "first_name": getattr(user, "first_name", None),
                "last_name":  getattr(user, "last_name", None),
                "ts":         self.registered_users[uid].get("ts") or datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            })
            self._save_registered_users()
            return await update.message.reply_text("✅ You are already registered!")

        # New registration
        self.registered_users[uid] = {
            "username":   getattr(user, "username", None),
            "first_name": getattr(user, "first_name", None),
            "last_name":  getattr(user, "last_name", None),
            "ts":         datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            "registered_via": "manual",
        }
        self._save_registered_users()

        await update.message.reply_text(
            f"🎉 Welcome, {user.first_name or 'User'}! You are now registered.\n"
            "Please get started by typing in `/help`."
        )

    def _log_event(self, payload: dict):
        try:
            now_bkk = datetime.now(ZoneInfo("Asia/Bangkok"))
            day = now_bkk.strftime("%Y%m%d")
            log_path = self.logs_dir / f"events-{day}.jsonl"

            # ensure timestamp in GMT+7
            payload = dict(payload)  # avoid mutating caller's dict
            payload.setdefault("ts", now_bkk.isoformat())

            # make sure folder exists (defensive)
            self.logs_dir.mkdir(parents=True, exist_ok=True)

            with log_path.open("a", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
                f.write("\n")

            logger.info("Logged event to %s", log_path)
        except Exception:
            logger.exception("Failed to write log event")

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.warning("🚀 echo() triggered!")   # WARNING always shows up
        if update.effective_message:
            logger.warning("Text received: %s", update.effective_message.text)
        else:
            logger.warning("No text in message")
        msg = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        # Only process if it's text (this handler is already text-only, but be safe)
        text = msg.text if msg else None
        if text is None:
            return

        payload = {
            "user_id": user.id if user else None,
            "chat_id": chat.id if chat else None,
            "chat_type": chat.type if chat else None,
            "text": text,
        }
        logger.info("MSG %s", payload)
        self._log_event(payload)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id not in self.registered_users:
            return await update.message.reply_text("⚠️ Please register first by contacting the admin.")

        msg = """🤖 **Realtime Report Bot**

*Deposit Channel Distribution* (Specific date)
• `/dist a <YYYYMMDD>` : Distribution for all countries
• `/dist <COUNTRY> <YYYYMMDD>` : Distribution for one country (e.g., `/dist TH 20250901`)

*Acquisition Performance* (Rolling 3 days)
• `/apf a` : Acquisition data for all countries
• `/apf <COUNTRY>` : Data for a specific country (e.g., `/apf TH`)

*Deposit Performance* (Rolling 3 days)
• `/dpf a` : Deposit data for all countries
• `/dpf <COUNTRY>` : Data for a specific country (e.g., `/dpf PH`)

*📍 Supported Countries:* TH, PH, BD, PK, ID

*ℹ️ Data Scope:*
• *Timezone:* GMT+7
• *Data Update:* Near real-time"""
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    async def apf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # self._log_event({
        # **self._base_payload(update),
        # "event": "command",
        # "command": update.effective_message.text,   # logs "/help" or "/start"
        # })

        user = update.effective_user
        if not user or user.id not in self.registered_users:
            return await update.message.reply_text("⚠️ Please register first by contacting the admin.")
        
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
                f"⏰ Data Cutoff: Data up to {current_time} (GMT+7) for each day \n"
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
        user = update.effective_user
        if not user or user.id not in self.registered_users:
            return await update.message.reply_text("⚠️ Please register first by contacting the admin.")
        # self._log_event({
        # **self._base_payload(update),
        # "event": "command",
        # "command": update.effective_message.text,   # logs "/help" or "/start"
        # })
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
        # self._log_event({
        # **self._base_payload(update),
        # "event": "command",
        # "command": update.effective_message.text,   # logs "/help" or "/start"
        # })

        user = update.effective_user
        if not user or user.id not in self.registered_users:
            return await update.message.reply_text("⚠️ Please register first by contacting the admin.")
        
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
                f"⏰ Data Cutoff: Data up to {current_time} (GMT+7) for each day \n"
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
        # application.add_handler(MessageHandler("who", self.who_command))  # <-- add this

        application.add_handler(CommandHandler("register_now", self.register_now))
        application.add_handler(CommandHandler("start", self.start_command))

        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("apf", self.apf_command))
        application.add_handler(CommandHandler("dist", self.dist_command))
        application.add_handler(CommandHandler("dpf", self.dpf_command))

        application.add_handler(CommandHandler("admin_create_link", self.admin_create_link))

        # Catch-all for logging all invalid messages
        application.add_handler(MessageHandler(filters.ALL, self.echo), group=1)

        application.run_polling(poll_interval=2.0, timeout=50)

if __name__ == "__main__":
    bot = RealTimeBot()
    bot.run()