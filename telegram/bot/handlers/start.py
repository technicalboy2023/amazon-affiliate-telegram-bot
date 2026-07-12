import logging

from aiogram import types
from sqlalchemy import update as sql_update

from core.container import get_container
from database.models import TelegramAccount
from database.repositories.message_repo import MessageRepository
from services.post_customizer import PostCustomizer

logger = logging.getLogger(__name__)

COMMANDS_TEXT = (
    "Commands:\n\n"
    "📋 Info:\n"
    "/help - Show this help\n"
    "/status - Current status\n"
    "/config - View all runtime settings\n"
    "/stats - Today's statistics\n"
    "/history - Recent forwarded messages\n"
    "/errors - Recent errors\n"
    "/ping - Health check\n\n"
    "⚙️ Control:\n"
    "/pause - Pause forwarding\n"
    "/stop - Stop monitoring\n"
    "/resume - Resume forwarding\n"
    "/reload - Restart monitor with updated settings\n"
    "/logout - Disconnect userbot\n\n"
    "🔗 Affiliate:\n"
    "/affiliate <tag> - Set affiliate tag\n"
    "/clear_affiliate - Clear affiliate tag\n"
    "/sources - List source channels\n"
    "/add_source <channel> - Add source channel\n"
    "/remove_source <channel> - Remove source channel\n"
    "/dest <channel> - Set destination channel\n"
    "/remove_dest - Clear destination channel\n"
    "/domain <domain> - Set Amazon domain (amazon.in/com)\n"
    "/set_delay <sec> - Set delay between forwards\n\n"
    "✂️ Customization:\n"
    "/add_replace Old➜New - Add word replacement\n"
    "/remove_replace Old - Remove replacement\n"
    "/list_replaces - View all replacements\n"
    "/add_block Word - Block posts containing word\n"
    "/remove_block Word - Remove block rule\n"
    "/list_blocks - View all block rules\n"
    "/set_header Text - Add header to posts\n"
    "/set_footer Text - Add footer to posts\n"
    "/clear_header - Remove header\n"
    "/clear_footer - Remove footer\n\n"
    "🔐 Auth:\n"
    "/login - Log in to Telegram account"
)


async def cmd_start(message: types.Message) -> None:
    await message.answer(f"Welcome to the Affiliate Bot.\n\n{COMMANDS_TEXT}")


async def cmd_help(message: types.Message) -> None:
    await message.answer(COMMANDS_TEXT)


async def cmd_status(message: types.Message) -> None:
    container = get_container()
    ss = container.settings_service
    sources = await ss.get_source_channels()
    if not sources:
        sources = container.settings.source_channels
    tag = await ss.get_affiliate_tag()
    if not tag:
        tag = container.settings.default_affiliate_tag
    domain = await ss.get("amazon_domain", "")
    if not domain:
        domain = container.settings.default_amazon_domain
    dest = await ss.get_dest_channel()
    if not dest:
        dest = container.settings.dest_channel_username or str(container.settings.dest_channel_id or "")
    cm = container.channel_monitor
    is_monitoring = bool(cm and cm._handler)
    is_paused = await cm.customizer.is_paused() if cm else False
    if is_paused:
        status_text = "paused"
    elif is_monitoring:
        status_text = "active"
    else:
        status_text = "stopped"
    userbot_connected = bool(container.userbot and container.userbot.is_connected())
    lines = [
        f"Bot: @{(await message.bot.get_me()).username}",
        f"Userbot: {'connected' if userbot_connected else 'disconnected'}",
        f"Affiliate tag: {tag or '(not set)'}",
        f"Domain: {domain}",
        f"Source channels: {', '.join(sources) if sources else '(none)'}",
        f"Destination: @{dest}" if dest else "Destination: (not set)",
        f"Monitoring: {status_text}",
    ]
    await message.answer("\n".join(lines))


async def cmd_stats(message: types.Message) -> None:
    container = get_container()
    stats = await container.stats_service.get_today_stats(user_id=container.settings.default_user_id)
    await message.answer(
        "📊 Today's Statistics:\n"
        f"Processed: {stats.get('processed', 0)}\n"
        f"Published: {stats.get('published', 0)}\n"
        f"Errors: {stats.get('errors', 0)}"
    )


async def cmd_history(message: types.Message) -> None:
    container = get_container()
    async with container.session_factory() as session:
        repo = MessageRepository(session)
        msgs = await repo.get_recent(user_id=container.settings.default_user_id, limit=10)
    if not msgs:
        await message.answer("No forwarded messages yet.")
        return
    lines = ["📝 Recent Forwards:"]
    for m in msgs:
        dt = m.processed_at.strftime("%H:%M") if m.processed_at else "?"
        status_icon = "✅" if m.status == "success" else "❌"
        links = m.links_replaced or 0
        lines.append(f"{status_icon} [{dt}] {links} links | src:{m.source_channel_id}")
    await message.answer("\n".join(lines))


async def cmd_errors(message: types.Message) -> None:
    container = get_container()
    async with container.session_factory() as session:
        repo = MessageRepository(session)
        msgs = await repo.get_error_messages(user_id=container.settings.default_user_id, limit=10)
    if not msgs:
        await message.answer("No errors recorded.")
        return
    lines = ["❌ Recent Errors:"]
    for m in msgs:
        dt = m.processed_at.strftime("%H:%M") if m.processed_at else "?"
        err = (m.error_message or "")[:100]
        lines.append(f"[{dt}] src:{m.source_channel_id} — {err}")
    await message.answer("\n".join(lines))


async def cmd_pause(message: types.Message) -> None:
    container = get_container()
    if container.channel_monitor:
        await container.channel_monitor.customizer.set_paused(True)
        await container.channel_monitor.stop()
    await message.answer("Forwarding paused. Use /resume to continue.")


async def cmd_stop(message: types.Message) -> None:
    container = get_container()
    if not container.channel_monitor:
        await message.answer("Monitor is not running.")
        return
    await container.channel_monitor.stop()
    await message.answer("Monitor stopped.")


async def cmd_resume(message: types.Message) -> None:
    container = get_container()
    if not container.channel_monitor:
        await message.answer("Monitor not initialized.")
        return
    await container.channel_monitor.customizer.set_paused(False)
    await container.channel_monitor.restart()
    await message.answer("Monitor resumed.")


async def cmd_logout(message: types.Message) -> None:
    container = get_container()
    if container.channel_monitor:
        await container.channel_monitor.stop()
    if container.userbot_client:
        await container.userbot_client.stop()
    if container.userbot and container.userbot.is_connected():
        await container.userbot.disconnect()
    async with container.session_factory() as session:
        stmt = sql_update(TelegramAccount).values(is_active=False, session_string_encrypted=None, status="logged_out")
        await session.execute(stmt)
        await session.commit()
    await message.answer("Logged out. Use /login to re-authenticate.")


async def cmd_domain(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(f"Current domain: {container.settings.default_amazon_domain}\nUsage: /domain amazon.com")
        return
    domain = parts[1].strip()
    if not domain:
        await message.answer("Domain cannot be empty.")
        return
    await container.settings_service.set("amazon_domain", domain)
    await message.answer(f"Amazon domain set to: {domain}")


async def cmd_set_delay(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        delay = await container.channel_monitor.customizer.get_delay() if container.channel_monitor else 0
        await message.answer(f"Current delay: {delay}s\nUsage: /set_delay <seconds>")
        return
    try:
        secs = int(parts[1].strip())
        if secs < 0:
            await message.answer("Delay must be >= 0.")
            return
    except ValueError:
        await message.answer("Invalid number. Usage: /set_delay <seconds>")
        return
    if container.channel_monitor:
        await container.channel_monitor.customizer.set_delay(secs)
    else:
        c = get_container()
        pc = PostCustomizer(c.settings_service)
        await pc.set_delay(secs)
    await message.answer(f"Forward delay set to {secs}s.")


async def cmd_affiliate(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = await container.settings_service.get_affiliate_tag()
        if not current:
            current = container.settings.default_affiliate_tag
        await message.answer(f"Current affiliate tag: {current or '(not set)'}\nUsage: /affiliate <yourtag-21>")
        return
    tag = parts[1].strip()
    if not tag:
        await message.answer("Tag cannot be empty.")
        return
    await container.settings_service.set("affiliate_tag", tag)
    await message.answer(f"Affiliate tag set to: {tag}")


async def cmd_clear_affiliate(message: types.Message) -> None:
    container = get_container()
    await container.settings_service.set("affiliate_tag", "")
    await message.answer("Affiliate tag cleared.")


async def cmd_sources(message: types.Message) -> None:
    container = get_container()
    sources = await container.settings_service.get_source_channels()
    if not sources:
        sources = container.settings.source_channels
    if sources:
        await message.answer("Monitored source channels:\n" + "\n".join(f"- @{s}" for s in sources))
    else:
        await message.answer("No source channels configured.")


async def cmd_add_source(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /add_source <channel_username>")
        return
    channel = parts[1].strip().lstrip("@")
    if not channel:
        await message.answer("Channel name cannot be empty.")
        return
    current = await container.settings_service.get_source_channels()
    if not current:
        current = list(container.settings.source_channels)
    if channel in current:
        await message.answer(f"Already monitoring @{channel}")
        return
    current.append(channel)
    await container.settings_service.set("source_channels", ",".join(current))
    await message.answer(f"Added @{channel}. Sources: {', '.join(current)}")
    await message.answer("Run /reload to apply changes.")


async def cmd_remove_source(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /remove_source <channel_username>")
        return
    channel = parts[1].strip().lstrip("@")
    current = await container.settings_service.get_source_channels()
    if not current:
        current = list(container.settings.source_channels)
    if channel not in current:
        await message.answer(f"Not monitoring @{channel}")
        return
    current.remove(channel)
    await container.settings_service.set("source_channels", ",".join(current))
    await message.answer(f"Removed @{channel}. Sources: {', '.join(current) if current else '(none)'}")
    await message.answer("Run /reload to apply changes.")


async def cmd_dest(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = await container.settings_service.get_dest_channel()
        if not current:
            current = container.settings.dest_channel_username or str(container.settings.dest_channel_id or "")
        await message.answer(
            f"Current destination: @{current}\nUsage: /dest <channel_username>" if current
            else "No destination set.\nUsage: /dest <channel_username>"
        )
        return
    channel = parts[1].strip().lstrip("@")
    if not channel:
        await message.answer("Channel name cannot be empty.")
        return
    await container.settings_service.set("dest_channel", channel)
    await message.answer(f"Destination channel set to @{channel}")
    await message.answer("Run /reload to apply changes.")


async def cmd_remove_dest(message: types.Message) -> None:
    container = get_container()
    await container.settings_service.set("dest_channel", "")
    await message.answer("Destination channel cleared.")


async def cmd_config(message: types.Message) -> None:
    container = get_container()
    ss = container.settings_service
    tag = await ss.get_affiliate_tag()
    if not tag:
        tag = container.settings.default_affiliate_tag
    dest = await ss.get_dest_channel()
    if not dest:
        dest = container.settings.dest_channel_username or str(container.settings.dest_channel_id or "")
    sources = await ss.get_source_channels()
    if not sources:
        sources = container.settings.source_channels
    domain = await ss.get("amazon_domain", "")
    if not domain:
        domain = container.settings.default_amazon_domain
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(ss)
    delay = await customizer.get_delay()
    header = await customizer.get_header()
    footer = await customizer.get_footer()
    replaces = await customizer.get_replacements()
    blocks = await customizer.get_blocked_words()
    paused = await customizer.is_paused()
    lines = [
        "⚙️ Runtime Config:\n",
        f"Affiliate tag: {tag or '(not set)'}",
        f"Amazon domain: {domain}",
        f"Source channels: {', '.join(sources) if sources else '(none)'}",
        f"Destination: @{dest}" if dest else "Destination: (not set)",
        f"Forward delay: {delay}s",
        f"Paused: {'yes' if paused else 'no'}",
        f"Header: {'set' if header else 'none'}",
        f"Footer: {'set' if footer else 'none'}",
        f"Replacements: {len(replaces)}",
        f"Blocked words: {len(blocks)}",
    ]
    await message.answer("\n".join(lines))


async def cmd_ping(message: types.Message) -> None:
    await message.answer("Pong!")


async def cmd_reload(message: types.Message) -> None:
    container = get_container()
    if not container.channel_monitor:
        await message.answer("Monitor is not running.")
        return
    try:
        await container.channel_monitor.restart()
        await message.answer("Monitor reloaded with updated settings.")
    except Exception as e:
        logger.error("Reload failed: %s", e)
        await message.answer(f"Reload failed: {e}")


async def cmd_add_replace(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /add_replace OldWord➜NewWord")
        return
    rule = parts[1].strip()
    if "➜" not in rule:
        await message.answer("Use ➜ separator. Example: /add_replace ShopNow➜BuyNow")
        return
    old, new = rule.split("➜", 1)
    old = old.strip()
    new = new.strip()
    if not old:
        await message.answer("Old word cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    replacements = await customizer.get_replacements()
    for item in replacements:
        if item["old"] == old:
            await message.answer(f"Replacement '{old}' already exists.")
            return
    replacements.append({"old": old, "new": new})
    await customizer.set_replacements(replacements)
    await message.answer(f"Replacement added: {old} ➜ {new}")


async def cmd_remove_replace(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /remove_replace OldWord")
        return
    old = parts[1].strip()
    if not old:
        await message.answer("Word cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    replacements = await customizer.get_replacements()
    filtered = [r for r in replacements if r["old"] != old]
    if len(filtered) == len(replacements):
        await message.answer(f"No replacement found for '{old}'.")
        return
    await customizer.set_replacements(filtered)
    await message.answer(f"Replacement removed: {old}")


async def cmd_list_replaces(message: types.Message) -> None:
    container = get_container()
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    replacements = await customizer.get_replacements()
    if not replacements:
        await message.answer("No word replacements configured.")
        return
    lines = ["✂️ Word Replacements:"]
    for r in replacements:
        lines.append(f"{r['old']} ➜ {r['new']}")
    await message.answer("\n".join(lines))


async def cmd_add_block(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /add_block <word>")
        return
    word = parts[1].strip().lower()
    if not word:
        await message.answer("Word cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    words = await customizer.get_blocked_words()
    if word in words:
        await message.answer(f"'{word}' is already blocked.")
        return
    words.append(word)
    await customizer.set_blocked_words(words)
    await message.answer(f"Blocked word added: {word}")


async def cmd_remove_block(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /remove_block <word>")
        return
    word = parts[1].strip().lower()
    if not word:
        await message.answer("Word cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    words = await customizer.get_blocked_words()
    if word not in words:
        await message.answer(f"'{word}' is not in the block list.")
        return
    words.remove(word)
    await customizer.set_blocked_words(words)
    await message.answer(f"Blocked word removed: {word}")


async def cmd_list_blocks(message: types.Message) -> None:
    container = get_container()
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    words = await customizer.get_blocked_words()
    if not words:
        await message.answer("No blocked words configured.")
        return
    await message.answer("🚫 Blocked Words:\n" + "\n".join(f"- {w}" for w in words))


async def cmd_set_header(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        cm = container.channel_monitor
        customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
        current = await customizer.get_header()
        await message.answer(f"Current header:\n{current}\n\nUsage: /set_header <text>" if current else "No header set.\nUsage: /set_header <text>")
        return
    text = parts[1].strip()
    if not text:
        await message.answer("Header text cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    await customizer.set_header(text)
    await message.answer(f"Header set to:\n{text}")


async def cmd_set_footer(message: types.Message) -> None:
    container = get_container()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        cm = container.channel_monitor
        customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
        current = await customizer.get_footer()
        await message.answer(f"Current footer:\n{current}\n\nUsage: /set_footer <text>" if current else "No footer set.\nUsage: /set_footer <text>")
        return
    text = parts[1].strip()
    if not text:
        await message.answer("Footer text cannot be empty.")
        return
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    await customizer.set_footer(text)
    await message.answer(f"Footer set to:\n{text}")


async def cmd_clear_header(message: types.Message) -> None:
    container = get_container()
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    await customizer.clear_header()
    await message.answer("Header cleared.")


async def cmd_clear_footer(message: types.Message) -> None:
    container = get_container()
    cm = container.channel_monitor
    customizer = cm.customizer if cm else PostCustomizer(container.settings_service)
    await customizer.clear_footer()
    await message.answer("Footer cleared.")
