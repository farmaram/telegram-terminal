import asyncio
import os
import subprocess
import re
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from PIL import Image, ImageDraw, ImageFont, ImageOps
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeSticker, InputStickerSetEmpty

api_id = int(os.environ.get("TG_API_ID", "123456"))
api_hash = os.environ.get("TG_API_HASH", "your_api_hash")

SESSION_NAME = "personal_userbot"
COMMAND_PREFIX = "."
QUOTE_DIR = Path("downloads/quotes")
MAX_SPAM_COUNT = 1000
SPAM_DELAY_SECONDS = 0.05
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "dclid",
    "gbraid",
    "wbraid",
    "msclkid",
    "yclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mibextid",
    "ref",
    "ref_src",
    "spm",
    "si",
    "feature",
    "app",
    "share_id",
    "share_item_id",
    "timestamp",
    "is_from_webapp",
    "sender_device",
    "web_id",
    "tt_from",
    "_r",
    "_t",
}

client = TelegramClient(SESSION_NAME, api_id, api_hash)
AVATAR_CACHE = {}
ACTIVE_SPAMS = {}


HELP_TEXT = """personal-userbot commands

Quotes
  .q                    quote the replied message as sticker
  .quote                same as .q
  .quotly               same as .q
  .q --png              send quote as PNG instead of sticker
  .q N                  quote N messages, max 10
  .q custom text        make a quote from custom text
  .q on selected quote  quote only the selected Telegram quote text

Bot
  .phelp                show this help
  .pping                latency check
  .spam text N          send text N times, max 1000
  .spam N               reply to media and resend it N times
  .unspam               stop spam in this chat
  .cleanurl URL         remove tracking params from URL
"""


def tg_code(text):
    safe = str(text).replace("```", "`\u200b``")
    return f"```{safe}```"


def parse_command(text):
    text = text or ""

    if not text.startswith(COMMAND_PREFIX):
        return None, ""

    body = text[len(COMMAND_PREFIX):].strip()

    if not body:
        return None, ""

    name, _, rest = body.partition(" ")
    return name.lower(), rest.strip()


def parse_quote_options(raw):
    args = raw.split()
    send_png = False
    count = 1
    text_parts = []

    for arg in args:
        if arg == "--png":
            send_png = True
        elif arg.isdigit() and not text_parts:
            count = max(1, min(10, int(arg)))
        else:
            text_parts.append(arg)

    return send_png, count, " ".join(text_parts).strip()


def parse_spam_options(raw):
    raw = raw.strip()

    if not raw:
        return None, None

    if raw.isdigit():
        return "", max(1, min(MAX_SPAM_COUNT, int(raw)))

    text, _, count_text = raw.rpartition(" ")

    if not text.strip() or not count_text.isdigit():
        return None, None

    count = max(1, min(MAX_SPAM_COUNT, int(count_text)))
    return text.strip(), count


def topic_reply_to(event):
    reply_header = getattr(getattr(event, "message", None), "reply_to", None)

    if not reply_header:
        return None

    return getattr(reply_header, "reply_to_msg_id", None) or getattr(reply_header, "reply_to_top_id", None)


def topic_id(event):
    reply_header = getattr(getattr(event, "message", None), "reply_to", None)

    if not reply_header:
        return None

    return getattr(reply_header, "reply_to_top_id", None) or getattr(reply_header, "reply_to_msg_id", None)


def spam_key(event):
    return event.chat_id, topic_id(event)


def is_tracking_param(name):
    lower = name.lower()
    return lower.startswith("utm_") or lower in TRACKING_PARAMS


def extract_url(text):
    match = URL_RE.search(text or "")

    if not match:
        return ""

    return match.group(0).rstrip(".,;:!?")


def clean_tracking_url(url):
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not is_tracking_param(key)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


async def clean_url_message(event, raw):
    url = extract_url(raw)

    if not url:
        reply = await event.get_reply_message()
        url = extract_url(getattr(reply, "raw_text", "") if reply else "")

    if not url:
        await event.reply(tg_code("Use: .cleanurl URL, or reply to a message with URL"))
        return

    await event.reply(clean_tracking_url(url))


def load_quote_font(size, bold=False):
    candidates = []

    if bold:
        candidates.extend([
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ])

    candidates.extend([
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("assets/fonts/DejaVuSansMono.ttf"),
    ])

    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                pass

    return ImageFont.load_default()


def avatar_initials(name):
    parts = [p for p in re.split(r"\s+", name.strip()) if p]

    if not parts:
        return "?"

    return "".join(p[0].upper() for p in parts[:2])


def multiline_size(draw, text, font, spacing=8):
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
    return box[2] - box[0], box[3] - box[1]


def circle_crop(image, size):
    image = ImageOps.fit(image.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(image, (0, 0), mask)
    return output


async def get_sender_avatar(sender, name, size=104):
    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    sender_id = getattr(sender, "id", None) or name or "unknown"
    cache_key = (sender_id, name, size)

    if cache_key in AVATAR_CACHE:
        return AVATAR_CACHE[cache_key].copy()

    avatar_path = QUOTE_DIR / f"avatar-{sender_id}.jpg"

    try:
        if avatar_path.is_file():
            avatar = circle_crop(Image.open(avatar_path), size)
            AVATAR_CACHE[cache_key] = avatar
            return avatar.copy()

        downloaded = await client.download_profile_photo(sender, file=str(avatar_path))

        if downloaded and Path(downloaded).is_file():
            avatar = circle_crop(Image.open(downloaded), size)
            AVATAR_CACHE[cache_key] = avatar
            return avatar.copy()
    except Exception as e:
        print(f"Avatar download failed: {e}")

    avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(avatar)
    draw.ellipse((0, 0, size - 1, size - 1), fill=(76, 132, 255, 255))
    font = load_quote_font(38, bold=True)
    initials = avatar_initials(name)
    box = draw.textbbox((0, 0), initials, font=font)
    draw.text(
        ((size - (box[2] - box[0])) / 2, (size - (box[3] - box[1])) / 2 - 3),
        initials,
        font=font,
        fill=(255, 255, 255, 255),
    )
    AVATAR_CACHE[cache_key] = avatar
    return avatar.copy()


def fit_quote_text(text, max_chars=900):
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."

    return text


def fit_media_image(image, max_width=820, max_height=520):
    image = image.convert("RGBA")
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    radius = max(18, min(image.size) // 12)
    draw.rounded_rectangle((0, 0, image.size[0] - 1, image.size[1] - 1), radius=radius, fill=255)

    framed = Image.new("RGBA", image.size, (0, 0, 0, 0))
    framed.paste(image, (0, 0), mask)
    return framed


def extract_video_frame(video_path):
    frame_path = Path(f"{video_path}.frame.jpg")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "00:00:01",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(frame_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if frame_path.is_file():
            return Image.open(frame_path).convert("RGBA")
    except FileNotFoundError:
        print("Video quote needs ffmpeg installed to extract a frame.")
    except Exception as e:
        print(f"Video frame extraction failed: {e}")

    return None


def open_media_image(path):
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


async def download_media_thumbnail(reply):
    thumb_path = QUOTE_DIR / f"thumb-{reply.id}.jpg"

    try:
        downloaded = await reply.download_media(file=str(thumb_path), thumb=-1)

        if downloaded:
            return open_media_image(downloaded)
    except Exception as e:
        print(f"Media thumbnail download failed: {e}")

    return None


async def get_quote_media(reply):
    if not reply or not reply.media:
        return None

    QUOTE_DIR.mkdir(parents=True, exist_ok=True)

    # Animated stickers often download as .tgs, which Pillow/ffmpeg cannot render
    # directly here. Telegram usually exposes a static thumbnail for them.
    if getattr(reply, "sticker", None):
        thumbnail = await download_media_thumbnail(reply)

        if thumbnail is not None:
            return thumbnail

    media_path = QUOTE_DIR / f"media-{reply.id}"

    try:
        downloaded = await reply.download_media(file=str(media_path))

        if not downloaded:
            return None

        downloaded_path = Path(downloaded)
        image = open_media_image(downloaded_path)

        if image is not None:
            return image

        frame = extract_video_frame(downloaded_path)

        if frame is not None:
            return frame

        return await download_media_thumbnail(reply)
    except Exception as e:
        print(f"Media download failed: {e}")
        return await download_media_thumbnail(reply)


def author_color(name):
    colors = [
        (51, 144, 236, 255),
        (0, 150, 136, 255),
        (230, 126, 34, 255),
        (142, 68, 173, 255),
        (211, 47, 47, 255),
        (46, 125, 50, 255),
    ]
    return colors[sum(name.encode("utf-8", errors="ignore")) % len(colors)]


def quote_bubble_image(author, text, avatar, media_image=None):
    name_font = load_quote_font(30, bold=True)
    text_font = load_quote_font(36)
    meta_font = load_quote_font(20)

    text = fit_quote_text(text)
    wrapped_parts = [textwrap.fill(part, width=32) for part in text.splitlines()]
    wrapped = "\n".join(wrapped_parts).strip()
    media = fit_media_image(media_image, max_width=720, max_height=440) if media_image is not None else None

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    text_w, text_h = multiline_size(draw, wrapped, text_font, spacing=10) if wrapped else (0, 0)
    name_w, name_h = multiline_size(draw, author, name_font, spacing=0)
    media_w, media_h = media.size if media else (0, 0)
    body_w = max(text_w, media_w, name_w, 260)

    avatar_size = 96
    gap = 18
    bubble_pad_x = 28
    bubble_pad_y = 22
    content_gap = 18 if wrapped and media else 0
    bubble_w = min(900, body_w + bubble_pad_x * 2)
    bubble_h = bubble_pad_y * 2 + name_h + 14 + media_h + content_gap + text_h + 30
    width = avatar_size + gap + bubble_w + 28
    height = max(avatar_size + 26, bubble_h + 26)

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    avatar_x = 12
    avatar_y = height - avatar_size - 14
    avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    image.alpha_composite(avatar, (avatar_x, avatar_y))

    bubble_x = avatar_x + avatar_size + gap
    bubble_y = 10
    draw.rounded_rectangle((bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h), radius=30, fill=(20, 20, 22, 255))
    draw.polygon(
        [
            (bubble_x + 8, bubble_y + bubble_h - 42),
            (bubble_x - 20, bubble_y + bubble_h - 20),
            (bubble_x + 16, bubble_y + bubble_h - 18),
        ],
        fill=(20, 20, 22, 255),
    )

    x = bubble_x + bubble_pad_x
    y = bubble_y + bubble_pad_y
    draw.text((x, y), author, font=name_font, fill=author_color(author))
    y += name_h + 14

    if media:
        image.alpha_composite(media, (x, y))
        y += media.size[1] + content_gap

    if wrapped:
        draw.text((x, y), wrapped, font=text_font, fill=(245, 245, 247, 255), spacing=10)

    timestamp = datetime.now().strftime("%H:%M")
    time_box = draw.textbbox((0, 0), timestamp, font=meta_font)
    draw.text(
        (bubble_x + bubble_w - (time_box[2] - time_box[0]) - 22, bubble_y + bubble_h - 32),
        timestamp,
        font=meta_font,
        fill=(158, 158, 166, 255),
    )

    return image


def create_quote_image(author, text, avatar, media_image=None):
    return create_quote_stack([
        {
            "author": author,
            "text": text,
            "avatar": avatar,
            "media_image": media_image,
        }
    ])


def create_quote_stack(items):
    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    bubbles = [
        quote_bubble_image(
            item["author"],
            item["text"],
            item["avatar"],
            item.get("media_image"),
        )
        for item in items
    ]
    gap = 10
    width = max(bubble.size[0] for bubble in bubbles)
    height = sum(bubble.size[1] for bubble in bubbles) + gap * (len(bubbles) - 1)

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0

    for bubble in bubbles:
        image.alpha_composite(bubble, (0, y))
        y += bubble.size[1] + gap

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = QUOTE_DIR / f"quote-{stamp}.png"
    image.save(path)
    return path

def create_quote_sticker(png_path):
    image = Image.open(png_path).convert("RGBA")
    width, height = image.size
    scale = min(512 / width, 512 / height, 1)
    sticker_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    image = image.resize(sticker_size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - sticker_size[0]) // 2
    y = (512 - sticker_size[1]) // 2
    canvas.alpha_composite(image, (x, y))

    webp_path = png_path.with_suffix(".webp")
    canvas.save(webp_path, "WEBP", lossless=True, quality=90, method=3)
    return webp_path


def display_name(entity, fallback="User"):
    if not entity:
        return fallback

    title = getattr(entity, "title", None)

    if title:
        return title

    first = getattr(entity, "first_name", None) or ""
    last = getattr(entity, "last_name", None) or ""
    name = f"{first} {last}".strip()

    if name:
        return name

    username = getattr(entity, "username", None)

    if username:
        return f"@{username}"

    return fallback


async def forwarded_sender(reply):
    forward = getattr(reply, "forward", None)

    if not forward:
        return None, None

    sender = getattr(forward, "sender", None)

    if sender:
        return sender, display_name(sender)

    chat = getattr(forward, "chat", None)

    if chat:
        return chat, display_name(chat)

    sender_id = getattr(forward, "sender_id", None)

    if sender_id:
        try:
            entity = await client.get_entity(sender_id)
            return entity, display_name(entity)
        except Exception:
            pass

    from_name = getattr(forward, "from_name", None)

    if from_name:
        return None, from_name

    return None, None


def selected_reply_quote_text(event):
    reply_header = getattr(getattr(event, "message", None), "reply_to", None)

    if not reply_header:
        return ""

    quote_text = getattr(reply_header, "quote_text", None) or ""
    return quote_text.strip()


async def build_quote_item(message, text_override=None, include_media=True):
    text = text_override if text_override is not None else (message.raw_text or "")
    sender = await message.get_sender()
    forwarded_entity, forwarded_name = await forwarded_sender(message)
    author = forwarded_name or display_name(sender)
    avatar_sender = forwarded_entity or sender
    media_image = await get_quote_media(message) if include_media else None

    if not text.strip() and media_image is None:
        text = "[unsupported media]"

    avatar = await get_sender_avatar(avatar_sender, author)
    return {
        "author": author,
        "text": text,
        "avatar": avatar,
        "media_image": media_image,
    }


async def collect_quote_messages(event, reply, count):
    if count <= 1:
        return [reply]

    messages = [reply]
    min_id = reply.id
    max_id = reply.id + count + 25

    async for message in client.iter_messages(event.chat_id, min_id=min_id, max_id=max_id, reverse=True):
        if message.id <= reply.id:
            continue

        messages.append(message)

        if len(messages) >= count:
            break

    return messages


async def quote_message(event, raw_options=""):
    send_png, count, custom_text = parse_quote_options(raw_options)
    reply = await event.get_reply_message()

    if custom_text:
        sender = await event.get_sender()
        author = display_name(sender)
        avatar = await get_sender_avatar(sender, author)
        png_path = create_quote_image(author, custom_text, avatar)
    elif reply:
        selected_text = selected_reply_quote_text(event)

        if selected_text and count == 1:
            item = await build_quote_item(reply, text_override=selected_text, include_media=False)
            png_path = create_quote_stack([item])
        else:
            messages = await collect_quote_messages(event, reply, count)
            items = await asyncio.gather(*(build_quote_item(message) for message in messages))
            png_path = create_quote_stack(items)
    else:
        await event.reply(tg_code("Reply to a message with .q, or use: .q custom text"))
        return

    if send_png:
        await event.reply(file=str(png_path))
        return

    sticker_path = create_quote_sticker(png_path)
    await event.reply(
        file=str(sticker_path),
        force_document=False,
        attributes=[DocumentAttributeSticker(alt="💬", stickerset=InputStickerSetEmpty())],
    )


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    name, rest = parse_command(event.raw_text)

    if not name:
        return

    if name == "phelp":
        await event.reply(tg_code(HELP_TEXT))
    elif name == "pping":
        started = datetime.now()
        msg = await event.reply(tg_code("pong"))
        latency = int((datetime.now() - started).total_seconds() * 1000)
        await msg.edit(tg_code(f"pong {latency}ms"))
    elif name == "spam":
        text, count = parse_spam_options(rest)

        if text is None:
            await event.reply(tg_code("Use: .spam text N, or reply to media with .spam N"))
            return

        reply = await event.get_reply_message() if not text else None
        media = getattr(reply, "media", None) if reply else None

        if not text and media is None:
            await event.reply(tg_code("Reply to a sticker, GIF or media with .spam N"))
            return

        chat_id = event.chat_id
        reply_to = topic_reply_to(event)
        active_key = spam_key(event)
        previous_stop = ACTIVE_SPAMS.get(active_key)

        if previous_stop:
            previous_stop.set()

        stop_event = asyncio.Event()
        ACTIVE_SPAMS[active_key] = stop_event
        await event.delete()

        try:
            for _ in range(count):
                if stop_event.is_set():
                    break

                if text:
                    await client.send_message(chat_id, text, reply_to=reply_to)
                else:
                    await client.send_message(chat_id, "", file=media, reply_to=reply_to)
                await asyncio.sleep(SPAM_DELAY_SECONDS)
        finally:
            if ACTIVE_SPAMS.get(active_key) is stop_event:
                ACTIVE_SPAMS.pop(active_key, None)
    elif name == "cleanurl":
        await clean_url_message(event, rest)
    elif name == "unspam":
        active_key = spam_key(event)
        stop_events = []

        stop_event = ACTIVE_SPAMS.get(active_key)
        if stop_event:
            stop_events.append(stop_event)
        else:
            stop_events.extend(
                active_stop
                for (chat_id, _), active_stop in ACTIVE_SPAMS.items()
                if chat_id == event.chat_id
            )

        if stop_events:
            for stop_event in stop_events:
                stop_event.set()
            await event.delete()
        else:
            await event.reply(tg_code("No spam running in this chat"))
    elif name in {"q", "quote", "quotly"}:
        await quote_message(event, rest)


async def main():
    print("personal-userbot is running. Send $phelp in Telegram.")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
