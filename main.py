# =============================================================================
#
#   NL-bot-V3  |  discord.py  |  Single-file bot
#   Run with:  python main.py
#
# =============================================================================

# ── Imports ───────────────────────────────────────────────────────────────────
import discord
from discord.ext import commands, tasks
from discord import app_commands

import os
import json
import math
import random
import asyncio
import datetime
import aiohttp

# =============================================================================
#  TOKEN  —  paste your bot token below
# =============================================================================

TOKEN = "ur discord bot token here"

# =============================================================================
#  SECTION 1 — CONFIG
# =============================================================================

PREFIX = "?"

EMBED_COLOR   = 0x5865F2
SUCCESS_COLOR = 0x57F287
ERROR_COLOR   = 0xED4245
WARNING_COLOR = 0xFEE75C

# ── Staff Role IDs ─────────────────────────────────────────────────────────────
OWNER_ROLE_ID     = 1496245215936118784
ADMIN_ROLE_ID     = 1496246480267383007
MODERATOR_ROLE_ID = 1496246562777469149
BOT_ROLE_ID       = 1496263911345885345

# ── Base Role ──────────────────────────────────────────────────────────────────
MEMBER_ROLE_ID = 1496246646303096914

# ── Level Roles { level: role_id } — REPLACE mode ─────────────────────────────
LEVEL_ROLES = {
    5:   1496264389282758787,
    10:  1496287876860870716,
    20:  1496287887023411221,
    30:  1496287890488033360,
    45:  1496287891205263452,
    60:  1496287892400505004,
    75:  1496287983031025674,
    100: 1496288071795216505,
}

# ── Channel IDs ────────────────────────────────────────────────────────────────
SELFROLE_CHANNEL_ID  = 1496547554261864590
RULES_CHANNEL_ID     = 1496248348523499560   # #regels channel
LOG_CHANNEL_ID       = 1496652154373410856   # hardcoded log channel
MH_TICKET_CHANNEL_ID = 1496820438737621112   # mental health ticket panel
GEN_TICKET_CHANNEL_ID= 1496820466881659020   # general ticket panel

# ── Bot Message Redirect ───────────────────────────────────────────────────────
REDIRECT_BOT_ID        = 302050872383242240    # bot whose messages we intercept
REDIRECT_SOURCE_CH_ID  = 1496276022973304912   # channel to watch
REDIRECT_TARGET_CH_ID  = 1496313264987050067   # channel to forward into

# ── Self-Role Data ────────────────────────────────────────────────────────────
LANGUAGE_ROLES = [
    ("🇳🇱 Dutch",         1496552165999771698),
    ("🇬🇧 English",       1496552180994281482),
    ("🇩🇪 German",        1496552184031219873),
    ("🇫🇷 French",        1496621285168648286),
    ("🌍 International",  1496552189848715274),
]
ACTIVITY_ROLES = [
    ("😴 Sleep Schedule", 1496552593932157052),
    ("🐺 Night Animal",   1496552594821353684),
    ("☀️ Morning Guy",    1496552595622330559),
]
NOTIFICATION_ROLES = [
    ("🔔 All Notifications",  1496552596310331643),
    ("📢 Announcements Only", 1496552597631406090),
    ("🎁 Giveaways",          1496552598600159252),
    ("🎉 Events",             1496553039061057726),
    ("🚨 Important Updates",  1496553039526625311),
    ("🚫 No Pings",           1496553040516485240),
    ("Bump",                  1496553044182171828),
]
AGE_ROLES = [
    ("16–18", 1496553040784916501),
    ("18–30", 1496553041900470457),
    ("30+",   1496553042818891787),
]

# ── Leveling ───────────────────────────────────────────────────────────────────
XP_PER_MESSAGE_MIN  = 15
XP_PER_MESSAGE_MAX  = 25
XP_COOLDOWN_SECONDS = 60
XP_PER_VOICE_MINUTE = 10

# ── Economy ────────────────────────────────────────────────────────────────────
DAILY_MIN           = 200
DAILY_MAX           = 400
DAILY_COOLDOWN_H    = 24
WORK_MIN            = 50
WORK_MAX            = 150
WORK_COOLDOWN_H     = 1
STEAL_SUCCESS_RATE  = 0.40
STEAL_PENALTY_RATE  = 0.25
STEAL_COOLDOWN_H    = 1

# ── Auto-mod ───────────────────────────────────────────────────────────────────
SPAM_THRESHOLD      = 5
SPAM_WINDOW_SECONDS = 5

# =============================================================================
#  SECTION 2 — PERMISSION HELPERS
# =============================================================================

def has_owner(member: discord.Member) -> bool:
    return any(r.id == OWNER_ROLE_ID for r in member.roles)

def has_admin(member: discord.Member) -> bool:
    return any(r.id in (OWNER_ROLE_ID, ADMIN_ROLE_ID) for r in member.roles)

def has_mod(member: discord.Member) -> bool:
    return any(r.id in (OWNER_ROLE_ID, ADMIN_ROLE_ID, MODERATOR_ROLE_ID)
               for r in member.roles)

def require_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if has_admin(interaction.user):
            return True
        await interaction.response.send_message(
            embed=make_embed("❌ Access Denied",
                "You need the **Admin** or **Owner** role.", ERROR_COLOR),
            ephemeral=True)
        return False
    return app_commands.check(predicate)

def require_mod():
    async def predicate(interaction: discord.Interaction) -> bool:
        if has_mod(interaction.user):
            return True
        await interaction.response.send_message(
            embed=make_embed("❌ Access Denied",
                "You need the **Moderator** role or higher.", ERROR_COLOR),
            ephemeral=True)
        return False
    return app_commands.check(predicate)

# =============================================================================
#  SECTION 3 — DATABASE HELPERS
# =============================================================================

DB_PATH = "database.json"

def load_db() -> dict:
    if not os.path.exists(DB_PATH):
        empty = {"guilds": {}}
        save_db(empty)
        return empty
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db: dict) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def get_guild(db: dict, guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in db["guilds"]:
        db["guilds"][gid] = {
            "config": {
                "log_channel":     LOG_CHANNEL_ID,   # hardcoded default
                "welcome_channel": None,
                "goodbye_channel": None,
                "levelup_channel": None,
                "welcome_message": "Welcome {mention} to **{server}**!",
                "goodbye_message": "**{user}** has left the server.",
                "automod_enabled": False,
                "banned_words":    [],
            },
            "users":          {},
            "xp_multipliers": {},
            "tickets":        {},
            "giveaways":      {},
        }
    return db["guilds"][gid]

def get_user(db: dict, guild_id: int, user_id: int) -> dict:
    guild = get_guild(db, guild_id)
    uid   = str(user_id)
    if uid not in guild["users"]:
        guild["users"][uid] = {
            "xp": 0, "level": 0, "coins": 0,
            "last_xp": 0, "last_daily": 0,
            "last_work": 0, "last_steal": 0,
        }
    return guild["users"][uid]

def current_level(xp: int) -> int:
    return int(0.1 * math.sqrt(xp))

def xp_for_level(level: int) -> int:
    return (level * 10) ** 2

def make_embed(title="", description="", color=EMBED_COLOR,
               footer="NL-bot-V3") -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.set_footer(text=footer)
    e.timestamp = datetime.datetime.utcnow()
    return e

# =============================================================================
#  SECTION 4 — BOT SETUP
# =============================================================================

intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.voice_states    = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# =============================================================================
#  SECTION 5 — PERSISTENT VIEWS
#  All views with custom_id survive bot restarts.
# =============================================================================

# ── Verification View ──────────────────────────────────────────────────────────
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ I Accept", style=discord.ButtonStyle.success,
                       custom_id="verify_accept")
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        role = interaction.guild.get_role(MEMBER_ROLE_ID)
        if not role:
            return await interaction.response.send_message(
                "❌ Member role not found. Contact an admin.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message(
                "✅ Je bent al geverifieerd!", ephemeral=True)
        await interaction.user.add_roles(role, reason="Accepted rules")
        await interaction.response.send_message(
            f"✅ Je bent geverifieerd en hebt nu toegang tot de server!", ephemeral=True)

        # Log the verification
        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            e = make_embed("✅ Lid Geverifieerd", color=SUCCESS_COLOR)
            e.add_field(name="Gebruiker",
                        value=f"{interaction.user.mention} (`{interaction.user}`)")
            e.add_field(name="Tijdstip",
                        value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>")
            e.set_thumbnail(url=interaction.user.display_avatar.url)
            e.set_footer(text=f"User ID: {interaction.user.id}")
            await log_ch.send(embed=e)


# ── Self-Role Select (reusable) ────────────────────────────────────────────────
class SelfRoleSelect(discord.ui.Select):
    def __init__(self, category: str, roles: list,
                 exclusive: bool, placeholder: str):
        self.category  = category
        self.exclusive = exclusive
        self.role_ids  = [r[1] for r in roles]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1 if exclusive else len(roles),
            options=[discord.SelectOption(label=n, value=str(rid)) for n, rid in roles],
            custom_id=f"selfrole_{category}",
        )

    async def callback(self, interaction: discord.Interaction):
        selected = [int(v) for v in self.values]
        if self.exclusive:
            old = [r for r in interaction.user.roles if r.id in self.role_ids]
            if old:
                await interaction.user.remove_roles(*old, reason="Self-role swap")
        added = []
        for rid in selected:
            role = interaction.guild.get_role(rid)
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role, reason="Self-role")
                added.append(role.name)
        msg = f"✅ Rollen bijgewerkt: **{', '.join(added)}**" if added else "✅ Al up-to-date."
        await interaction.response.send_message(msg, ephemeral=True)


class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect("language", LANGUAGE_ROLES, False,
                                     "🌍 Kies je taalrol(len)..."))

class ActivityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect("activity", ACTIVITY_ROLES, True,
                                     "🕒 Kies je activiteitsrol..."))

class NotificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect("notification", NOTIFICATION_ROLES, True,
                                     "🔔 Kies je notificatierol..."))

class AgeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect("age", AGE_ROLES, True,
                                     "🎂 Kies je leeftijdsrol..."))


# ── Ticket Views ───────────────────────────────────────────────────────────────
class CloseTicketView(discord.ui.View):
    """Persistent close button inside every ticket channel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket Sluiten", style=discord.ButtonStyle.danger,
                       custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction,
                           button: discord.ui.Button):
        # Allow Mod+ OR the ticket creator (channel named ticket-username)
        user_slug = interaction.user.name.lower().replace(" ", "-")
        is_creator = interaction.channel.name.endswith(user_slug)
        if not has_mod(interaction.user) and not is_creator:
            return await interaction.response.send_message(
                "❌ Alleen medewerkers of de opener kunnen dit ticket sluiten.",
                ephemeral=True)
        await interaction.response.send_message(
            "🔒 Ticket wordt gesloten in **5 seconden**...")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket gesloten door {interaction.user}")


class MHTicketOpenView(discord.ui.View):
    """Button panel posted in the mental health ticket channel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🧠 Open Mental Health Ticket",
                       style=discord.ButtonStyle.primary,
                       custom_id="open_mh_ticket")
    async def open_mh(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        await _create_ticket(interaction, kind="mh")


class GenTicketOpenView(discord.ui.View):
    """Button panel posted in the general ticket channel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open General Ticket",
                       style=discord.ButtonStyle.secondary,
                       custom_id="open_gen_ticket")
    async def open_gen(self, interaction: discord.Interaction,
                       button: discord.ui.Button):
        await _create_ticket(interaction, kind="gen")


async def _create_ticket(interaction: discord.Interaction, kind: str):
    """Shared logic to create a private ticket channel."""
    guild = interaction.guild
    user  = interaction.user

    # Check if user already has an open ticket
    slug      = user.name.lower().replace(" ", "-")
    chan_name = f"ticket-{slug}"
    existing  = discord.utils.get(guild.text_channels, name=chan_name)
    if existing:
        return await interaction.response.send_message(
            f"❌ Je hebt al een open ticket: {existing.mention}", ephemeral=True)

    # Build permission overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user:               discord.PermissionOverwrite(read_messages=True,
                                                        send_messages=True,
                                                        attach_files=True),
    }
    for rid in (OWNER_ROLE_ID, ADMIN_ROLE_ID, MODERATOR_ROLE_ID):
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True)

    ch = await guild.create_text_channel(
        name=chan_name, overwrites=overwrites,
        reason=f"Ticket geopend door {user}")

    if kind == "mh":
        title = "🧠 Mental Health Ticket"
        desc  = (f"{user.mention} — welkom. Je bent in een veilige ruimte.\n\n"
                 "Een medewerker zal zo snel mogelijk contact met je opnemen.\n"
                 "Gebruik de knop hieronder om het ticket te sluiten als je klaar bent.")
        color = 0x9B59B6
    else:
        title = "🎫 General Support Ticket"
        desc  = (f"{user.mention} — bedankt voor het openen van een ticket!\n\n"
                 "Beschrijf je vraag of probleem en een medewerker helpt je snel.\n"
                 "Gebruik de knop hieronder om het ticket te sluiten als je klaar bent.")
        color = EMBED_COLOR

    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_footer(text="NL-bot-V3 | Ticket systeem")
    embed.timestamp = datetime.datetime.utcnow()

    await ch.send(embed=embed, view=CloseTicketView())
    await interaction.response.send_message(
        f"✅ Ticket aangemaakt: {ch.mention}", ephemeral=True)

    # Log ticket creation
    log_ch = guild.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        e = make_embed(f"🎫 Ticket Geopend ({kind.upper()})", color=EMBED_COLOR)
        e.add_field(name="Gebruiker", value=f"{user.mention} (`{user}`)")
        e.add_field(name="Kanaal",    value=ch.mention)
        await log_ch.send(embed=e)

# =============================================================================
#  SECTION 6 — MODERATION COG
#  Admin+: ban, unban, kick
#  Mod+:   mute, unmute, warn, automod
# =============================================================================

class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot):
        self.bot = bot

    async def _audit_log(self, guild: discord.Guild, action: str,
                         mod: discord.Member, target, reason: str):
        """Send a formatted action embed to the log channel."""
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if not ch:
            return
        e = make_embed(f"🔨 {action}", color=ERROR_COLOR)
        e.add_field(name="Gebruiker",  value=f"{target.mention} (`{target}`)", inline=True)
        e.add_field(name="Moderator",  value=mod.mention,                      inline=True)
        e.add_field(name="Reden",      value=reason or "Geen reden opgegeven", inline=False)
        e.set_footer(text=f"User ID: {target.id}")
        await ch.send(embed=e)

    @app_commands.command(name="ban", description="Ban a member. (Admin+)")
    @require_admin()
    async def ban(self, interaction: discord.Interaction,
                  member: discord.Member, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message(
                embed=make_embed("❌ Error",
                    "You cannot ban someone with an equal or higher role.",
                    ERROR_COLOR), ephemeral=True)
        await member.ban(reason=reason)
        await interaction.response.send_message(embed=make_embed(
            "🔨 Banned",
            f"**{member}** has been banned.\n📝 Reason: {reason}", ERROR_COLOR))
        await self._audit_log(interaction.guild, "Ban", interaction.user, member, reason)

    @app_commands.command(name="unban", description="Unban a user by ID. (Admin+)")
    @require_admin()
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(embed=make_embed(
                "✅ Unbanned", f"**{user}** has been unbanned.", SUCCESS_COLOR))
        except Exception:
            await interaction.response.send_message(embed=make_embed(
                "❌ Error", "Could not find or unban that user ID.", ERROR_COLOR),
                ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member. (Admin+)")
    @require_admin()
    async def kick(self, interaction: discord.Interaction,
                   member: discord.Member, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message(
                embed=make_embed("❌ Error",
                    "You cannot kick someone with an equal or higher role.",
                    ERROR_COLOR), ephemeral=True)
        await member.kick(reason=reason)
        await interaction.response.send_message(embed=make_embed(
            "👢 Kicked",
            f"**{member}** has been kicked.\n📝 Reason: {reason}", WARNING_COLOR))
        await self._audit_log(interaction.guild, "Kick", interaction.user, member, reason)

    @app_commands.command(name="mute", description="Timeout a member. (Mod+)")
    @require_mod()
    async def mute(self, interaction: discord.Interaction,
                   member: discord.Member, minutes: int = 10,
                   reason: str = "No reason provided."):
        if not has_admin(interaction.user) and has_admin(member):
            return await interaction.response.send_message(
                embed=make_embed("❌ Error",
                    "Moderators cannot mute Admins or Owners.", ERROR_COLOR),
                ephemeral=True)
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(embed=make_embed(
            "🔇 Muted",
            f"**{member}** muted for **{minutes}m**.\n📝 Reason: {reason}",
            WARNING_COLOR))
        await self._audit_log(interaction.guild, f"Mute ({minutes}m)",
                               interaction.user, member, reason)

    @app_commands.command(name="unmute", description="Remove a timeout. (Mod+)")
    @require_mod()
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(embed=make_embed(
            "🔊 Unmuted", f"**{member}**'s timeout removed.", SUCCESS_COLOR))

    @app_commands.command(name="warn", description="Warn a member via DM. (Mod+)")
    @require_mod()
    async def warn(self, interaction: discord.Interaction,
                   member: discord.Member, reason: str = "No reason provided."):
        try:
            await member.send(embed=make_embed(
                "⚠️ Warning",
                f"**Server:** {interaction.guild.name}\n📝 **Reason:** {reason}",
                WARNING_COLOR))
        except discord.Forbidden:
            pass
        await interaction.response.send_message(embed=make_embed(
            "⚠️ Warning Issued",
            f"**{member}** warned.\n📝 Reason: {reason}", WARNING_COLOR))
        await self._audit_log(interaction.guild, "Warning",
                               interaction.user, member, reason)

    @app_commands.command(name="automod",
                          description="Enable/disable automod or add a banned word. (Admin+)")
    @require_admin()
    async def automod(self, interaction: discord.Interaction,
                      enabled: bool, banned_word: str = ""):
        db    = load_db()
        guild = get_guild(db, interaction.guild_id)
        guild["config"]["automod_enabled"] = enabled
        if banned_word and banned_word not in guild["config"]["banned_words"]:
            guild["config"]["banned_words"].append(banned_word)
        save_db(db)
        status = "enabled ✅" if enabled else "disabled ❌"
        await interaction.response.send_message(embed=make_embed(
            "🛡️ Automod", f"Automod is now **{status}**.", SUCCESS_COLOR))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        db    = load_db()
        guild = get_guild(db, message.guild.id)
        if not guild["config"]["automod_enabled"]:
            return
        content = message.content.lower()
        for word in guild["config"]["banned_words"]:
            if word.lower() in content:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} ⚠️ Banned word detected.",
                    delete_after=5)
                return

# =============================================================================
#  SECTION 7 — LEVELING COG
# =============================================================================

class LevelingCog(commands.Cog, name="Leveling"):
    def __init__(self, bot):
        self.bot = bot
        self.voice_xp_task.start()

    def cog_unload(self):
        self.voice_xp_task.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        db   = load_db()
        user = get_user(db, message.guild.id, message.author.id)
        now  = datetime.datetime.utcnow().timestamp()

        if now - user["last_xp"] < XP_COOLDOWN_SECONDS:
            return

        guild_doc       = get_guild(db, message.guild.id)
        multiplier      = 1.0
        member_role_ids = [str(r.id) for r in message.author.roles]
        for rid, mult in guild_doc["xp_multipliers"].items():
            if rid in member_role_ids:
                multiplier = max(multiplier, mult)

        xp_gain       = int(random.randint(XP_PER_MESSAGE_MIN,
                                           XP_PER_MESSAGE_MAX) * multiplier)
        old_level     = user["level"]
        user["xp"]   += xp_gain
        user["last_xp"] = now
        new_level     = current_level(user["xp"])
        user["level"] = new_level
        save_db(db)

        if new_level > old_level:
            await self._handle_levelup(message.guild, message.author, new_level)

        await bot.process_commands(message)

    async def _handle_levelup(self, guild: discord.Guild,
                               member: discord.Member, new_level: int):
        # Replace level role
        all_lvl_ids = set(LEVEL_ROLES.values())
        to_remove   = [r for r in member.roles if r.id in all_lvl_ids]
        if to_remove:
            await member.remove_roles(*to_remove, reason="Level role replace")

        earned_id = None
        for lvl in sorted(LEVEL_ROLES.keys()):
            if new_level >= lvl:
                earned_id = LEVEL_ROLES[lvl]

        if earned_id:
            role = guild.get_role(earned_id)
            if role:
                await member.add_roles(role, reason=f"Level {new_level} reward")

        db        = load_db()
        guild_doc = get_guild(db, guild.id)
        ch_id     = guild_doc["config"].get("levelup_channel")
        channel   = guild.get_channel(ch_id) if ch_id else None
        if not channel:
            return

        embed = make_embed(
            "⭐ Level Up!",
            f"🎉 {member.mention} reached **Level {new_level}**!\n"
            + (f"🏆 New role: <@&{earned_id}>" if earned_id else ""),
            SUCCESS_COLOR,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @tasks.loop(minutes=1)
    async def voice_xp_task(self):
        for guild in bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot or member.voice.self_deaf or member.voice.afk:
                        continue
                    db        = load_db()
                    user      = get_user(db, guild.id, member.id)
                    old_level = user["level"]
                    user["xp"] += XP_PER_VOICE_MINUTE
                    new_level  = current_level(user["xp"])
                    user["level"] = new_level
                    save_db(db)
                    if new_level > old_level:
                        await self._handle_levelup(guild, member, new_level)

    @voice_xp_task.before_loop
    async def before_voice_xp(self):
        await bot.wait_until_ready()

    async def _send_rank(self, ctx_or_i, member: discord.Member):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        lvl  = user["level"]
        xp   = user["xp"]
        curr = xp - xp_for_level(lvl)
        need = xp_for_level(lvl + 1) - xp_for_level(lvl)
        filled = int((curr / max(need, 1)) * 20)
        bar    = "█" * filled + "░" * (20 - filled)
        embed  = make_embed(
            f"📊 {member.display_name}'s Rank",
            f"**Level:** {lvl}\n**XP:** {curr:,} / {need:,}\n`{bar}`\n**Total XP:** {xp:,}",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if isinstance(ctx_or_i, discord.Interaction):
            await ctx_or_i.response.send_message(embed=embed)
        else:
            await ctx_or_i.send(embed=embed)

    @commands.command(name="rank")
    async def rank_prefix(self, ctx, member: discord.Member = None):
        await self._send_rank(ctx, member or ctx.author)

    @app_commands.command(name="rank", description="Check your rank and XP.")
    async def rank_slash(self, interaction: discord.Interaction,
                         member: discord.Member = None):
        await self._send_rank(interaction, member or interaction.user)

    async def _send_lb(self, ctx_or_i):
        guild = (ctx_or_i.guild if isinstance(ctx_or_i, discord.Interaction)
                 else ctx_or_i.guild)
        db    = load_db()
        users = get_guild(db, guild.id)["users"]
        top   = sorted(users.items(), key=lambda x: x[1]["xp"], reverse=True)[:10]
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        lines  = [
            f"{medals[i]} **{(guild.get_member(int(uid)) or type('', (), {'display_name': f'User {uid}'})()).display_name}**"
            f" — Lv.{d['level']} ({d['xp']:,} XP)"
            for i, (uid, d) in enumerate(top)
        ]
        embed = make_embed("🏆 XP Leaderboard", "\n".join(lines) or "No data yet.")
        if isinstance(ctx_or_i, discord.Interaction):
            await ctx_or_i.response.send_message(embed=embed)
        else:
            await ctx_or_i.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb"])
    async def lb_prefix(self, ctx):
        await self._send_lb(ctx)

    @app_commands.command(name="leaderboard", description="Top 10 XP leaderboard.")
    async def lb_slash(self, interaction: discord.Interaction):
        await self._send_lb(interaction)

    @app_commands.command(name="setlevelchannel",
                          description="Set the level-up announcement channel. (Admin+)")
    @require_admin()
    async def setlevelchannel(self, interaction: discord.Interaction,
                               channel: discord.TextChannel):
        db = load_db()
        get_guild(db, interaction.guild_id)["config"]["levelup_channel"] = channel.id
        save_db(db)
        await interaction.response.send_message(embed=make_embed(
            "✅ Level Channel Set",
            f"Level-up announcements → {channel.mention}", SUCCESS_COLOR))

    @app_commands.command(name="addmultiplier",
                          description="Set an XP multiplier for a role. (Admin+)")
    @require_admin()
    async def addmultiplier(self, interaction: discord.Interaction,
                             role: discord.Role, multiplier: float):
        db = load_db()
        get_guild(db, interaction.guild_id)["xp_multipliers"][str(role.id)] = multiplier
        save_db(db)
        await interaction.response.send_message(embed=make_embed(
            "✅ Multiplier Set",
            f"{role.mention} → **{multiplier}x** XP", SUCCESS_COLOR))

# =============================================================================
#  SECTION 8 — ECONOMY COG
# =============================================================================

class EconomyCog(commands.Cog, name="Economy"):
    def __init__(self, bot):
        self.bot = bot

    async def _send(self, c, embed):
        if isinstance(c, discord.Interaction):
            await c.response.send_message(embed=embed)
        else:
            await c.send(embed=embed)

    # balance
    async def _balance(self, c, member):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        await self._send(c, make_embed(
            f"💰 {member.display_name}'s Balance",
            f"**{user['coins']:,}** coins", EMBED_COLOR))

    @commands.command(name="balance", aliases=["bal"])
    async def balance_prefix(self, ctx, member: discord.Member = None):
        await self._balance(ctx, member or ctx.author)

    @app_commands.command(name="balance", description="Check your coin balance.")
    async def balance_slash(self, interaction: discord.Interaction,
                            member: discord.Member = None):
        await self._balance(interaction, member or interaction.user)

    # daily
    async def _daily(self, c, member):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        now  = datetime.datetime.utcnow().timestamp()
        cd   = DAILY_COOLDOWN_H * 3600
        if now - user["last_daily"] < cd:
            left = int(cd - (now - user["last_daily"]))
            h, m = divmod(left // 60, 60)
            return await self._send(c, make_embed("⏳ Cooldown",
                f"Come back in **{h}h {m}m**.", WARNING_COLOR))
        reward            = random.randint(DAILY_MIN, DAILY_MAX)
        user["coins"]    += reward
        user["last_daily"] = now
        save_db(db)
        await self._send(c, make_embed("🎁 Daily Reward",
            f"You claimed **{reward:,}** coins!\nBalance: **{user['coins']:,}**",
            SUCCESS_COLOR))

    @commands.command(name="daily")
    async def daily_prefix(self, ctx):
        await self._daily(ctx, ctx.author)

    @app_commands.command(name="daily", description="Claim your daily reward.")
    async def daily_slash(self, interaction: discord.Interaction):
        await self._daily(interaction, interaction.user)

    # work
    WORK_MSGS = [
        "You fixed bugs and earned", "You delivered packages and earned",
        "You walked dogs and earned", "You streamed games and earned",
    ]

    async def _work(self, c, member):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        now  = datetime.datetime.utcnow().timestamp()
        cd   = WORK_COOLDOWN_H * 3600
        if now - user["last_work"] < cd:
            left = int(cd - (now - user["last_work"]))
            return await self._send(c, make_embed("⏳ Tired",
                f"Rest for **{left // 60} more minute(s)**.", WARNING_COLOR))
        reward          = random.randint(WORK_MIN, WORK_MAX)
        user["coins"]  += reward
        user["last_work"] = now
        save_db(db)
        await self._send(c, make_embed("💼 Work Done",
            f"{random.choice(self.WORK_MSGS)} **{reward:,}** coins!\n"
            f"Balance: **{user['coins']:,}**", SUCCESS_COLOR))

    @commands.command(name="work")
    async def work_prefix(self, ctx):
        await self._work(ctx, ctx.author)

    @app_commands.command(name="work", description="Work to earn coins.")
    async def work_slash(self, interaction: discord.Interaction):
        await self._work(interaction, interaction.user)

    # coinflip
    async def _coinflip(self, c, member, amount: int):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        if amount <= 0 or user["coins"] < amount:
            return await self._send(c, make_embed("❌ Invalid",
                "Not enough coins.", ERROR_COLOR))
        if random.choice([True, False]):
            user["coins"] += amount
            msg, color = f"🪙 Heads! You won **{amount:,}** coins!", SUCCESS_COLOR
        else:
            user["coins"] -= amount
            msg, color = f"🪙 Tails! You lost **{amount:,}** coins.", ERROR_COLOR
        save_db(db)
        await self._send(c, make_embed("🎰 Coin Flip",
            f"{msg}\nBalance: **{user['coins']:,}**", color))

    @commands.command(name="coinflip", aliases=["cf"])
    async def cf_prefix(self, ctx, amount: int):
        await self._coinflip(ctx, ctx.author, amount)

    @app_commands.command(name="coinflip", description="Bet on heads or tails.")
    async def cf_slash(self, interaction: discord.Interaction, amount: int):
        await self._coinflip(interaction, interaction.user, amount)

    # slots
    SYMBOLS = ["🍒", "🍋", "🍊", "⭐", "💎", "7️⃣"]

    async def _slots(self, c, member, amount: int):
        db   = load_db()
        user = get_user(db, member.guild.id, member.id)
        if amount <= 0 or user["coins"] < amount:
            return await self._send(c, make_embed("❌ Invalid",
                "Not enough coins.", ERROR_COLOR))
        reels = [random.choice(self.SYMBOLS) for _ in range(3)]
        line  = " | ".join(reels)
        if reels[0] == reels[1] == reels[2]:
            mult = 10 if reels[0] == "💎" else 5
            user["coins"] += amount * mult
            msg, color = f"🎉 JACKPOT! +**{amount * mult:,}** coins!", SUCCESS_COLOR
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            user["coins"] += amount // 2
            msg, color = f"🙂 Two in a row! +**{amount // 2:,}** coins.", WARNING_COLOR
        else:
            user["coins"] -= amount
            msg, color = f"😔 No match. -**{amount:,}** coins.", ERROR_COLOR
        save_db(db)
        await self._send(c, make_embed("🎰 Slots",
            f"[ {line} ]\n\n{msg}\nBalance: **{user['coins']:,}**", color))

    @commands.command(name="slots")
    async def slots_prefix(self, ctx, amount: int):
        await self._slots(ctx, ctx.author, amount)

    @app_commands.command(name="slots", description="Spin the slot machine.")
    async def slots_slash(self, interaction: discord.Interaction, amount: int):
        await self._slots(interaction, interaction.user, amount)

    # steal
    async def _steal(self, c, member, target: discord.Member):
        if target.id == member.id or target.bot:
            return await self._send(c, make_embed("❌ Invalid",
                "Can't steal from yourself or a bot.", ERROR_COLOR))
        db       = load_db()
        user     = get_user(db, member.guild.id, member.id)
        tgt_user = get_user(db, target.guild.id, target.id)
        now      = datetime.datetime.utcnow().timestamp()
        cd       = STEAL_COOLDOWN_H * 3600
        if now - user["last_steal"] < cd:
            left = int(cd - (now - user["last_steal"]))
            return await self._send(c, make_embed("⏳ Cooldown",
                f"Wait **{left // 60} more minute(s)**.", WARNING_COLOR))
        user["last_steal"] = now
        if tgt_user["coins"] <= 0:
            save_db(db)
            return await self._send(c, make_embed("💸 Empty Pockets",
                f"{target.display_name} has no coins!", WARNING_COLOR))
        if random.random() < STEAL_SUCCESS_RATE:
            stolen             = max(1, int(tgt_user["coins"] * 0.10))
            tgt_user["coins"] -= stolen
            user["coins"]     += stolen
            msg, color = f"✅ Stole **{stolen:,}** coins from {target.mention}!", SUCCESS_COLOR
        else:
            penalty        = max(1, int(user["coins"] * STEAL_PENALTY_RATE))
            user["coins"]  = max(0, user["coins"] - penalty)
            msg, color = f"❌ Caught! Paid **{penalty:,}** coin fine.", ERROR_COLOR
        save_db(db)
        await self._send(c, make_embed("🦝 Steal", msg, color))

    @commands.command(name="steal")
    async def steal_prefix(self, ctx, target: discord.Member):
        await self._steal(ctx, ctx.author, target)

    @app_commands.command(name="steal", description="Try to steal coins from someone.")
    async def steal_slash(self, interaction: discord.Interaction,
                          target: discord.Member):
        await self._steal(interaction, interaction.user, target)

    # richlist
    async def _richlist(self, c):
        guild  = c.guild if isinstance(c, discord.Interaction) else c.guild
        db     = load_db()
        users  = get_guild(db, guild.id)["users"]
        top    = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:10]
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        lines  = [
            f"{medals[i]} **{(guild.get_member(int(uid)) or type('', (), {'display_name': f'User {uid}'})()).display_name}**"
            f" — {d['coins']:,} coins"
            for i, (uid, d) in enumerate(top)
        ]
        embed = make_embed("💰 Rich List", "\n".join(lines) or "No data yet.")
        if isinstance(c, discord.Interaction):
            await c.response.send_message(embed=embed)
        else:
            await c.send(embed=embed)

    @commands.command(name="richlist", aliases=["richest"])
    async def richlist_prefix(self, ctx):
        await self._richlist(ctx)

    @app_commands.command(name="richlist", description="Top 10 richest users.")
    async def richlist_slash(self, interaction: discord.Interaction):
        await self._richlist(interaction)

# =============================================================================
#  SECTION 9 — FUN COG
# =============================================================================

class FunCog(commands.Cog, name="Fun"):
    def __init__(self, bot):
        self.bot             = bot
        self.trivia_sessions = {}

    async def _send(self, c, embed):
        if isinstance(c, discord.Interaction):
            await c.response.send_message(embed=embed)
        else:
            await c.send(embed=embed)

    # ── joke ──────────────────────────────────────────────────────────────────
    @commands.command(name="joke")
    async def joke_prefix(self, ctx):
        await self._joke(ctx)

    @app_commands.command(name="joke", description="Get a random dad joke.")
    async def joke_slash(self, interaction: discord.Interaction):
        await self._joke(interaction)

    async def _joke(self, c):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://icanhazdadjoke.com/",
                                 headers={"Accept": "application/json"},
                                 timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        data = await r.json()
                        return await self._send(c, make_embed("😄 Dad Joke", data["joke"]))
        except Exception:
            pass
        await self._send(c, make_embed("❌ Error", "Could not fetch a joke right now.", ERROR_COLOR))

    # ── meme — FIXED with meme-api.com primary + Reddit fallbacks ────────────
    @commands.command(name="meme")
    async def meme_prefix(self, ctx):
        await self._meme(ctx)

    @app_commands.command(name="meme", description="Get a random meme.")
    async def meme_slash(self, interaction: discord.Interaction):
        await self._meme(interaction)

    async def _meme(self, c):
        """
        Source priority:
          1. meme-api.com/gimme  (primary — reliable, no auth needed)
          2. reddit.com/r/memes  (fallback 1)
          3. reddit.com/r/dankmemes (fallback 2)
        """
        headers = {"User-Agent": "NL-bot-V3/3.0 (Discord bot)"}

        async with aiohttp.ClientSession() as session:

            # ── Primary: meme-api.com ──────────────────────────────────────────
            try:
                async with session.get(
                    "https://meme-api.com/gimme",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        # meme-api returns: url, title, subreddit, ups, nsfw
                        if not data.get("nsfw", True) and data.get("url"):
                            embed = make_embed(data.get("title", "Meme"))
                            embed.set_image(url=data["url"])
                            embed.set_footer(
                                text=f"r/{data.get('subreddit', 'memes')} "
                                     f"| 👍 {data.get('ups', 0):,} | NL-bot-V3")
                            if isinstance(c, discord.Interaction):
                                return await c.response.send_message(embed=embed)
                            return await c.send(embed=embed)
            except Exception:
                pass  # fall through to Reddit

            # ── Fallback: Reddit JSON API ──────────────────────────────────────
            for sub in ["memes", "dankmemes", "me_irl"]:
                try:
                    async with session.get(
                        f"https://www.reddit.com/r/{sub}/random.json?limit=1",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=8)
                    ) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                        post = data[0]["data"]["children"][0]["data"]
                        # Skip NSFW or non-image posts
                        url = post.get("url", "")
                        if post.get("over_18") or not any(
                            url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")
                        ):
                            continue
                        embed = make_embed(post.get("title", "Meme"))
                        embed.set_image(url=url)
                        embed.set_footer(
                            text=f"r/{sub} | 👍 {post.get('ups', 0):,} | NL-bot-V3")
                        if isinstance(c, discord.Interaction):
                            return await c.response.send_message(embed=embed)
                        return await c.send(embed=embed)
                except Exception:
                    continue

        # ── All sources failed ─────────────────────────────────────────────────
        await self._send(c, make_embed(
            "😔 No Meme Found",
            "All meme sources are currently unavailable. Try again in a moment!",
            WARNING_COLOR))

    # ── rps ───────────────────────────────────────────────────────────────────
    @commands.command(name="rps")
    async def rps_prefix(self, ctx, choice: str):
        await self._rps(ctx, choice)

    @app_commands.command(name="rps", description="Rock Paper Scissors.")
    async def rps_slash(self, interaction: discord.Interaction, choice: str):
        await self._rps(interaction, choice)

    async def _rps(self, c, choice: str):
        choice  = choice.lower()
        options = ["rock", "paper", "scissors"]
        emojis  = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        if choice not in options:
            return await self._send(c, make_embed("❌ Invalid",
                "Choose rock, paper, or scissors.", ERROR_COLOR))
        bot_pick = random.choice(options)
        if choice == bot_pick:
            result, color = "🤝 Tie!", EMBED_COLOR
        elif (choice, bot_pick) in [("rock","scissors"),("paper","rock"),("scissors","paper")]:
            result, color = "🎉 You win!", SUCCESS_COLOR
        else:
            result, color = "😔 You lose!", ERROR_COLOR
        await self._send(c, make_embed("✂️ RPS",
            f"You: {emojis[choice]}  vs  Bot: {emojis[bot_pick]}\n\n**{result}**", color))

    # ── trivia ────────────────────────────────────────────────────────────────
    TRIVIA = [
        ("What is the capital of France?",          "paris"),
        ("How many sides does a hexagon have?",      "6"),
        ("What language is discord.py written in?",  "python"),
        ("What is 12 × 12?",                        "144"),
        ("Closest planet to the sun?",              "mercury"),
        ("How many bytes in a kilobyte?",            "1024"),
        ("Chemical symbol for gold?",               "au"),
        ("Who wrote Romeo and Juliet?",             "shakespeare"),
    ]

    @commands.command(name="trivia")
    async def trivia_prefix(self, ctx):
        await self._trivia(ctx)

    @app_commands.command(name="trivia", description="Answer a trivia question!")
    async def trivia_slash(self, interaction: discord.Interaction):
        await self._trivia(interaction)

    async def _trivia(self, c):
        ch_id   = c.channel.id
        channel = c.channel
        if ch_id in self.trivia_sessions:
            return await self._send(c, make_embed("⚠️ Active Trivia",
                "A trivia question is already running here!", WARNING_COLOR))
        q, a = random.choice(self.TRIVIA)
        self.trivia_sessions[ch_id] = a
        embed = make_embed("🧠 Trivia!", f"**{q}**\n\nYou have **30 seconds**!")
        if isinstance(c, discord.Interaction):
            await c.response.send_message(embed=embed)
        else:
            await c.send(embed=embed)
        def check(m):
            return (m.channel.id == ch_id and not m.author.bot
                    and m.content.lower().strip() == a)
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            del self.trivia_sessions[ch_id]
            await channel.send(embed=make_embed("✅ Correct!",
                f"🎉 {msg.author.mention} got it! Answer: **{a}**", SUCCESS_COLOR))
        except asyncio.TimeoutError:
            self.trivia_sessions.pop(ch_id, None)
            await channel.send(embed=make_embed("⏰ Time's Up!",
                f"The answer was **{a}**.", ERROR_COLOR))

# =============================================================================
#  SECTION 10 — UTILITIES COG
#  Rules/Verify, Self-Roles, Welcome/Goodbye, Polls, Tickets, Giveaways
# =============================================================================

class UtilitiesCog(commands.Cog, name="Utilities"):
    def __init__(self, bot):
        self.bot = bot
        # Register all persistent views so buttons survive restarts
        bot.add_view(VerifyView())
        bot.add_view(LanguageView())
        bot.add_view(ActivityView())
        bot.add_view(NotificationView())
        bot.add_view(AgeView())
        bot.add_view(CloseTicketView())
        bot.add_view(MHTicketOpenView())
        bot.add_view(GenTicketOpenView())

    # ── /setuprules — post Dutch rules embed with verify button ───────────────
    @app_commands.command(name="setuprules",
                          description="Post het regels-embed met verificatieknop. (Admin+)")
    @require_admin()
    async def setuprules(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(RULES_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(
                "❌ Regelkanaal niet gevonden.", ephemeral=True)

        embed = discord.Embed(
            title="📜 REGELS",
            description=(
                "@here Welkom bij **NL Oost | 18+ | Hechte Community** "
                "Lees de regels goed door voordat je meedoet.\n\n"
                "─────────────────────────────\n\n"
                "🔞 **18+ only**\n"
                "Deze server is uitsluitend voor personen van 18 jaar en ouder.\n\n"
                "🤝 **Respectvol gedrag**\n"
                "Behandel iedereen met respect. Pesten, uitschelden of discrimineren "
                "wordt niet getolereerd.\n\n"
                "🚫 **Geen spam**\n"
                "Geen herhaalde berichten, caps lock misbruik of onnodige mentions.\n\n"
                "🔗 **Geen reclame**\n"
                "Geen links naar andere servers, sociale media of producten "
                "zonder toestemming van een mod.\n\n"
                "🖼️ **Geen ongepaste content**\n"
                "Geen NSFW-content buiten aangewezen kanalen. "
                "Illegale content leidt direct tot een ban.\n\n"
                "🎙️ **Gedrag in spraakkanalen**\n"
                "Geen oorverdovende geluiden, muziek door je microfoon of treiteren.\n\n"
                "🛡️ **Luister naar de moderators**\n"
                "Beslissingen van moderators zijn definitief.\n\n"
                "🌍 **Spreek Nederlands of Engels**\n"
                "Houd gesprekken in het Nederlands of Engels.\n\n"
                "─────────────────────────────\n"
                "⚠️ Overtredingen kunnen leiden tot een waarschuwing, timeout of ban."
            ),
            color=EMBED_COLOR,
        )
        embed.set_footer(text="NL-bot-V3 | Druk op de knop om toegang te krijgen")
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message(
            f"✅ Regelembed geplaatst in {channel.mention}!", ephemeral=True)

    # ── /setuproles — post self-role dashboard ────────────────────────────────
    @app_commands.command(name="setuproles",
                          description="Post the self-role dashboard. (Admin+)")
    @require_admin()
    async def setuproles(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(SELFROLE_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(
                "❌ Self-role channel not found.", ephemeral=True)

        await channel.send(embed=discord.Embed(
            title="🌍 Language Roles",
            description="Pick the language(s) you speak. **Multi-select allowed.**\n\n"
                        + "\n".join(f"• {n}" for n, _ in LANGUAGE_ROLES),
            color=0x3498DB).set_footer(text="NL-bot-V3 | Self-Roles"),
            view=LanguageView())

        await channel.send(embed=discord.Embed(
            title="🕒 Activity / Lifestyle",
            description="Pick your vibe. **One at a time — swaps automatically.**\n\n"
                        + "\n".join(f"• {n}" for n, _ in ACTIVITY_ROLES),
            color=0x9B59B6).set_footer(text="NL-bot-V3 | Self-Roles"),
            view=ActivityView())

        await channel.send(embed=discord.Embed(
            title="🔔 Notification Roles",
            description="Choose your ping preference. **One at a time.**\n\n"
                        + "\n".join(f"• {n}" for n, _ in NOTIFICATION_ROLES),
            color=0xE67E22).set_footer(text="NL-bot-V3 | Self-Roles"),
            view=NotificationView())

        await channel.send(embed=discord.Embed(
            title="🎂 Age Roles",
            description="Pick your age group. **One at a time.**\n\n"
                        + "\n".join(f"• {n}" for n, _ in AGE_ROLES),
            color=0xE91E63).set_footer(text="NL-bot-V3 | Self-Roles"),
            view=AgeView())

        await interaction.response.send_message(
            f"✅ Self-role dashboard posted in {channel.mention}!", ephemeral=True)

    # ── /ticketsetup — post 2 ticket panels ───────────────────────────────────
    @app_commands.command(name="ticketsetup",
                          description="Post de ticket panels in beide kanalen. (Admin+)")
    @require_admin()
    async def ticketsetup(self, interaction: discord.Interaction):
        guild = interaction.guild

        # Panel 1 — Mental Health
        mh_ch = guild.get_channel(MH_TICKET_CHANNEL_ID)
        if mh_ch:
            embed_mh = discord.Embed(
                title="🧠 Mental Health Support",
                description=(
                    "Heb je het moeilijk of wil je met iemand praten?\n\n"
                    "Klik op de knop hieronder om een **privé ticket** te openen. "
                    "Onze medewerkers zijn er voor je.\n\n"
                    "🔒 Alleen jij en het staffteam kunnen het ticket zien."
                ),
                color=0x9B59B6,
            )
            embed_mh.set_footer(text="NL-bot-V3 | Ticket Systeem")
            embed_mh.timestamp = datetime.datetime.utcnow()
            await mh_ch.send(embed=embed_mh, view=MHTicketOpenView())

        # Panel 2 — General Support
        gen_ch = guild.get_channel(GEN_TICKET_CHANNEL_ID)
        if gen_ch:
            embed_gen = discord.Embed(
                title="🎫 General Support",
                description=(
                    "Heb je een vraag, probleem of wil je iets melden?\n\n"
                    "Klik op de knop hieronder om een **privé ticket** te openen. "
                    "Een medewerker helpt je zo snel mogelijk.\n\n"
                    "🔒 Alleen jij en het staffteam kunnen het ticket zien."
                ),
                color=EMBED_COLOR,
            )
            embed_gen.set_footer(text="NL-bot-V3 | Ticket Systeem")
            embed_gen.timestamp = datetime.datetime.utcnow()
            await gen_ch.send(embed=embed_gen, view=GenTicketOpenView())

        channels_posted = []
        if mh_ch:  channels_posted.append(mh_ch.mention)
        if gen_ch: channels_posted.append(gen_ch.mention)
        await interaction.response.send_message(
            f"✅ Ticket panels geplaatst in: {', '.join(channels_posted)}", ephemeral=True)

    # ── Welcome / Goodbye ──────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        db  = load_db()
        cfg = get_guild(db, member.guild.id)["config"]
        ch  = member.guild.get_channel(cfg.get("welcome_channel") or 0)
        if not ch:
            return
        msg   = cfg["welcome_message"].format(
            mention=member.mention, user=str(member), server=member.guild.name)
        embed = make_embed("👋 Welcome!", msg, SUCCESS_COLOR)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        db  = load_db()
        cfg = get_guild(db, member.guild.id)["config"]
        ch  = member.guild.get_channel(cfg.get("goodbye_channel") or 0)
        if not ch:
            return
        msg = cfg["goodbye_message"].format(user=str(member), server=member.guild.name)
        await ch.send(embed=make_embed("👋 Goodbye", msg, WARNING_COLOR))

    @app_commands.command(name="setwelcome",
                          description="Set the welcome channel. (Admin+)")
    @require_admin()
    async def setwelcome(self, interaction: discord.Interaction,
                         channel: discord.TextChannel):
        db = load_db()
        get_guild(db, interaction.guild_id)["config"]["welcome_channel"] = channel.id
        save_db(db)
        await interaction.response.send_message(embed=make_embed(
            "✅ Welcome Channel", f"→ {channel.mention}", SUCCESS_COLOR))

    @app_commands.command(name="setgoodbye",
                          description="Set the goodbye channel. (Admin+)")
    @require_admin()
    async def setgoodbye(self, interaction: discord.Interaction,
                         channel: discord.TextChannel):
        db = load_db()
        get_guild(db, interaction.guild_id)["config"]["goodbye_channel"] = channel.id
        save_db(db)
        await interaction.response.send_message(embed=make_embed(
            "✅ Goodbye Channel", f"→ {channel.mention}", SUCCESS_COLOR))

    # ── Poll ───────────────────────────────────────────────────────────────────
    @app_commands.command(name="poll", description="Create a reaction poll.")
    async def poll(self, interaction: discord.Interaction, question: str,
                   option1: str, option2: str,
                   option3: str = "", option4: str = ""):
        opts   = [o for o in [option1, option2, option3, option4] if o]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        desc   = "\n".join(f"{emojis[i]} {o}" for i, o in enumerate(opts))
        await interaction.response.send_message(embed=make_embed(f"📊 {question}", desc))
        msg = await interaction.original_response()
        for i in range(len(opts)):
            await msg.add_reaction(emojis[i])

    # ── Giveaway ───────────────────────────────────────────────────────────────
    @app_commands.command(name="giveaway",
                          description="Start a timed giveaway. (Admin+)")
    @require_admin()
    async def giveaway(self, interaction: discord.Interaction,
                       prize: str, minutes: int, winners: int = 1):
        end = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        embed = discord.Embed(
            title="🎁 Giveaway!",
            description=(
                f"**Prize:** {prize}\n**Winners:** {winners}\n"
                f"**Ends:** <t:{int(end.timestamp())}:R>\n\nReact with 🎉 to enter!"
            ),
            color=SUCCESS_COLOR,
        ).set_footer(text="NL-bot-V3 | Giveaway")
        await interaction.response.send_message("🎉 Giveaway started!")
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")
        await asyncio.sleep(minutes * 60)
        msg      = await interaction.channel.fetch_message(msg.id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users    = [u async for u in reaction.users() if not u.bot]
        if not users:
            return await interaction.channel.send("😔 No entries. Giveaway cancelled.")
        picked   = random.sample(users, min(winners, len(users)))
        mentions = ", ".join(u.mention for u in picked)
        await interaction.channel.send(embed=make_embed(
            "🎉 Giveaway Ended!",
            f"**Prize:** {prize}\n**Winner(s):** {mentions}", SUCCESS_COLOR))

# =============================================================================
#  SECTION 11 — LOGGING COG
#  All events log to hardcoded LOG_CHANNEL_ID (1496652154373410856)
# =============================================================================

class LoggingCog(commands.Cog, name="Logging"):
    def __init__(self, bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Return the hardcoded log channel."""
        return guild.get_channel(LOG_CHANNEL_ID)

    # ── Message edit ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content or not before.guild:
            return
        ch = await self._log(before.guild)
        if not ch:
            return
        e = make_embed("✏️ Bericht Bewerkt", color=WARNING_COLOR)
        e.add_field(name="Auteur",  value=before.author.mention,   inline=True)
        e.add_field(name="Kanaal",  value=before.channel.mention,  inline=True)
        e.add_field(name="Oud",     value=before.content[:1024] or "—", inline=False)
        e.add_field(name="Nieuw",   value=after.content[:1024]  or "—", inline=False)
        e.add_field(name="Link",    value=f"[Spring naar bericht]({after.jump_url})", inline=False)
        await ch.send(embed=e)

    # ── Message delete ─────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        ch = await self._log(message.guild)
        if not ch:
            return
        e = make_embed("🗑️ Bericht Verwijderd", color=ERROR_COLOR)
        e.add_field(name="Auteur",  value=message.author.mention,  inline=True)
        e.add_field(name="Kanaal",  value=message.channel.mention, inline=True)
        e.add_field(name="Inhoud",  value=message.content[:1024] or "—", inline=False)
        await ch.send(embed=e)

    # ── Member join ────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = await self._log(member.guild)
        if not ch:
            return
        e = make_embed("📥 Lid Toegetreden", color=SUCCESS_COLOR)
        e.add_field(name="Gebruiker",  value=f"{member.mention} (`{member}`)")
        e.add_field(name="Account aangemaakt",
                    value=f"<t:{int(member.created_at.timestamp())}:R>")
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=f"User ID: {member.id}")
        await ch.send(embed=e)

    # ── Member leave ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ch = await self._log(member.guild)
        if not ch:
            return
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        e = make_embed("📤 Lid Verlaten", color=WARNING_COLOR)
        e.add_field(name="Gebruiker", value=f"{member} (`{member.id}`)")
        e.add_field(name="Rollen",    value=", ".join(roles) or "Geen", inline=False)
        await ch.send(embed=e)

    # ── Ban ────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        ch = await self._log(guild)
        if not ch:
            return
        e = make_embed("🔨 Lid Gebanned", color=ERROR_COLOR)
        e.add_field(name="Gebruiker", value=f"{user} (`{user.id}`)")
        await ch.send(embed=e)

    # ── Unban ──────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        ch = await self._log(guild)
        if not ch:
            return
        e = make_embed("✅ Lid Ungebanned", color=SUCCESS_COLOR)
        e.add_field(name="Gebruiker", value=f"{user} (`{user.id}`)")
        await ch.send(embed=e)

# =============================================================================
#  SECTION 12 — REDIRECT COG
#  Watches REDIRECT_SOURCE_CH_ID for messages from REDIRECT_BOT_ID,
#  copies the text to REDIRECT_TARGET_CH_ID, then deletes the original.
# =============================================================================

class RedirectCog(commands.Cog, name="Redirect"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ── Guard 1: only fire for the specific target bot ─────────────────────
        if message.author.id != REDIRECT_BOT_ID:
            return

        # ── Guard 2: only fire in the source channel ───────────────────────────
        if message.channel.id != REDIRECT_SOURCE_CH_ID:
            return

        # ── Guard 3: never re-trigger on NL-bot-V3 itself (loop prevention) ────
        if message.author.id == self.bot.user.id:
            return

        # ── Skip if there is no text content to forward ────────────────────────
        content = message.content.strip()
        if not content:
            return

        # ── Forward text to target channel ─────────────────────────────────────
        target_ch = message.guild.get_channel(REDIRECT_TARGET_CH_ID)
        if not target_ch:
            return  # target channel not found — do nothing

        try:
            await target_ch.send(content)
        except discord.Forbidden:
            return  # missing Send Messages permission in target channel
        except discord.HTTPException:
            return  # Discord API hiccup — fail silently

        # ── Delete the original message from the source channel ────────────────
        try:
            await message.delete()
        except discord.Forbidden:
            pass  # missing Manage Messages — original stays, not a crash
        except discord.NotFound:
            pass  # already deleted somehow — fine

# =============================================================================
#  SECTION 13 — ON READY
# =============================================================================

@bot.event
async def on_ready():
    slash_count  = 0
    slash_status = ""
    try:
        synced       = await bot.tree.sync()
        slash_count  = len(synced)
        slash_status = f"synced {slash_count} command(s)"
    except Exception as e:
        slash_status = f"sync failed ({e})"

    total   = len(bot.commands) + slash_count
    db      = load_db()
    db_stat = "loaded" if os.path.exists(DB_PATH) else "created"

    print(f"\n╔{'═'*42}╗")
    print(f"║{'NL-bot-V3  |  Starting up...':^42}║")
    print(f"╚{'═'*42}╝")
    print(f" [✓] Logged in as   {bot.user} (ID: {bot.user.id})")
    print(f" [✓] Prefix         {PREFIX}")
    print(f" [✓] Database       {DB_PATH} — {db_stat}")
    print(f" [✓] Log channel    {LOG_CHANNEL_ID} (hardcoded)")
    print(f" [✓] Guilds         connected to {len(bot.guilds)} server(s)")
    print(f" [✓] Commands       {total} total registered")
    print(f" [✓] Slash cmds     {slash_status}")
    print(f"{'═'*44}")
    print(f"  NL-bot-V3 connected successfully!")
    print(f"{'═'*44}\n")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}help | /help"))

# =============================================================================
#  SECTION 14 — REGISTER COGS + RUN
# =============================================================================

async def main():
    async with bot:
        await bot.add_cog(ModerationCog(bot))
        await bot.add_cog(LevelingCog(bot))
        await bot.add_cog(EconomyCog(bot))
        await bot.add_cog(FunCog(bot))
        await bot.add_cog(UtilitiesCog(bot))
        await bot.add_cog(LoggingCog(bot))
        await bot.add_cog(RedirectCog(bot))
        try:
            await bot.start(TOKEN)
        except discord.LoginFailure:
            print("\n [✗] Connection failed — invalid TOKEN.")
            print("     Open main.py, find TOKEN = and paste your bot token.\n")
        except Exception as e:
            print(f"\n [✗] Unexpected startup error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
