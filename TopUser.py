import asyncio
import base64
import html
import json
import types
import os
import subprocess
import re
import shutil
import tempfile
import textwrap
import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from telethon import TelegramClient, events
from telethon.tl import functions
from telethon.tl.types import DocumentAttributeSticker, DocumentAttributeVideo, InputStickerSetEmpty

api_id = int(os.environ.get("TG_API_ID", "123456"))
api_hash = os.environ.get("TG_API_HASH", "your_api_hash")

SESSION_NAME = "personal_userbot"
COMMAND_PREFIX = "."
TERMINAL_PREFIX = "$"
QUOTE_DIR = Path("downloads/quotes")
MEDIA_DIR = Path("downloads/media")
DOWNLOAD_DIR = Path("downloads/links")
MAX_SPAM_COUNT = 1000
SPAM_DELAY_SECONDS = 0.05
ONLINE_REFRESH_SECONDS = max(10, int(os.environ.get("TOPUSER_ONLINE_REFRESH_SECONDS", "10")))
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
    "__cft__",
    "__tn__",
    "eav",
    "paipv",
    "rdid",
    "sfnsn",
}
DROP_ALL_QUERY_DOMAINS = ("tiktok.com", "instagram.com", "x.com", "twitter.com", "pinterest.com")
REDIRECT_PARAM_NAMES = {
    "u",
    "url",
    "q",
    "target",
    "to",
    "dest",
    "destination",
    "redirect",
    "redirect_url",
    "redirect_uri",
    "link",
    "r",
    "adurl",
}
REDIRECT_HOST_SUFFIXES = (
    "google.com",
    "google.com.br",
    "bing.com",
    "duckduckgo.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
)
SHORT_URL_HOSTS = {
    "vt.tiktok.com",
    "vm.tiktok.com",
    "t.tiktok.com",
    "fb.watch",
    "t.co",
    "bit.ly",
    "tinyurl.com",
    "shorturl.at",
    "is.gd",
    "buff.ly",
    "ow.ly",
    "pin.it",
}

client = TelegramClient(SESSION_NAME, api_id, api_hash)
AVATAR_CACHE = {}
ACTIVE_SPAMS = {}
ACTIVE_EXPORTS = {}
EXPORT_AVATAR_CACHE = {}
VEGADATA_CHANNEL_ID = "UCd2FHKnQ3ymrNhdsV9J0VmA"
VEGADATA_CHANNEL_URL = "https://youtube.com/@vegadata"
VEGADATA_COUNTER_URL = f"https://mixerno.space/api/youtube-channel-counter/user/{VEGADATA_CHANNEL_ID}"


TOPUSER_ASCII = r"""
 _______          __  __
|__   __|        | | | |
   | | ___  _ __ | | | |___  ___ _ __
   | |/ _ \| '_ \| | | / __|/ _ \ '__|
   | | (_) | |_) | |_| \__ \  __/ |
   |_|\___/| .__/ \___/|___/\___|_|
            | |
            |_|
""".strip("\n")

FALLBACK_TELEGRAM_TERMINAL_HELP = """telegram-terminal
  $help                 show telegram-terminal help
"""

TOPUSER_HELP = """TopUser personal userbot help

Bot
  .help                 show this help
  .pping                latency check

Quotes
  .q                    quote the replied message as sticker
  .q --png              send quote as PNG instead of sticker
  .q N                  quote N messages, max 10
  .q custom text        make a quote from custom text
  .q on selected quote  quote only selected Telegram quote text

Spam
  .spam text N          send text N times, max 1000
  .spam N               reply to media and resend it N times
  .unspam               stop spam in this chat/topic

Links
  .cleanurl URL         remove tracking params from URL
  .vegadata            show @vegadata YouTube subscribers
  .download URL         download video with Nayan API
  .mp3 URL              get audio using API when available
  add mp3 after any API shortcut to request audio
  .api URL              download with Nayan API for supported sites
  .yt/.ig/.fb/.x URL    API shortcuts for social links
  .pin/.capcut/.soundcloud URL and more API shortcuts

Media
  .144p                 reply to media and send a low quality version

Chat
  .exportchat           export current chat/topic as HTML
  .exportchat ID/@user export another chat as HTML
  .cancelexport         stop export and send partial HTML
  .cl                   delete your messages in this chat/topic

Files
  generated files are deleted after sending"""


TELEGRAM_TERMINAL_SOURCE = 'import asyncio\nimport os\nimport socket\nimport time\nimport re\nimport shlex\nimport struct\nimport tempfile\nimport zlib\nfrom datetime import datetime\nfrom pathlib import Path\n\nimport pexpect\nimport pyte\nfrom PIL import Image, ImageDraw, ImageFont\n\nfrom telethon import TelegramClient, events\nfrom telethon.errors import FloodWaitError\n\nclient = None\n\nVERSION = "1.3.0"\nBASE_DIR = Path(__file__).resolve().parent\nEDIT_INTERVAL = 3\nMAX_MESSAGE_OUTPUT = 3900\nMAX_BUFFER_SIZE = 200000\nTERM_COLUMNS = 160\nTERM_LINES = 44\nTERM_SCROLLBACK = 400\nSHOT_RENDER_ROWS = 76\nSHOT_LIVE_SECONDS = 5\nSHOT_LIVE_MAX_SECONDS = 10\nSHOT_LIVE_INTERVAL = 0.2\nSHOT_LIVE_MAX_BYTES = 8 * 1024 * 1024\n\nDONE_MARKER = "__TCM_DONE_982741__"\nMARKER_HOLD_SIZE = len(DONE_MARKER) - 1\n\n\ndef spawn_shell():\n    child = pexpect.spawn(\n        "bash",\n        ["--noprofile", "--norc", "--noediting"],\n        encoding="utf-8",\n        echo=False,\n        dimensions=(TERM_LINES, TERM_COLUMNS),\n        env={\n            **os.environ,\n            "TERM": "xterm-256color",\n            "TERM_PROGRAM": "telegram-terminal",\n            "TERM_PROGRAM_VERSION": VERSION,\n            "COLORTERM": "truecolor",\n            "PS1": "",\n            "PS2": "",\n            "PROMPT_COMMAND": "",\n        }\n    )\n    child.delaybeforesend = 0\n    return child\n\n\nshell = spawn_shell()\nterminal_screen = pyte.HistoryScreen(TERM_COLUMNS, TERM_LINES, history=TERM_SCROLLBACK)\nterminal_stream = pyte.Stream(terminal_screen)\n\ncurrent_msg = None\ncurrent_event = None\n\noutput_buffer = ""\ncommand_output_buffer = ""\ncommand_file_output_buffer = ""\noutput_revision = 0\n\neditor_state = None\n\ncommand_history = []\nlast_command = None\nlog_enabled = False\ncurrent_log_path = None\ncurrent_output_mode = "chat"\ncurrent_output_no_session = False\ncurrent_shot_clear_after = False\ncurrent_shot_save_path = None\ncurrent_shot_wide = False\ncurrent_shot_command = None\ncurrent_command_started_at = None\ncurrent_command_last_activity = None\npending_shell_data = ""\nshot_theme = "black"\nshot_title = "telegram-terminal"\nshell_cwd = Path.cwd()\nterminal_waiting_prompt = False\nterminal_external_prompt = False\nstarted_at = time.time()\ntruetype_available = True\ntruetype_warning_shown = False\n\nSHELL_WATCHDOG_IDLE_TIMEOUT = 1800\nSHELL_WATCHDOG_POLL_INTERVAL = 10\n\nSHOT_THEMES = {\n    "black": {\n        "bg": (0, 0, 0),\n        "bar": (24, 30, 39),\n        "line": (42, 52, 65),\n        "title": (226, 232, 240),\n        "text": (235, 235, 235),\n        "cursor": (235, 235, 235),\n        "cursor_text": (0, 0, 0),\n    },\n    "green": {\n        "bg": (0, 0, 0),\n        "bar": (0, 0, 0),\n        "line": (28, 48, 34),\n        "title": (226, 232, 240),\n        "text": (220, 255, 226),\n        "cursor": (220, 255, 226),\n        "cursor_text": (0, 0, 0),\n    },\n    "white": {\n        "bg": (0, 0, 0),\n        "bar": (0, 0, 0),\n        "line": (42, 42, 42),\n        "title": (238, 242, 247),\n        "text": (235, 239, 245),\n        "cursor": (235, 239, 245),\n        "cursor_text": (0, 0, 0),\n    },\n    "amber": {\n        "bg": (0, 0, 0),\n        "bar": (0, 0, 0),\n        "line": (82, 58, 22),\n        "title": (255, 236, 179),\n        "text": (255, 213, 128),\n        "cursor": (255, 213, 128),\n        "cursor_text": (0, 0, 0),\n    },\n}\n\nansi_escape = re.compile(\n    r\'\\x1B(?:\\][^\\x07]*(?:\\x07|\\x1B\\\\)|\\[[0-?]*[ -/]*[@-~]|[@-Z\\\\-_])\'\n)\n\n\ndef clean_output(text):\n    return ansi_escape.sub(\'\', text)\n\n\ndef render_terminal_text(text):\n    lines = [[]]\n    col = 0\n\n    for char in text:\n        if char == "\\r":\n            lines[-1] = []\n            col = 0\n        elif char == "\\n":\n            lines.append([])\n            col = 0\n        elif char == "\\b":\n            col = max(0, col - 1)\n        elif char == "\\t":\n            spaces = 8 - (col % 8)\n\n            for _ in range(spaces):\n                if col == len(lines[-1]):\n                    lines[-1].append(" ")\n                else:\n                    lines[-1][col] = " "\n\n                col += 1\n        elif char >= " ":\n            line = lines[-1]\n\n            if col > len(line):\n                line.extend(" " for _ in range(col - len(line)))\n\n            if col == len(line):\n                line.append(char)\n            else:\n                line[col] = char\n\n            col += 1\n\n    return "\\n".join("".join(line).rstrip() for line in lines).rstrip()\n\n\ndef command_message_preview():\n    return command_output_buffer[-MAX_MESSAGE_OUTPUT:] if command_output_buffer else ""\n\ndef tg_code(text):\n    safe = str(text).replace("```", "`\\u200b``")\n    return f"```{safe}```"\n\n\ndef build_help():\n    return """telegram-terminal help\n\nShell\n  $<command>                 run command in persistent bash\n  $ttinput <text>            send one input line\n  $ttpaste <text>            paste raw text without Enter\n\nTerminal Keys\n  $ctrlc / $ctrl c           send Ctrl+C\n  $ctrlb / $ctrl b           send Ctrl+B, useful for tmux prefix\n  $ctrla / $ctrl a           send Ctrl+A\n  $ctrld                     send Ctrl+D\n  $ctrlz                     send Ctrl+Z\n  $enter                     send Enter\n  $tab                       send Tab\n  $up / $down / $left / $right\n  $key esc|backspace|delete|home|end|pgup|pgdn|space\n  $key f1..f12               send function keys\n\nScreenshots\n  $shot                      screenshot current terminal screen\n  $shot 80                   screenshot last 80 text-buffer lines\n  $shot wide                 wider terminal screenshot\n  $shot clear                screenshot, then clear screen/buffer\n  $shot live N               readable animated screenshot, 1-10 seconds\n  $shot live wide N          wider animated screenshot, 1-10 seconds\n  $shot run <cmd>            run command and send screenshot\n  $shot run wide <cmd>       run command with wider screenshot\n  $shot run clear <cmd>      run, screenshot, then clear\n  $shot run --no-session <cmd>\n  $shot theme [black|green|white|amber]\n  $shot title <text>\n  $tt size [COLSxROWS]       show or resize the pty/screenshot terminal\n\nBuffers\n  $buf tail [lines|full]     show session output buffer\n  $buf send [file.txt]       send session buffer as .txt\n  $buf save <file.txt>       save session buffer on server\n  $tt save-session [file]    save session buffer on server\n  $buf clear                 clear session buffer and shot screen\n  $buf status                show buffer status\n\nFiles\n  $ttget <file>              send file from server\n  $ttput <path>              upload attached document to path\n\nEditor\n  $ttedit open <file>        open file\n  $ttedit show               show editor buffer\n  $ttedit set N <text>       replace line N\n  $ttedit insert N <text>    insert before line N\n  $ttedit append <text>      append line\n  $ttedit delete N[-M]       delete line/range\n  $ttedit undo               undo last edit\n  $ttedit find <text>        find text\n  $ttedit replace old new    replace first match\n  $ttedit replace-all old new\n  $ttedit save               save file\n  $ttedit cancel             close editor\n\nHistory / Logs\n  $cmd history [N]           show command history\n  $cmd last                  show last command\n  $cmd rerun N               rerun command by history number\n  $out log on|off|status     save command outputs to logs/\n\nBot\n  $tt status                 shell/editor status\n  $tt restart                restart persistent bash\n  $tt reset                  clear bot runtime state\n  $tt version                show version\n  $tt ping                   check latency\n  $tt uptime                 show bot and system uptime\n  $tt uptime bot             show bot uptime\n  $tt uptime system          show system uptime\n  $tt about                  show summary"""\n\n\nHELP_TEXT = build_help()\n\n\ndef editor_preview(max_chars=3300):\n    if not editor_state:\n        return "No file is open. Use $ttedit open <file> first."\n\n    lines = editor_state["lines"]\n    path = editor_state["path"]\n    dirty = "modified" if editor_state["dirty"] else "saved"\n    header = f"Editing: {path} ({len(lines)} lines, {dirty})\\n"\n    header += "Commands: $ttedit show | $ttedit set N text | $ttedit insert N text | $ttedit delete N[-M] | $ttedit save | $ttedit cancel\\n\\n"\n    body = "\\n".join(f"{idx:4}: {line}" for idx, line in enumerate(lines, start=1))\n    preview = header + body\n\n    if len(preview) > max_chars:\n        preview = preview[:max_chars] + "\\n... (preview truncated; file is still loaded)"\n\n    return preview\n\n\ndef parse_line_range(value, total_lines):\n    value = value.strip()\n\n    if not value:\n        raise ValueError("missing line number")\n\n    if "-" in value:\n        start_text, end_text = value.split("-", 1)\n        start = int(start_text)\n        end = int(end_text)\n    else:\n        start = end = int(value)\n\n    if start < 1 or end < start or end > total_lines:\n        raise ValueError(f"line range must be between 1 and {total_lines}")\n\n    return start, end\n\n\ndef split_command_args(command):\n    try:\n        return shlex.split(command)\n    except ValueError:\n        return command.split()\n\n\n\ndef tail_output(arg=""):\n    if not output_buffer:\n        return "Output buffer is empty."\n\n    arg = arg.strip().lower()\n\n    if arg == "full":\n        return output_buffer\n\n    if arg:\n        try:\n            line_count = max(1, int(arg))\n        except ValueError:\n            line_count = 80\n    else:\n        line_count = 80\n\n    return "\\n".join(output_buffer.splitlines()[-line_count:])\n\n\n\ndef history_preview(limit=30):\n    if not command_history:\n        return "History is empty."\n\n    items = command_history[-limit:]\n    offset = len(command_history) - len(items)\n    return "\\n".join(f"{offset + idx + 1}: {cmd}" for idx, cmd in enumerate(items))\n\n\ndef create_log_path(command):\n    logs_dir = Path("logs")\n    logs_dir.mkdir(parents=True, exist_ok=True)\n    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", command.strip())[:60].strip("_")\n\n    if not safe_name:\n        safe_name = "command"\n\n    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")\n    return logs_dir / f"{stamp}-{safe_name}.txt"\n\n\ndef write_command_log(command, content, path):\n    if not path:\n        return\n\n    header = f"Command: {command}\\nTime: {datetime.now().isoformat(timespec=\'seconds\')}\\n\\n"\n    path.write_text(header + content, encoding="utf-8", errors="replace")\n\n\ndef reset_runtime_state():\n    global current_msg\n    global current_event\n    global command_output_buffer\n    global command_file_output_buffer\n    global output_revision\n    global current_log_path\n    global current_output_mode\n    global current_output_no_session\n    global current_shot_clear_after\n    global current_shot_save_path\n    global current_shot_wide\n    global current_shot_command\n    global current_command_started_at\n    global current_command_last_activity\n    global pending_shell_data\n    global terminal_waiting_prompt\n    global terminal_external_prompt\n\n    current_msg = None\n    current_event = None\n    command_output_buffer = ""\n    command_file_output_buffer = ""\n    current_log_path = None\n    current_output_mode = "chat"\n    current_output_no_session = False\n    current_shot_clear_after = False\n    current_shot_save_path = None\n    current_shot_wide = False\n    current_shot_command = None\n    current_command_started_at = None\n    current_command_last_activity = None\n    pending_shell_data = ""\n    terminal_waiting_prompt = False\n    terminal_external_prompt = False\n    output_revision += 1\n\n\ndef reply_target_id(event):\n    message = getattr(event, "message", event)\n    return getattr(message, "id", None)\n\n\nasync def reply_file(event, file_path, message=None, force_document=False):\n    chat_id = getattr(event, "chat_id", None)\n\n    if chat_id is None and hasattr(event, "get_chat"):\n        chat = await event.get_chat()\n        chat_id = getattr(chat, "id", chat)\n\n    await event.client.send_file(\n        chat_id,\n        str(file_path),\n        caption=message,\n        reply_to=reply_target_id(event),\n        force_document=force_document,\n    )\n\n\nasync def send_text_file(event, content, filename="telegram-terminal-output.txt", message="Output attached as text file."):\n    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tmp:\n        tmp.write(content)\n        tmp_path = Path(tmp.name)\n\n    final_path = tmp_path.with_name(filename)\n    tmp_path.replace(final_path)\n\n    try:\n        await reply_file(event, final_path, message)\n    finally:\n        try:\n            final_path.unlink()\n        except OSError:\n            pass\n\n\n\nFONT_5X7 = {\n    " ": [0, 0, 0, 0, 0, 0, 0],\n    "!": [4, 4, 4, 4, 4, 0, 4],\n    "\\"": [10, 10, 10, 0, 0, 0, 0],\n    "#": [10, 10, 31, 10, 31, 10, 10],\n    "$": [4, 15, 20, 14, 5, 30, 4],\n    "%": [24, 25, 2, 4, 8, 19, 3],\n    "&": [12, 18, 20, 8, 21, 18, 13],\n    "\'": [4, 4, 8, 0, 0, 0, 0],\n    "(": [2, 4, 8, 8, 8, 4, 2],\n    ")": [8, 4, 2, 2, 2, 4, 8],\n    "*": [0, 4, 21, 14, 21, 4, 0],\n    "+": [0, 4, 4, 31, 4, 4, 0],\n    ",": [0, 0, 0, 0, 4, 4, 8],\n    "-": [0, 0, 0, 31, 0, 0, 0],\n    ".": [0, 0, 0, 0, 0, 12, 12],\n    "/": [1, 2, 4, 8, 16, 0, 0],\n    "0": [14, 17, 19, 21, 25, 17, 14],\n    "1": [4, 12, 4, 4, 4, 4, 14],\n    "2": [14, 17, 1, 2, 4, 8, 31],\n    "3": [30, 1, 1, 14, 1, 1, 30],\n    "4": [2, 6, 10, 18, 31, 2, 2],\n    "5": [31, 16, 16, 30, 1, 1, 30],\n    "6": [14, 16, 16, 30, 17, 17, 14],\n    "7": [31, 1, 2, 4, 8, 8, 8],\n    "8": [14, 17, 17, 14, 17, 17, 14],\n    "9": [14, 17, 17, 15, 1, 1, 14],\n    ":": [0, 12, 12, 0, 12, 12, 0],\n    ";": [0, 12, 12, 0, 4, 4, 8],\n    "<": [2, 4, 8, 16, 8, 4, 2],\n    "=": [0, 0, 31, 0, 31, 0, 0],\n    ">": [8, 4, 2, 1, 2, 4, 8],\n    "?": [14, 17, 1, 2, 4, 0, 4],\n    "@": [14, 17, 1, 13, 21, 21, 14],\n    "A": [14, 17, 17, 31, 17, 17, 17],\n    "B": [30, 17, 17, 30, 17, 17, 30],\n    "C": [14, 17, 16, 16, 16, 17, 14],\n    "D": [30, 17, 17, 17, 17, 17, 30],\n    "E": [31, 16, 16, 30, 16, 16, 31],\n    "F": [31, 16, 16, 30, 16, 16, 16],\n    "G": [14, 17, 16, 23, 17, 17, 14],\n    "H": [17, 17, 17, 31, 17, 17, 17],\n    "I": [14, 4, 4, 4, 4, 4, 14],\n    "J": [7, 2, 2, 2, 18, 18, 12],\n    "K": [17, 18, 20, 24, 20, 18, 17],\n    "L": [16, 16, 16, 16, 16, 16, 31],\n    "M": [17, 27, 21, 21, 17, 17, 17],\n    "N": [17, 25, 21, 19, 17, 17, 17],\n    "O": [14, 17, 17, 17, 17, 17, 14],\n    "P": [30, 17, 17, 30, 16, 16, 16],\n    "Q": [14, 17, 17, 17, 21, 18, 13],\n    "R": [30, 17, 17, 30, 20, 18, 17],\n    "S": [15, 16, 16, 14, 1, 1, 30],\n    "T": [31, 4, 4, 4, 4, 4, 4],\n    "U": [17, 17, 17, 17, 17, 17, 14],\n    "V": [17, 17, 17, 17, 17, 10, 4],\n    "W": [17, 17, 17, 21, 21, 21, 10],\n    "X": [17, 17, 10, 4, 10, 17, 17],\n    "Y": [17, 17, 10, 4, 4, 4, 4],\n    "Z": [31, 1, 2, 4, 8, 16, 31],\n    "[": [14, 8, 8, 8, 8, 8, 14],\n    "\\\\": [16, 8, 4, 2, 1, 0, 0],\n    "]": [14, 2, 2, 2, 2, 2, 14],\n    "^": [4, 10, 17, 0, 0, 0, 0],\n    "_": [0, 0, 0, 0, 0, 0, 31],\n    "`": [8, 4, 2, 0, 0, 0, 0],\n    "{": [2, 4, 4, 8, 4, 4, 2],\n    "|": [4, 4, 4, 0, 4, 4, 4],\n    "}": [8, 4, 4, 2, 4, 4, 8],\n    "~": [0, 0, 8, 21, 2, 0, 0],\n}\n\nfor char in "abcdefghijklmnopqrstuvwxyz":\n    FONT_5X7[char] = FONT_5X7[char.upper()]\n\n\ndef png_chunk(kind, data):\n    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)\n\n\ndef write_png(path, width, height, pixels):\n    raw = bytearray()\n\n    for y in range(height):\n        raw.append(0)\n        start = y * width * 3\n        raw.extend(pixels[start:start + width * 3])\n\n    data = b"\\x89PNG\\r\\n\\x1a\\n"\n    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))\n    data += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))\n    data += png_chunk(b"IEND", b"")\n    path.write_bytes(data)\n\n\ndef draw_rect(pixels, width, height, x1, y1, x2, y2, color):\n    x1 = max(0, min(width, x1))\n    x2 = max(0, min(width, x2))\n    y1 = max(0, min(height, y1))\n    y2 = max(0, min(height, y2))\n\n    for y in range(y1, y2):\n        row = y * width * 3\n        for x in range(x1, x2):\n            idx = row + x * 3\n            pixels[idx:idx + 3] = bytes(color)\n\n\ndef draw_circle(pixels, width, height, cx, cy, radius, color):\n    rr = radius * radius\n\n    for y in range(cy - radius, cy + radius + 1):\n        if y < 0 or y >= height:\n            continue\n\n        for x in range(cx - radius, cx + radius + 1):\n            if x < 0 or x >= width:\n                continue\n\n            if (x - cx) ** 2 + (y - cy) ** 2 <= rr:\n                idx = (y * width + x) * 3\n                pixels[idx:idx + 3] = bytes(color)\n\n\ndef draw_text(pixels, width, height, x, y, text, color, scale=2, line_gap=2):\n    cursor_x = x\n    cursor_y = y\n    char_width = 6 * scale\n    line_height = 7 * scale + line_gap\n\n    for char in text:\n        if char == "\\n":\n            cursor_x = x\n            cursor_y += line_height\n            continue\n\n        if char == "\\t":\n            cursor_x += char_width * 4\n            continue\n\n        glyph = FONT_5X7.get(char, FONT_5X7.get("?"))\n\n        for gy, row in enumerate(glyph):\n            for gx in range(5):\n                if row & (1 << (4 - gx)):\n                    draw_rect(\n                        pixels,\n                        width,\n                        height,\n                        cursor_x + gx * scale,\n                        cursor_y + gy * scale,\n                        cursor_x + (gx + 1) * scale,\n                        cursor_y + (gy + 1) * scale,\n                        color,\n                    )\n\n        cursor_x += char_width\n\n        if cursor_x > width - char_width:\n            cursor_x = x\n            cursor_y += line_height\n\n        if cursor_y > height - line_height:\n            break\n\nTERMINAL_PALETTE = {\n    "black": (0, 0, 0),\n    "red": (205, 49, 49),\n    "green": (13, 188, 121),\n    "brown": (229, 229, 16),\n    "yellow": (229, 229, 16),\n    "blue": (36, 114, 200),\n    "magenta": (188, 63, 188),\n    "cyan": (17, 168, 205),\n    "white": (229, 229, 229),\n    "brightblack": (102, 102, 102),\n    "brightred": (241, 76, 76),\n    "brightgreen": (35, 209, 139),\n    "brightyellow": (245, 245, 67),\n    "brightblue": (59, 142, 234),\n    "brightmagenta": (214, 112, 214),\n    "brightcyan": (41, 184, 219),\n    "brightwhite": (255, 255, 255),\n}\n\nFONT_PATHS = [\n    BASE_DIR / "assets/fonts/DejaVuSansMono.ttf",\n    "assets/fonts/DejaVuSansMono.ttf",\n    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",\n    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",\n    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",\n]\n\nTERMUX_PILLOW_FREETYPE_HELP = (\n    "TrueType fonts unavailable; screenshots will use Pillow\'s default font.\\n"\n    "If you are running this in Termux, install FreeType support and reinstall Pillow:\\n"\n    "  pkg install freetype libjpeg-turbo zlib python\\n"\n    "  pip uninstall -y pillow\\n"\n    "  pip install --no-cache-dir --force-reinstall pillow\\n"\n    "If pip still builds Pillow without _imagingft, use Termux\'s package instead:\\n"\n    "  pip uninstall -y pillow\\n"\n    "  pkg install python-pillow"\n)\n\n\ndef xterm_color(index):\n    index = max(0, min(255, int(index)))\n\n    if index < 16:\n        palette = [\n            (0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16),\n            (36, 114, 200), (188, 63, 188), (17, 168, 205), (229, 229, 229),\n            (102, 102, 102), (241, 76, 76), (35, 209, 139), (245, 245, 67),\n            (59, 142, 234), (214, 112, 214), (41, 184, 219), (255, 255, 255),\n        ]\n        return palette[index]\n\n    if 16 <= index <= 231:\n        index -= 16\n        r = index // 36\n        g = (index % 36) // 6\n        b = index % 6\n        steps = [0, 95, 135, 175, 215, 255]\n        return (steps[r], steps[g], steps[b])\n\n    shade = 8 + (index - 232) * 10\n    return (shade, shade, shade)\n\n\ndef resolve_terminal_color(value, default_color):\n    if value is None:\n        return default_color\n\n    if isinstance(value, int):\n        return xterm_color(value)\n\n    name = str(value).lower().strip().replace("-", "")\n\n    if name in {"default", ""}:\n        return default_color\n\n    if name.startswith("#"):\n        name = name[1:]\n\n    if len(name) == 6 and all(char in "0123456789abcdef" for char in name):\n        return tuple(int(name[i:i + 2], 16) for i in (0, 2, 4))\n\n    if name.startswith("ansi"):\n        name = name[4:]\n\n    return TERMINAL_PALETTE.get(name) or default_color\n\n\ndef brighten(color):\n    return tuple(min(255, int(channel * 1.25) + 18) for channel in color)\n\n\ndef load_terminal_font(size):\n    global truetype_available\n    global truetype_warning_shown\n\n    if truetype_available:\n        for font_path in FONT_PATHS:\n            if not Path(font_path).is_file():\n                continue\n\n            try:\n                return ImageFont.truetype(str(font_path), size=size)\n            except ImportError as e:\n                truetype_available = False\n\n                if not truetype_warning_shown:\n                    print(f"{TERMUX_PILLOW_FREETYPE_HELP}\\nOriginal error: {e}")\n                    truetype_warning_shown = True\n\n                break\n            except Exception as e:\n                if not truetype_warning_shown:\n                    print(f"Font load failed ({font_path}); using Pillow default font: {e}")\n                    truetype_warning_shown = True\n\n    return ImageFont.load_default()\n\n\ndef font_bbox(font, text):\n    if hasattr(font, "getbbox"):\n        return font.getbbox(text)\n\n    if hasattr(font, "getsize"):\n        width, height = font.getsize(text)\n        return (0, 0, width, height)\n\n    return (0, 0, 10, 18)\n\n\ndef terminal_cell(screen, row, col):\n    line = screen.buffer.get(row, {})\n    return line.get(col)\n\n\ndef screen_rows(screen):\n    rows = []\n    history = getattr(screen, "history", None)\n\n    if history is not None:\n        rows.extend(list(history.top))\n\n    rows.extend(screen.buffer.get(row, {}) for row in range(screen.lines))\n    return rows\n\n\ndef row_has_text(row):\n    return any(getattr(cell, "data", " ") != " " for cell in row.values())\n\n\ndef terminal_has_text(screen=None):\n    screen = screen or terminal_screen\n    return any(row_has_text(row) for row in screen_rows(screen))\n\n\ndef terminal_snapshot_lines():\n    lines = []\n\n    for row in screen_rows(terminal_screen):\n        chars = []\n        for col in range(terminal_screen.columns):\n            cell = row.get(col)\n            chars.append(getattr(cell, "data", " ") if cell else " ")\n        lines.append("".join(chars).rstrip())\n\n    return lines\n\n\ndef feed_terminal_screen(data):\n    if not data:\n        return\n\n    try:\n        terminal_stream.feed(data)\n    except Exception as e:\n        print(f"Terminal emulator feed error: {e}")\n\n\ndef reset_terminal_screen():\n    global terminal_screen\n    global terminal_stream\n    global terminal_waiting_prompt\n    global terminal_external_prompt\n\n    terminal_screen = pyte.HistoryScreen(TERM_COLUMNS, TERM_LINES, history=TERM_SCROLLBACK)\n    terminal_stream = pyte.Stream(terminal_screen)\n    terminal_waiting_prompt = False\n    terminal_external_prompt = False\n\n\ndef resize_terminal(cols, lines):\n    global TERM_COLUMNS\n    global TERM_LINES\n    global terminal_screen\n    global terminal_stream\n\n    cols = max(40, min(240, int(cols)))\n    lines = max(12, min(80, int(lines)))\n    TERM_COLUMNS = cols\n    TERM_LINES = lines\n\n    try:\n        shell.setwinsize(lines, cols)\n    except Exception:\n        pass\n\n    try:\n        terminal_screen.resize(lines, cols)\n    except Exception:\n        terminal_screen = pyte.HistoryScreen(cols, lines, history=TERM_SCROLLBACK)\n        terminal_stream = pyte.Stream(terminal_screen)\n\n    return cols, lines\n\n\ndef parse_terminal_size(value):\n    match = re.fullmatch(r"\\s*(\\d{2,3})\\s*[x, ]\\s*(\\d{2,3})\\s*", value)\n\n    if not match:\n        raise ValueError("usage: $tt size COLSxROWS, example: $tt size 120x36")\n\n    return int(match.group(1)), int(match.group(2))\n\n\ndef short_cwd(path):\n    home = Path.home()\n\n    if path == home:\n        return "~"\n\n    try:\n        return "~/" + str(path.relative_to(home))\n    except ValueError:\n        return str(path)\n\n\ndef update_shell_cwd(command):\n    global shell_cwd\n\n    try:\n        parts = shlex.split(command)\n    except ValueError:\n        return\n\n    if not parts or parts[0] != "cd":\n        return\n\n    target = Path.home() if len(parts) == 1 else Path(parts[1]).expanduser()\n\n    if not target.is_absolute():\n        target = shell_cwd / target\n\n    shell_cwd = target.resolve(strict=False)\n\n\ndef feed_terminal_prompt(command="", newline=True, replace_current=False):\n    user = os.environ.get("USER") or "user"\n    host = socket.gethostname().split(".")[0]\n    cwd = short_cwd(shell_cwd)\n\n    if replace_current and terminal_has_text():\n        prefix = "\\r\\x1b[2K"\n    else:\n        prefix = "\\r\\n" if terminal_has_text() and getattr(terminal_screen.cursor, "x", 0) else ""\n\n    suffix = "\\r\\n" if newline else ""\n    command_text = f" {command}" if command else ""\n    prompt = f"{prefix}\\x1b[1;32m{user}@{host}\\x1b[0m:\\x1b[1;34m{cwd}\\x1b[0m${command_text}{suffix}"\n    feed_terminal_screen(prompt)\n\n\ndef fallback_text_to_screen(content):\n    screen = pyte.HistoryScreen(TERM_COLUMNS, TERM_LINES, history=TERM_SCROLLBACK)\n    stream = pyte.Stream(screen)\n    stream.feed(clean_output(content).replace("\\r", ""))\n    return screen\n\n\n\ndef render_terminal_image(content, wide=False, use_terminal=True, command_line=None):\n    theme = SHOT_THEMES.get(shot_theme, SHOT_THEMES["black"])\n    screen = terminal_screen\n\n    if not use_terminal or not terminal_has_text(screen):\n        screen = fallback_text_to_screen(content or "Output buffer is empty.")\n\n    cols = screen.columns\n    all_rows = screen_rows(screen)\n    max_rows = SHOT_RENDER_ROWS if wide else min(SHOT_RENDER_ROWS, 64)\n    start_row = max(0, len(all_rows) - max_rows)\n    rendered_rows = all_rows[start_row:]\n    command_line = (command_line or "").strip()\n    rendered_lines = [\n        "".join(getattr(row.get(col), "data", " ") if row.get(col) else " " for col in range(cols)).rstrip()\n        for row in rendered_rows\n    ]\n    command_is_visible = any(line.endswith(f"$ {command_line}") for line in rendered_lines)\n    show_command_header = bool(command_line and not command_is_visible)\n    rows = (len(rendered_rows) or screen.lines) + (1 if show_command_header else 0)\n    font_size = 16 if wide else 17\n    font = load_terminal_font(font_size)\n    title_font = load_terminal_font(16)\n    bbox = font_bbox(font, "M")\n    cell_width = max(9, bbox[2] - bbox[0] + 1)\n    cell_height = max(18, bbox[3] - bbox[1] + 7)\n    pad_x = 22 if wide else 26\n    pad_top = 64\n    pad_bottom = 22\n    title_height = 46\n    width = pad_x * 2 + cols * cell_width\n    height = pad_top + rows * cell_height + pad_bottom\n\n    image = Image.new("RGB", (width, height), theme["bg"])\n    draw = ImageDraw.Draw(image)\n    draw.rectangle((0, 0, width, title_height), fill=theme["bar"])\n    draw.rectangle((0, title_height, width, title_height + 1), fill=theme["line"])\n    draw.ellipse((18, 15, 31, 28), fill=(255, 95, 87))\n    draw.ellipse((42, 15, 55, 28), fill=(255, 189, 46))\n    draw.ellipse((66, 15, 79, 28), fill=(40, 200, 64))\n    draw.text((100, 13), shot_title[:100], fill=theme["title"], font=title_font)\n\n    history_len = len(list(getattr(getattr(screen, "history", None), "top", [])))\n    cursor_row = history_len + getattr(screen.cursor, "y", -1)\n    cursor_col = getattr(screen.cursor, "x", -1)\n    visible_cursor_row = cursor_row - start_row + (1 if show_command_header else 0)\n    cursor_visible = 0 <= visible_cursor_row < rows and 0 <= cursor_col < cols\n\n    row_offset = 0\n\n    if show_command_header:\n        user = os.environ.get("USER") or "user"\n        host = socket.gethostname().split(".")[0]\n        prompt_text = f"{user}@{host}:{short_cwd(shell_cwd)}$ "\n        draw.text((pad_x, pad_top), prompt_text[:cols], fill=resolve_terminal_color("brightgreen", theme["text"]), font=font)\n        prompt_width = min(len(prompt_text), cols) * cell_width\n        draw.text((pad_x + prompt_width, pad_top), command_line[:max(0, cols - len(prompt_text))], fill=theme["text"], font=font)\n        row_offset = 1\n\n    for row_index, row_data in enumerate(rendered_rows):\n        y = pad_top + (row_index + row_offset) * cell_height\n        for col in range(cols):\n            cell = row_data.get(col)\n            char = getattr(cell, "data", " ") if cell else " "\n\n            if not char or char == "\\x00":\n                char = " "\n\n            fg = resolve_terminal_color(getattr(cell, "fg", None), theme["text"])\n            bg = resolve_terminal_color(getattr(cell, "bg", None), theme["bg"])\n            is_cursor = cursor_visible and (row_index + row_offset) == visible_cursor_row and col == cursor_col\n\n            if cell and getattr(cell, "reverse", False):\n                fg, bg = bg, fg\n\n            if cell and getattr(cell, "bold", False):\n                fg = brighten(fg)\n\n            if cell and getattr(cell, "dim", False):\n                fg = tuple(max(0, int(channel * 0.55)) for channel in fg)\n\n            if is_cursor:\n                bg = theme.get("cursor", theme["text"])\n                fg = theme.get("cursor_text", theme["bg"])\n\n            x = pad_x + col * cell_width\n\n            if bg != theme["bg"] or is_cursor:\n                draw.rectangle((x, y, x + cell_width, y + cell_height), fill=bg)\n\n            if char != " ":\n                draw.text((x, y), char, fill=fg, font=font)\n\n            if cell and getattr(cell, "underscore", False):\n                draw.line((x, y + cell_height - 3, x + cell_width, y + cell_height - 3), fill=fg)\n\n            if cell and getattr(cell, "strikethrough", False):\n                draw.line((x, y + cell_height // 2, x + cell_width, y + cell_height // 2), fill=fg)\n\n    return image\n\n\nasync def send_terminal_screenshot(event, content, wide=False, save_path=None, use_terminal=True, command_line=None):\n    try:\n        image = render_terminal_image(content, wide=wide, use_terminal=use_terminal, command_line=command_line)\n\n        if save_path:\n            image_path = Path(save_path).expanduser()\n            image_path.parent.mkdir(parents=True, exist_ok=True)\n            image.save(image_path, "PNG")\n            await reply_file(event, image_path, f"Terminal screenshot saved: {image_path}")\n            return\n\n        with tempfile.TemporaryDirectory() as tmp_dir:\n            image_path = Path(tmp_dir) / "telegram-terminal.png"\n            image.save(image_path, "PNG")\n            await reply_file(event, image_path, "Terminal screenshot:")\n\n    except Exception as e:\n        await event.reply(tg_code(f"Screenshot Error:\\n{type(e).__name__}: {e}"))\n\n\ndef gif_terminal_frame(image):\n    palette_container = getattr(Image, "Palette", None)\n    palette_mode = getattr(palette_container, "ADAPTIVE", None) if palette_container else None\n    dither_container = getattr(Image, "Dither", None)\n    dither_mode = getattr(dither_container, "NONE", None) if dither_container else None\n\n    if palette_mode is None:\n        palette_mode = Image.ADAPTIVE\n\n    if dither_mode is None:\n        dither_mode = Image.NONE\n\n    frame = image.convert("P", palette=palette_mode, colors=256, dither=dither_mode)\n    frame.info.pop("transparency", None)\n    return frame\n\n\ndef save_terminal_live_gif(path, frames, seconds):\n    step = 1\n\n    while True:\n        selected = frames[::step]\n\n        if selected[-1] is not frames[-1]:\n            selected.append(frames[-1])\n\n        frame_duration = max(20, int(seconds * 1000 / len(selected)))\n        gif_frames = [frame if frame.mode == "P" else gif_terminal_frame(frame) for frame in selected]\n        gif_frames[0].save(\n            path,\n            "GIF",\n            save_all=True,\n            append_images=gif_frames[1:],\n            duration=frame_duration,\n            loop=0,\n            optimize=False,\n            disposal=1,\n            transparency=None,\n        )\n\n        if path.stat().st_size <= SHOT_LIVE_MAX_BYTES or len(selected) <= 2:\n            return len(selected), frame_duration\n\n        step *= 2\n\n\nasync def send_terminal_live_shot(event, content, seconds=SHOT_LIVE_SECONDS, wide=False, use_terminal=True, command_line=None):\n    try:\n        seconds = max(1, min(SHOT_LIVE_MAX_SECONDS, int(seconds)))\n        frame_count = max(2, int(seconds / SHOT_LIVE_INTERVAL) + 1)\n        frames = []\n\n        for frame_index in range(frame_count):\n            frame = render_terminal_image(content, wide=wide, use_terminal=use_terminal, command_line=command_line)\n            frames.append(gif_terminal_frame(frame))\n\n            if frame_index < frame_count - 1:\n                await asyncio.sleep(SHOT_LIVE_INTERVAL)\n\n        with tempfile.TemporaryDirectory() as tmp_dir:\n            image_path = Path(tmp_dir) / "telegram-terminal-live.gif"\n            frame_count, frame_duration = save_terminal_live_gif(image_path, frames, seconds)\n            caption = f"Terminal live shot ({seconds}s, {frame_count} frames):"\n            await reply_file(event, image_path, caption, force_document=True)\n\n    except Exception as e:\n        await event.reply(tg_code(f"Live Shot Error:\\n{type(e).__name__}: {e}"))\n\n\nasync def handle_editor_command(event, command):\n    global editor_state\n\n    if not command.startswith("ttedit"):\n        return False\n\n    rest = command[6:].strip()\n    editor_actions = {\n        "show", "ls", "view", "set", "replace", "insert", "ins", "append", "add",\n        "delete", "del", "rm", "undo", "find", "replace-all", "replaceall", "save",\n        "cancel", "close", "quit",\n    }\n\n    action_name = rest.split(maxsplit=1)[0].lower() if rest else ""\n\n    if rest and (action_name not in editor_actions or action_name == "open"):\n        if action_name == "open":\n            _, _, path_text = rest.partition(" ")\n        else:\n            path_text = rest\n\n        if not path_text:\n            await event.reply(tg_code("Usage: $ttedit open <file>"))\n            return True\n\n        path = Path(path_text).expanduser()\n\n        try:\n            if path.exists():\n                content = path.read_text(encoding="utf-8", errors="replace")\n                lines = content.splitlines()\n            else:\n                lines = []\n\n            editor_state = {\n                "path": path,\n                "lines": lines,\n                "dirty": False,\n                "undo": [],\n            }\n\n            await event.reply(tg_code(editor_preview()))\n\n        except Exception as e:\n            await event.reply(tg_code(f"Editor open error:\\n{e}"))\n\n        return True\n\n    if not editor_state:\n        await event.reply(tg_code("No file is open. Use $ttedit open <file> first."))\n        return True\n\n    action_text = rest\n\n    if not action_text:\n        await event.reply(tg_code(editor_preview()))\n        return True\n\n    action, _, rest = action_text.partition(" ")\n    action = action.lower()\n\n    try:\n        lines = editor_state["lines"]\n\n        def snapshot():\n            editor_state["undo"].append(lines.copy())\n            editor_state["undo"] = editor_state["undo"][-20:]\n\n        if action in ("show", "ls", "view"):\n            await event.reply(tg_code(editor_preview()))\n\n        elif action == "set":\n            line_text, _, new_text = rest.partition(" ")\n            line_no = int(line_text)\n\n            if line_no < 1 or line_no > len(lines):\n                raise ValueError(f"line must be between 1 and {len(lines)}")\n\n            snapshot()\n            lines[line_no - 1] = new_text\n            editor_state["dirty"] = True\n            await event.reply(tg_code(f"Line {line_no} updated.\\n\\n{editor_preview()}"))\n\n        elif action in ("insert", "ins"):\n            line_text, _, new_text = rest.partition(" ")\n            line_no = int(line_text)\n\n            if line_no < 1 or line_no > len(lines) + 1:\n                raise ValueError(f"line must be between 1 and {len(lines) + 1}")\n\n            snapshot()\n            lines.insert(line_no - 1, new_text)\n            editor_state["dirty"] = True\n            await event.reply(tg_code(f"Inserted at line {line_no}.\\n\\n{editor_preview()}"))\n\n        elif action in ("append", "add"):\n            snapshot()\n            lines.append(rest)\n            editor_state["dirty"] = True\n            await event.reply(tg_code(f"Appended at line {len(lines)}.\\n\\n{editor_preview()}"))\n\n        elif action in ("delete", "del", "rm"):\n            if not lines:\n                raise ValueError("file is empty")\n\n            start, end = parse_line_range(rest, len(lines))\n            snapshot()\n            del lines[start - 1:end]\n            editor_state["dirty"] = True\n            await event.reply(tg_code(f"Deleted line(s) {start}-{end}.\\n\\n{editor_preview()}"))\n\n        elif action == "undo":\n            if not editor_state["undo"]:\n                raise ValueError("nothing to undo")\n\n            editor_state["lines"] = editor_state["undo"].pop()\n            editor_state["dirty"] = True\n            await event.reply(tg_code(f"Undo applied.\\n\\n{editor_preview()}"))\n\n        elif action == "find":\n            needle = rest\n\n            if not needle:\n                raise ValueError("usage: $ttedit find <text>")\n\n            matches = [f"{idx}: {line}" for idx, line in enumerate(lines, start=1) if needle in line]\n            await event.reply(tg_code("\\n".join(matches[:80]) if matches else f"No matches: {needle}"))\n\n        elif action in ("replace", "replace-all", "replaceall"):\n            old_text, _, new_text = rest.partition(" ")\n\n            if not old_text:\n                raise ValueError("usage: $ttedit replace <old> <new>")\n\n            count = 0\n            snapshot()\n\n            for idx, line in enumerate(lines):\n                if old_text in line:\n                    count += line.count(old_text)\n                    lines[idx] = line.replace(old_text, new_text)\n\n                    if action == "replace":\n                        break\n\n            if count == 0:\n                editor_state["undo"].pop()\n                await event.reply(tg_code(f"No matches: {old_text}"))\n            else:\n                editor_state["dirty"] = True\n                await event.reply(tg_code(f"Replaced {count} occurrence(s).\\n\\n{editor_preview()}"))\n\n        elif action == "save":\n            path = editor_state["path"]\n            path.parent.mkdir(parents=True, exist_ok=True)\n            content = "\\n".join(lines) + ("\\n" if lines else "")\n            path.write_text(content, encoding="utf-8")\n            editor_state["dirty"] = False\n            await event.reply(tg_code(f"Saved: {path}"))\n\n        elif action in ("cancel", "close", "quit"):\n            path = editor_state["path"]\n            dirty = editor_state["dirty"]\n            editor_state = None\n            suffix = "Unsaved changes discarded." if dirty else "Editor closed."\n            await event.reply(tg_code(f"{suffix}\\n{path}"))\n\n        else:\n            await event.reply(tg_code(editor_preview()))\n\n    except Exception as e:\n        await event.reply(tg_code(f"Editor error:\\n{e}"))\n\n    return True\n\nasync def send_file(event, command):\n    args = split_command_args(command)\n\n    if len(args) < 2:\n        await event.reply(tg_code("Usage: $ttget <file>"))\n        return True\n\n    path = Path(args[1]).expanduser()\n\n    if not path.is_file():\n        await event.reply(tg_code(f"File not found: {path}"))\n        return True\n\n    await reply_file(event, path, f"File: {path}")\n    return True\n\n\nasync def receive_file(event, command):\n    args = split_command_args(command)\n\n    if len(args) < 2:\n        await event.reply(tg_code("Usage: send a document with caption \'$ttput <path>\'"))\n        return True\n\n    if not event.message.file:\n        await event.reply(tg_code("Attach a document and use caption: $ttput <path>"))\n        return True\n\n    path = Path(args[1]).expanduser()\n    path.parent.mkdir(parents=True, exist_ok=True)\n    await event.message.download_media(file=str(path))\n    await event.reply(tg_code(f"Uploaded: {path}"))\n    return True\n\n\ndef restart_shell():\n    global shell\n    global terminal_screen\n    global terminal_stream\n    global terminal_waiting_prompt\n    global terminal_external_prompt\n    global pending_shell_data\n\n    try:\n        if shell.isalive():\n            shell.terminate(force=True)\n    except Exception:\n        pass\n\n    shell = spawn_shell()\n    terminal_screen = pyte.HistoryScreen(TERM_COLUMNS, TERM_LINES, history=TERM_SCROLLBACK)\n    terminal_stream = pyte.Stream(terminal_screen)\n    terminal_waiting_prompt = False\n    terminal_external_prompt = False\n    pending_shell_data = ""\n\n\nasync def shell_watchdog():\n    global current_command_started_at\n    global current_command_last_activity\n\n    while True:\n        await asyncio.sleep(SHELL_WATCHDOG_POLL_INTERVAL)\n\n        try:\n            if not shell.isalive():\n                print("Watchdog: shell dead; restarting")\n                restart_shell()\n                reset_runtime_state()\n                continue\n\n            if not current_command_started_at or not current_command_last_activity:\n                continue\n\n            if not command_output_buffer:\n                continue\n\n            idle_for = time.time() - current_command_last_activity\n\n            if idle_for < SHELL_WATCHDOG_IDLE_TIMEOUT:\n                continue\n\n            print(f"Watchdog: shell idle for {int(idle_for)}s; restarting")\n\n            if current_event:\n                try:\n                    await current_event.reply(\n                        tg_code(\n                            "Shell watchdog restarted the session after inactivity."\n                        )\n                    )\n                except Exception:\n                    pass\n\n            restart_shell()\n            reset_runtime_state()\n\n        except Exception as e:\n            print(f"Watchdog Error: {e}")\n\n\ndef command_program_names(command):\n    names = []\n\n    for segment in command.split("|"):\n        try:\n            parts = shlex.split(segment)\n        except ValueError:\n            parts = segment.split()\n\n        if parts:\n            names.append(Path(parts[0]).name)\n\n    return names\n\n\ndef is_interactive_shell_command(command):\n    try:\n        parts = shlex.split(command)\n    except ValueError:\n        parts = command.split()\n\n    if not parts:\n        return False\n\n    name = Path(parts[0]).name\n    full_screen_commands = {\n        "tmux", "screen", "vim", "vi", "nvim", "nano", "micro", "emacs",\n        "less", "more", "man", "top", "htop", "btop", "watch", "ssh",\n        "su", "login", "ftp", "sftp", "mysql", "psql", "sqlite3", "python",\n        "python3", "node", "irb", "php", "lua", "radian", "R", "cmatrix",\n        "asciiquarium", "cava", "hollywood",\n    }\n    non_interactive_flags = {"-c", "--command", "--version", "-V", "--help", "-h"}\n\n    if "|" in command and any(program in full_screen_commands for program in command_program_names(command)):\n        return True\n\n    if name == "sudo":\n        if any(arg in {"-i", "-s", "su"} for arg in parts[1:]):\n            return True\n\n        idx = 1\n        options_with_values = {"-u", "--user", "-g", "--group", "-p", "--prompt", "-C", "--close-from", "-h", "--host"}\n\n        while idx < len(parts):\n            arg = parts[idx]\n\n            if arg == "--":\n                idx += 1\n                break\n\n            if arg in options_with_values:\n                idx += 2\n                continue\n\n            if arg.startswith("-"):\n                idx += 1\n                continue\n\n            break\n\n        return idx < len(parts) and is_interactive_shell_command(" ".join(shlex.quote(arg) for arg in parts[idx:]))\n\n    if name == "tmux":\n        detached = {"-d", "detach", "detach-client", "ls", "list-sessions", "kill-session", "kill-server"}\n        return not any(arg in detached for arg in parts[1:])\n\n    if name in {"python", "python3", "node", "php", "lua", "R"}:\n        return not any(arg in non_interactive_flags for arg in parts[1:])\n\n    return name in full_screen_commands\n\n\ndef is_shell_exit_command(command):\n    try:\n        parts = shlex.split(command)\n    except ValueError:\n        parts = command.split()\n\n    return bool(parts) and parts[0] in {"exit", "logout"}\n\n\ndef shell_status():\n    status = "alive" if shell.isalive() else "dead"\n    editor = "none"\n\n    if editor_state:\n        dirty = "modified" if editor_state["dirty"] else "saved"\n        editor = f"{editor_state[\'path\']} ({dirty})"\n\n    return f"Shell: {status}\\nEditor: {editor}\\nBuffer: {len(output_buffer)} chars"\n\n\n\ndef buffer_status():\n    session_lines = len(output_buffer.splitlines()) if output_buffer else 0\n    command_lines = len(command_output_buffer.splitlines()) if command_output_buffer else 0\n    logging = "on" if log_enabled else "off"\n    editor = "none"\n\n    if editor_state:\n        dirty = "modified" if editor_state["dirty"] else "saved"\n        editor = f"{editor_state[\'path\']} ({dirty})"\n\n    log_path = str(current_log_path) if current_log_path else "none"\n    last = last_command or "none"\n\n    return (\n        f"Session buffer: {len(output_buffer)} chars, {session_lines} lines\\n"\n        f"Current command buffer: {len(command_output_buffer)} chars, {command_lines} lines\\n"\n        f"Last command: {last}\\n"\n        f"Logging: {logging}\\n"\n        f"Current log: {log_path}\\n"\n        f"Editor: {editor}"\n    )\n\n\n\ndef format_duration(seconds):\n    seconds = int(seconds)\n    days, seconds = divmod(seconds, 86400)\n    hours, seconds = divmod(seconds, 3600)\n    minutes, seconds = divmod(seconds, 60)\n    parts = []\n\n    if days:\n        parts.append(f"{days}d")\n\n    if hours or parts:\n        parts.append(f"{hours}h")\n\n    if minutes or parts:\n        parts.append(f"{minutes}m")\n\n    parts.append(f"{seconds}s")\n    return " ".join(parts)\n\n\ndef system_uptime():\n    try:\n        uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])\n    except Exception:\n        return "unavailable"\n\n    return format_duration(uptime_seconds)\n\n\ndef uptime_text(mode=""):\n    bot = format_duration(time.time() - started_at)\n\n    if mode == "bot":\n        return f"Bot uptime: {bot}"\n\n    if mode in {"system", "sys", "vps"}:\n        return f"System uptime: {system_uptime()}"\n\n    return f"Bot uptime: {bot}\\nSystem uptime: {system_uptime()}"\n\n\ndef about_text():\n    status = "alive" if shell.isalive() else "dead"\n    logging = "on" if log_enabled else "off"\n    editor = "none"\n\n    if editor_state:\n        dirty = "modified" if editor_state["dirty"] else "saved"\n        editor = f"{editor_state[\'path\']} ({dirty})"\n\n    return (\n        f"telegram-terminal {VERSION}\\n"\n        f"Uptime: {format_duration(time.time() - started_at)}\\n"\n        f"Shell: {status}\\n"\n        f"Session buffer: {len(output_buffer)} chars\\n"\n        f"Last command: {last_command or \'none\'}\\n"\n        f"Logging: {logging}\\n"\n        f"Editor: {editor}"\n    )\n\n\nasync def stream_shell_output():\n\n    global current_msg\n    global current_event\n    global output_buffer\n    global command_output_buffer\n    global command_file_output_buffer\n    global output_revision\n    global current_output_mode\n    global current_output_no_session\n    global current_shot_clear_after\n    global current_shot_save_path\n    global current_shot_wide\n    global current_shot_command\n    global current_command_started_at\n    global current_command_last_activity\n    global pending_shell_data\n    global terminal_waiting_prompt\n    global terminal_external_prompt\n\n    last_edit = 0\n    last_text = ""\n    seen_revision = output_revision\n\n    while True:\n\n        await asyncio.sleep(0.03)\n\n        if seen_revision != output_revision:\n            seen_revision = output_revision\n            last_edit = 0\n            last_text = ""\n\n        try:\n\n            if shell.isalive():\n\n                data = shell.read_nonblocking(\n                    size=4096,\n                    timeout=0.01\n                )\n\n                if data:\n\n                    command_finished = False\n\n                    if current_command_started_at:\n                        pending_shell_data += data\n\n                        if DONE_MARKER in pending_shell_data:\n                            raw_data = pending_shell_data.replace(DONE_MARKER, "", 1)\n                            pending_shell_data = ""\n                            command_finished = True\n                        elif len(pending_shell_data) > MARKER_HOLD_SIZE:\n                            raw_data = pending_shell_data[:-MARKER_HOLD_SIZE]\n                            pending_shell_data = pending_shell_data[-MARKER_HOLD_SIZE:]\n                        else:\n                            continue\n                    else:\n                        raw_data = data\n                        pending_shell_data = ""\n\n                    feed_terminal_screen(raw_data)\n                    cleaned = clean_output(raw_data)\n\n                    if not current_output_no_session:\n                        output_buffer += cleaned\n\n                    command_output_buffer += cleaned\n                    command_file_output_buffer += cleaned\n\n                    output_buffer = output_buffer[-MAX_BUFFER_SIZE:]\n                    command_output_buffer = command_output_buffer[-MAX_BUFFER_SIZE:]\n\n                    now = time.time()\n                    current_command_last_activity = now\n\n                    trimmed = command_message_preview()\n\n                    if command_finished:\n                        if not terminal_external_prompt:\n                            feed_terminal_prompt(newline=False)\n                            terminal_waiting_prompt = True\n                        else:\n                            terminal_waiting_prompt = False\n\n                        if current_msg:\n\n                            try:\n\n                                if current_log_path:\n                                    write_command_log(last_command or "", command_file_output_buffer, current_log_path)\n\n                                if current_output_mode == "ss":\n                                    target_event = current_event or current_msg\n                                    await send_terminal_screenshot(\n                                        target_event,\n                                        command_output_buffer,\n                                        wide=current_shot_wide,\n                                        save_path=current_shot_save_path,\n                                        command_line=current_shot_command,\n                                    )\n\n                                    try:\n                                        await current_msg.delete()\n                                    except Exception:\n                                        pass\n\n                                    if current_shot_clear_after:\n                                        output_buffer = ""\n                                        reset_terminal_screen()\n                                        output_revision += 1\n\n                                    current_output_mode = "chat"\n                                    current_output_no_session = False\n                                    current_shot_clear_after = False\n                                    current_shot_save_path = None\n                                    current_shot_wide = False\n                                    current_shot_command = None\n                                    current_msg = None\n                                    current_event = None\n                                    command_output_buffer = ""\n                                    command_file_output_buffer = ""\n                                    current_command_started_at = None\n                                    current_command_last_activity = None\n                                    last_text = trimmed\n                                    last_edit = now\n                                    continue\n\n                                if len(command_file_output_buffer) > MAX_MESSAGE_OUTPUT:\n                                    suffix = "\\n\\nOutput is large. Sending full output as .txt..."\n\n                                    if current_log_path:\n                                        suffix += f"\\nLog saved: {current_log_path}"\n\n                                    try:\n                                        await current_msg.edit(\n                                            tg_code(trimmed + suffix)\n                                        )\n                                    except Exception as e:\n                                        print(f"Final large-output edit error: {e}")\n\n                                    target_event = current_event or current_msg\n                                    await send_text_file(\n                                        target_event,\n                                        command_file_output_buffer,\n                                        "telegram-terminal-output.txt",\n                                        "Full output:"\n                                    )\n                                else:\n                                    suffix = f"\\n\\nLog saved: {current_log_path}" if current_log_path else ""\n                                    await current_msg.edit(\n                                        tg_code(trimmed + suffix)\n                                    )\n\n                                current_msg = None\n                                current_event = None\n                                command_output_buffer = ""\n                                command_file_output_buffer = ""\n                                current_output_mode = "chat"\n                                current_output_no_session = False\n                                current_shot_clear_after = False\n                                current_shot_save_path = None\n                                current_shot_command = None\n                                current_command_started_at = None\n                                current_command_last_activity = None\n                                last_text = trimmed\n                                last_edit = now\n\n                            except Exception as e:\n\n                                print(\n                                    f"Final Flush Error: {e}"\n                                )\n\n                    elif (\n                        current_msg and\n                        now - last_edit >= EDIT_INTERVAL\n                    ):\n\n                        if trimmed != last_text:\n\n                            try:\n\n                                await current_msg.edit(\n                                    tg_code(trimmed)\n                                )\n\n                                last_text = trimmed\n                                last_edit = now\n\n                            except FloodWaitError as e:\n\n                                print(\n                                    f"FloodWait: "\n                                    f"{e.seconds}s"\n                                )\n\n                                await asyncio.sleep(\n                                    e.seconds\n                                )\n\n                            except Exception as e:\n\n                                print(\n                                    f"Edit Error: {e}"\n                                )\n\n        except pexpect.exceptions.TIMEOUT:\n            pass\n\n        except pexpect.exceptions.EOF:\n            print("Shell EOF; restarting shell")\n            restart_shell()\n            reset_runtime_state()\n            last_text = ""\n            last_edit = 0\n\n        except Exception as e:\n            print(f"Stream Error: {e}")\n\n\nasync def shell_handler(event):\n\n    global current_msg\n    global current_event\n    global output_buffer\n    global command_output_buffer\n    global command_file_output_buffer\n    global output_revision\n    global last_command\n    global log_enabled\n    global current_log_path\n    global current_output_mode\n    global current_output_no_session\n    global current_shot_clear_after\n    global current_shot_save_path\n    global current_shot_wide\n    global current_shot_command\n    global current_command_started_at\n    global current_command_last_activity\n    global pending_shell_data\n    global terminal_waiting_prompt\n    global terminal_external_prompt\n    global shot_theme\n    global shot_title\n\n    if not event.out:\n        return\n\n    text = event.raw_text.strip()\n\n    if not text.startswith("$"):\n        return\n\n    command = text[1:].strip()\n\n    if not command:\n        return\n\n    command_key = command.lower().replace("+", " ").replace("-", " ")\n    command_key = " ".join(command_key.split())\n\n    aliases = {\n        "ctrl c": "ctrlc",\n        "control c": "ctrlc",\n        "ctrl d": "ctrld",\n        "control d": "ctrld",\n        "ctrl z": "ctrlz",\n        "control z": "ctrlz",\n        "ctrl b": "ctrlb",\n        "control b": "ctrlb",\n        "ctrl a": "ctrla",\n        "control a": "ctrla",\n        "ctrl l": "ctrll",\n        "control l": "ctrll",\n        "seta cima": "up",\n        "seta baixo": "down",\n        "seta esquerda": "left",\n        "seta direita": "right",\n    }\n\n    command_key = aliases.get(command_key, command_key)\n\n    current_time = datetime.now().strftime("%H:%M:%S")\n\n    if command_key in {"help", "tt help"}:\n        await event.reply(tg_code(build_help()))\n        return\n\n    if command_key == "tt status":\n        await event.reply(tg_code(shell_status()))\n        return\n\n    if command_key == "tt version":\n        await event.reply(tg_code(f"telegram-terminal {VERSION}"))\n        return\n\n    if command_key == "tt ping":\n        started = time.time()\n        msg = await event.reply(tg_code("pong"))\n        latency = int((time.time() - started) * 1000)\n        await msg.edit(tg_code(f"pong {latency}ms"))\n        return\n\n    if command_key == "tt uptime" or command_key.startswith("tt uptime "):\n        args = command.split(maxsplit=2)\n        mode = args[2].lower() if len(args) > 2 else ""\n\n        if mode and mode not in {"bot", "system", "sys", "vps"}:\n            await event.reply(tg_code("Usage: $tt uptime [bot|system]"))\n            return\n\n        await event.reply(tg_code(uptime_text(mode)))\n        return\n\n    if command_key == "tt about":\n        await event.reply(tg_code(about_text()))\n        return\n\n    if command_key == "tt size" or command_key.startswith("tt size "):\n        if command_key == "tt size":\n            await event.reply(tg_code(f"Terminal size: {TERM_COLUMNS}x{TERM_LINES}"))\n            return\n\n        try:\n            cols, lines = parse_terminal_size(command.split(maxsplit=2)[2])\n            cols, lines = resize_terminal(cols, lines)\n            reset_terminal_screen()\n            output_revision += 1\n            await event.reply(tg_code(f"Terminal resized: {cols}x{lines}"))\n        except Exception as e:\n            await event.reply(tg_code(str(e)))\n\n        return\n\n    if command_key in {"tt theme", "shot theme"} or command_key.startswith("tt theme ") or command_key.startswith("shot theme "):\n        args = command.split(maxsplit=2)\n\n        if len(args) < 3:\n            names = ", ".join(sorted(SHOT_THEMES))\n            await event.reply(tg_code(f"Current theme: {shot_theme}\\nAvailable: {names}"))\n            return\n\n        selected = args[2].strip().lower()\n\n        if selected not in SHOT_THEMES:\n            names = ", ".join(sorted(SHOT_THEMES))\n            await event.reply(tg_code(f"Unknown theme: {selected}\\nAvailable: {names}"))\n            return\n\n        shot_theme = selected\n        await event.reply(tg_code(f"Screenshot theme: {shot_theme}"))\n        return\n\n    if command_key in {"tt title", "shot title"} or command_key.startswith("tt title ") or command_key.startswith("shot title "):\n        args = command.split(maxsplit=2)\n\n        if len(args) < 3 or not args[2].strip():\n            await event.reply(tg_code(f"Screenshot title: {shot_title}"))\n            return\n\n        shot_title = args[2].strip()[:100]\n        await event.reply(tg_code(f"Screenshot title: {shot_title}"))\n        return\n\n    if command_key == "tt reset" or command_key == "tt cleanup":\n        reset_runtime_state()\n\n        if not shell.isalive():\n            restart_shell()\n\n        await event.reply(tg_code("Runtime state reset."))\n        return\n\n    if command_key == "buf tail" or command_key.startswith("buf tail "):\n        tail_arg = command[8:].strip()\n        content = tail_output(tail_arg)\n\n        if len(content) > MAX_MESSAGE_OUTPUT:\n            await send_text_file(\n                event,\n                content,\n                "telegram-terminal-tail.txt",\n                "Tail output:"\n            )\n        else:\n            await event.reply(tg_code(content))\n\n        return\n\n    if command.startswith("shot run "):\n        run_text = command[9:].strip()\n        current_shot_clear_after = False\n        current_output_no_session = False\n        current_shot_save_path = None\n        current_shot_wide = False\n        current_shot_command = None\n\n        while True:\n            if run_text.startswith("clear "):\n                current_shot_clear_after = True\n                run_text = run_text[6:].strip()\n                continue\n\n            if run_text.startswith("wide "):\n                current_shot_wide = True\n                run_text = run_text[5:].strip()\n                continue\n\n            if run_text.startswith("--no-session "):\n                current_output_no_session = True\n                run_text = run_text[13:].strip()\n                continue\n\n            break\n\n        command = run_text\n\n        if not command:\n            await event.reply(tg_code("Usage: $shot run <command>"))\n            return\n\n        command_key = command.lower().replace("+", " ").replace("-", " ")\n        command_key = " ".join(command_key.split())\n        command_key = aliases.get(command_key, command_key)\n        current_output_mode = "ss"\n        current_shot_command = command\n\n    elif command_key == "shot run":\n        await event.reply(tg_code("Usage: $shot run <command>"))\n        return\n\n    if command_key == "shot" or command_key.startswith("shot "):\n        shot_args = command.split()\n        wide = False\n        clear_after = False\n        live = False\n        live_seconds = SHOT_LIVE_SECONDS\n        tail_arg = ""\n        idx = 1\n\n        while idx < len(shot_args):\n            arg = shot_args[idx]\n\n            if arg == "wide":\n                wide = True\n            elif arg == "clear":\n                clear_after = True\n            elif arg == "live":\n                live = True\n            elif live and arg.isdigit():\n                live_seconds = arg\n            else:\n                tail_arg = arg\n\n            idx += 1\n\n        use_terminal = not tail_arg\n\n        if live:\n            await send_terminal_live_shot(\n                event,\n                tail_output(tail_arg),\n                seconds=live_seconds,\n                wide=wide,\n                use_terminal=use_terminal,\n            )\n        else:\n            await send_terminal_screenshot(\n                event,\n                tail_output(tail_arg),\n                wide=wide,\n                save_path=None,\n                use_terminal=use_terminal,\n            )\n\n        if clear_after:\n            output_buffer = ""\n            reset_terminal_screen()\n            output_revision += 1\n\n        return\n\n    if command_key == "buf send" or command_key.startswith("buf send "):\n        args = command.split(maxsplit=2)\n        filename = args[2].strip() if len(args) > 2 else "telegram-terminal-buffer.txt"\n\n        if not filename.endswith(".txt"):\n            filename += ".txt"\n\n        if not output_buffer:\n            await event.reply(tg_code("Output buffer is empty."))\n            return\n\n        await send_text_file(\n            event,\n            output_buffer,\n            Path(filename).name,\n            "Output buffer:"\n        )\n        return\n\n    if command_key == "buf save" or command_key.startswith("buf save "):\n        args = command.split(maxsplit=2)\n\n        if len(args) < 3:\n            await event.reply(tg_code("Usage: $buf save <file.txt>"))\n            return\n\n        if not output_buffer:\n            await event.reply(tg_code("Output buffer is empty."))\n            return\n\n        save_path = Path(args[2]).expanduser()\n        save_path.parent.mkdir(parents=True, exist_ok=True)\n        save_path.write_text(output_buffer, encoding="utf-8", errors="replace")\n        await event.reply(tg_code(f"Output buffer saved: {save_path}"))\n        return\n\n    if command_key == "tt save session" or command_key.startswith("tt save session "):\n        args = command.split(maxsplit=2)\n        filename = args[2].strip() if len(args) > 2 else "telegram-terminal-session.txt"\n\n        if not filename.endswith(".txt"):\n            filename += ".txt"\n\n        if not output_buffer:\n            await event.reply(tg_code("Output buffer is empty."))\n            return\n\n        save_path = Path(filename).expanduser()\n        save_path.parent.mkdir(parents=True, exist_ok=True)\n        save_path.write_text(output_buffer, encoding="utf-8", errors="replace")\n        await event.reply(tg_code(f"Session saved: {save_path}"))\n        return\n\n    if command_key == "buf status":\n        await event.reply(tg_code(buffer_status()))\n        return\n\n    if command_key == "buf clear":\n        output_buffer = ""\n        command_output_buffer = ""\n        command_file_output_buffer = ""\n        pending_shell_data = ""\n        current_msg = None\n        current_event = None\n        current_output_mode = "chat"\n        current_output_no_session = False\n        current_shot_clear_after = False\n        current_shot_save_path = None\n        current_shot_wide = False\n        current_shot_command = None\n        current_command_started_at = None\n        current_command_last_activity = None\n        reset_terminal_screen()\n        output_revision += 1\n        await event.reply(tg_code("Session output buffer and current command state cleared."))\n        return\n\n    if command_key.startswith("buf "):\n        await event.reply(tg_code("Usage: $buf status | $buf clear | $buf tail | $buf send | $buf save"))\n        return\n\n    if command_key == "cmd history" or command_key.startswith("cmd history "):\n        args = command.split(maxsplit=2)\n        limit = 30\n\n        if len(args) > 2:\n            try:\n                limit = max(1, int(args[2]))\n            except ValueError:\n                limit = 30\n\n        await event.reply(tg_code(history_preview(limit)))\n        return\n\n    if command_key == "cmd last":\n        await event.reply(tg_code(last_command or "No command has been executed yet."))\n        return\n\n    if command_key.startswith("cmd rerun "):\n        try:\n            index = int(command.split(maxsplit=2)[2])\n\n            if index < 1 or index > len(command_history):\n                raise ValueError\n\n            command = command_history[index - 1]\n            command_key = command.lower().replace("+", " ").replace("-", " ")\n            command_key = " ".join(command_key.split())\n            command_key = aliases.get(command_key, command_key)\n\n            await event.reply(tg_code(f"Rerun #{index}:\\n{command}"))\n        except Exception:\n            await event.reply(tg_code(f"Usage: $cmd rerun N\\n\\n{history_preview()}"))\n            return\n\n    if command_key == "out log" or command_key.startswith("out log "):\n        arg = command[7:].strip().lower()\n\n        if arg == "on":\n            log_enabled = True\n            await event.reply(tg_code("Logging enabled. Outputs will be saved in logs/."))\n        elif arg == "off":\n            log_enabled = False\n            await event.reply(tg_code("Logging disabled."))\n        elif arg == "status" or not arg:\n            status = "on" if log_enabled else "off"\n            await event.reply(tg_code(f"Logging: {status}"))\n        else:\n            await event.reply(tg_code("Usage: $out log on | $out log off | $out log status"))\n\n        return\n\n    if command_key in ("tt restart", "tt restart shell"):\n        restart_shell()\n        reset_runtime_state()\n        await event.reply(tg_code("Shell restarted."))\n        return\n\n    if await handle_editor_command(event, command):\n        return\n\n    if command.startswith("ttget "):\n        await send_file(event, command)\n        return\n\n    if command.startswith("ttput "):\n        await receive_file(event, command)\n        return\n\n    control_sequences = {\n        "ctrlc": "\\x03",\n        "ctrld": "\\x04",\n        "ctrlz": "\\x1a",\n        "ctrlb": "\\x02",\n        "ctrla": "\\x01",\n        "ctrll": "\\x0c",\n        "tab": "\\t",\n        "up": "\\x1b[A",\n        "down": "\\x1b[B",\n        "right": "\\x1b[C",\n        "left": "\\x1b[D",\n    }\n\n    named_keys = {\n        "esc": "\\x1b",\n        "backspace": "\\x7f",\n        "delete": "\\x1b[3~",\n        "home": "\\x1b[H",\n        "end": "\\x1b[F",\n        "pgup": "\\x1b[5~",\n        "pgdn": "\\x1b[6~",\n        "space": " ",\n        "f1": "\\x1bOP",\n        "f2": "\\x1bOQ",\n        "f3": "\\x1bOR",\n        "f4": "\\x1bOS",\n        "f5": "\\x1b[15~",\n        "f6": "\\x1b[17~",\n        "f7": "\\x1b[18~",\n        "f8": "\\x1b[19~",\n        "f9": "\\x1b[20~",\n        "f10": "\\x1b[21~",\n        "f11": "\\x1b[23~",\n        "f12": "\\x1b[24~",\n    }\n\n    if command_key == "enter":\n        try:\n            shell.sendline("")\n            print(f"[{current_time}] You Sent ENTER")\n            await event.reply(tg_code("ENTER sent"))\n        except Exception as e:\n            await event.reply(tg_code(f"ENTER Error:\\n{e}"))\n        return\n\n    if command_key in control_sequences:\n        try:\n            interrupted_started_at = current_command_started_at\n            shell.send(control_sequences[command_key])\n\n            if command_key == "ctrlc" and interrupted_started_at:\n                await asyncio.sleep(0.2)\n\n                if shell.isalive():\n                    shell.sendline(f"printf \'\\n{DONE_MARKER}\\n\'")\n\n                await asyncio.sleep(1.0)\n\n                if current_command_started_at == interrupted_started_at:\n                    preview = command_message_preview()\n                    suffix = "\\n\\nInterrupted."\n\n                    if current_msg:\n                        try:\n                            await current_msg.edit(tg_code((preview + suffix)[-MAX_MESSAGE_OUTPUT:]))\n                        except Exception as e:\n                            print(f"Ctrl+C final edit error: {e}")\n\n                    command_output_buffer = ""\n                    command_file_output_buffer = ""\n                    pending_shell_data = ""\n                    current_msg = None\n                    current_event = None\n                    current_output_mode = "chat"\n                    current_output_no_session = False\n                    current_shot_clear_after = False\n                    current_shot_save_path = None\n                    current_shot_wide = False\n                    current_shot_command = None\n                    current_command_started_at = None\n                    current_command_last_activity = None\n                    terminal_waiting_prompt = False\n                    feed_terminal_prompt(newline=False)\n                    output_revision += 1\n\n            print(f"[{current_time}] You Sent {command_key.upper()}")\n            await event.reply(tg_code(f"{command_key.upper()} sent"))\n        except Exception as e:\n            await event.reply(tg_code(f"Control Error:\\n{e}"))\n        return\n\n    if command.startswith("key "):\n        key_name = command[4:].strip().lower()\n\n        if key_name not in named_keys:\n            await event.reply(tg_code(f"Unknown key: {key_name}"))\n            return\n\n        try:\n            shell.send(named_keys[key_name])\n            await event.reply(tg_code(f"{key_name.upper()} sent"))\n        except Exception as e:\n            await event.reply(tg_code(f"Key Error:\\n{e}"))\n        return\n\n    if command.startswith("ttpaste "):\n        try:\n            pasted = command[8:]\n            shell.send(pasted)\n            await event.reply(tg_code(f"Pasted {len(pasted)} chars"))\n        except Exception as e:\n            await event.reply(tg_code(f"Paste Error:\\n{e}"))\n        return\n\n    if command.startswith("ttinput "):\n\n        user_input = command[8:]\n\n        try:\n\n            shell.sendline(user_input)\n\n            print(\n                f"[{current_time}] "\n                f"Input: {user_input}"\n            )\n\n            if terminal_external_prompt:\n                await event.reply(tg_code("Input sent"))\n            else:\n                await event.reply(\n                    tg_code(f"Input Sent:\\n{user_input}")\n                )\n\n        except Exception as e:\n\n            await event.reply(\n                tg_code(f"Input Error:\\n{e}")\n            )\n\n        return\n\n    if is_interactive_shell_command(command) or (terminal_external_prompt and is_shell_exit_command(command)):\n        print(\n            f"[{current_time}] "\n            f"Interactive: {command}"\n        )\n\n        last_command = command\n        command_history.append(command)\n        command_history[:] = command_history[-200:]\n        command_output_buffer = ""\n        command_file_output_buffer = ""\n        output_revision += 1\n        current_event = event\n\n        if not terminal_external_prompt:\n            # Interactive commands such as su/ssh own the prompt after this point.\n            # Start their virtual screen clean so old local prompts do not mix with\n            # the real remote/user prompt.\n            reset_terminal_screen()\n        terminal_waiting_prompt = False\n\n        current_command_started_at = None\n        current_command_last_activity = None\n        current_msg = None\n\n        try:\n            shell.sendline(command)\n            terminal_external_prompt = not is_shell_exit_command(command)\n\n            if current_output_mode == "ss":\n                await asyncio.sleep(1)\n                await send_terminal_screenshot(event, command_output_buffer, wide=current_shot_wide, save_path=current_shot_save_path, command_line=current_shot_command)\n\n                if current_shot_clear_after:\n                    output_buffer = ""\n                    reset_terminal_screen()\n                    output_revision += 1\n\n                current_output_mode = "chat"\n                current_output_no_session = False\n                current_shot_clear_after = False\n                current_shot_save_path = None\n                current_shot_wide = False\n                current_shot_command = None\n            else:\n                await event.reply(tg_code("Interactive command sent"))\n        except Exception as e:\n            await event.reply(tg_code(f"Interactive Error:\\n{e}"))\n\n        return\n\n    print(\n        f"[{current_time}] "\n        f"You Executed: {command}"\n    )\n\n    last_command = command\n    command_history.append(command)\n    command_history[:] = command_history[-200:]\n\n    command_output_buffer = ""\n    command_file_output_buffer = ""\n    output_revision += 1\n    current_event = event\n\n    if not terminal_external_prompt:\n        feed_terminal_prompt(command, replace_current=terminal_waiting_prompt)\n    terminal_waiting_prompt = False\n    update_shell_cwd(command)\n    current_command_started_at = time.time()\n    current_command_last_activity = current_command_started_at\n    current_log_path = create_log_path(command) if log_enabled else None\n\n    if current_output_mode == "ss":\n        current_msg = await event.reply(tg_code(f"Capturing:\\n{command}"))\n    else:\n        current_msg = await event.reply(\n            tg_code(f"Running:\\n{command}")\n        )\n\n    try:\n\n        builtin_commands = [\n            "cd",\n            "export",\n            "alias",\n            "source",\n            "set",\n            "unset",\n            "history",\n            "exit"\n        ]\n\n        first_word = command.strip().split()[0]\n\n        if first_word in builtin_commands:\n\n            shell.sendline(\n                f"{command}; echo {DONE_MARKER}"\n            )\n\n        else:\n\n            shell.sendline(\n                f"stdbuf -oL -eL {command}; "\n                f"echo {DONE_MARKER}"\n            )\n\n    except Exception as e:\n\n        await current_msg.edit(\n            tg_code(f"Execution Error:\\n{e}")\n        )\n\n\nasync def start(topuser_client):\n    global client\n    client = topuser_client\n    asyncio.create_task(stream_shell_output())\n    asyncio.create_task(shell_watchdog())\n    client.add_event_handler(shell_handler, events.NewMessage)\n\n\nasync def main():\n    raise RuntimeError("telegram-terminal is embedded in TopUser. Run personal-userbot.py instead.")\n\n\nif __name__ == "__main__":\n    asyncio.run(main())\n'


def load_telegram_terminal():
    module = types.ModuleType("topuser_telegram_terminal")
    module.__file__ = str(Path(__file__).resolve())
    exec(TELEGRAM_TERMINAL_SOURCE, module.__dict__)
    return module


TELEGRAM_TERMINAL = load_telegram_terminal()
TELEGRAM_TERMINAL_HELP = getattr(TELEGRAM_TERMINAL, "HELP_TEXT", FALLBACK_TELEGRAM_TERMINAL_HELP)

HELP_TEXT = f"""TopUser online

{TOPUSER_HELP}

{TELEGRAM_TERMINAL_HELP}
"""


def tg_code(text):
    safe = str(text).replace("```", "`\u200b``")
    return f"```{safe}```"


def parse_command(text, prefix=COMMAND_PREFIX):
    text = text or ""

    if not text.startswith(prefix):
        return None, ""

    body = text[len(prefix):].strip()

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
    return lower.startswith(("utm_", "__cft__")) or lower in TRACKING_PARAMS


def extract_url(text):
    match = URL_RE.search(text or "")

    if not match:
        return ""

    return match.group(0).rstrip(".,;:!?")


def clean_host(host):
    return host.lower().removeprefix("www.").removeprefix("m.").removeprefix("mobile.")


def host_matches(host, suffix):
    return host == suffix or host.endswith(f".{suffix}")


def should_resolve_url(url):
    parts = urlsplit(url)
    return clean_host(parts.netloc) in SHORT_URL_HOSTS


def resolve_redirect_url(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        return response.geturl()


async def resolve_url_if_needed(url):
    if not should_resolve_url(url):
        return url

    try:
        return await asyncio.to_thread(resolve_redirect_url, url)
    except Exception:
        return url


def redirect_target_from_query(host, query_items):
    if not any(host_matches(host, suffix) for suffix in REDIRECT_HOST_SUFFIXES):
        return ""

    for key, value in query_items:
        if key.lower() not in REDIRECT_PARAM_NAMES:
            continue

        target = unquote(value.strip())

        if extract_url(target):
            return target

    return ""


def clean_tracking_url(url, depth=0):
    if depth > 5:
        return url

    parts = urlsplit(url)
    host = clean_host(parts.netloc)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    target = redirect_target_from_query(host, query_items)

    if target:
        return clean_tracking_url(target, depth + 1)

    if host_matches(host, "pinterest.com"):
        pin_match = re.match(r"^(/pin/[^/]+)", parts.path)

        if pin_match:
            return urlunsplit((parts.scheme, parts.netloc, f"{pin_match.group(1)}/", "", parts.fragment))

    if any(host_matches(host, suffix) for suffix in DROP_ALL_QUERY_DOMAINS):
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))

    query = [
        (key, value)
        for key, value in query_items
        if value != "" and not is_tracking_param(key)
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

    resolved_url = await resolve_url_if_needed(url)
    await event.reply(clean_tracking_url(resolved_url))


def startup_notice_text():
    return (
        f"{TOPUSER_ASCII}\n\n"
        "TopUser is online.\n\n"
        "Personal userbot commands:\n"
        "  .help  - open the TopUser command menu\n\n"
        "Telegram Terminal commands:\n"
        "  $help  - open the terminal command menu\n\n"
        "Prefixes:\n"
        "  . for TopUser\n"
        "  $ for Telegram Terminal"
    )


def cleanup_files(*paths):
    for path in paths:
        if not path:
            continue

        try:
            Path(path).unlink(missing_ok=True)
        except OSError as e:
            log(f"cleanup failed for {path}: {e}")


def log(message):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def print_startup_console():
    print("\033[2J\033[H", end="")
    print(TOPUSER_ASCII)
    print()
    print("TopUser running")
    print("Personal Userbot: prefix . | help .help")
    print("Telegram Terminal: prefix $ | help $help")
    print("Logs:", flush=True)


async def keep_account_online():
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
        except Exception as e:
            log(f"online presence refresh failed: {e}")

        await asyncio.sleep(ONLINE_REFRESH_SECONDS)


def ask_keep_online():
    answer = input("Keep account online while TopUser is running? [yes/no]: ").strip().lower()
    return answer in {"yes", "y"}


def quote_font_candidates(bold=False):
    env_dir = os.environ.get("TOPUSER_FONT_DIR", "").strip()
    roots = [Path.cwd(), Path(__file__).resolve().parent]
    names = [
        "Lato-Bold.ttf" if bold else "Lato-Regular.ttf",
        "Inter-Bold.ttf" if bold else "Inter-Regular.ttf",
        "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf",
        "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
    ]

    if env_dir:
        roots.insert(0, Path(env_dir).expanduser())

    for root in roots:
        for folder in (root / "assets" / "fonts", root / "fonts", root):
            for name in names:
                yield folder / name

    system_dirs = [
        Path("/usr/share/fonts/truetype/lato"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/local/share/fonts"),
        Path("/system/fonts"),
        Path("/data/data/com.termux/files/usr/share/fonts/TTF"),
        Path("/data/data/com.termux/files/usr/share/fonts"),
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path.home() / "Library" / "Fonts",
        Path("C:/Windows/Fonts"),
    ]

    for folder in system_dirs:
        for name in names:
            yield folder / name


def load_quote_font(size, bold=False):
    seen = set()

    for candidate in quote_font_candidates(bold):
        key = str(candidate)

        if key in seen:
            continue

        seen.add(key)

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


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_text_to_width(draw, text, font, max_width):
    lines = []

    for raw_line in text.splitlines() or [""]:
        words = raw_line.split()

        if not words:
            lines.append("")
            continue

        line = ""

        for word in words:
            candidate = word if not line else f"{line} {word}"

            if text_size(draw, candidate, font)[0] <= max_width:
                line = candidate
                continue

            if line:
                lines.append(line)
                line = ""

            current = ""

            for char in word:
                piece = current + char

                if text_size(draw, piece, font)[0] <= max_width:
                    current = piece
                else:
                    if current:
                        lines.append(current)
                    current = char

            line = current

        lines.append(line)

    return "\n".join(lines).strip()



def draw_rounded_shadow(base, box, radius=34, shadow_offset=(0, 10), blur=18, alpha=120):
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    shadow = Image.new("RGBA", (w + blur * 4, h + blur * 4), (0, 0, 0, 0))
    mask = Image.new("L", shadow.size, 0)
    draw = ImageDraw.Draw(mask)
    origin = blur * 2
    draw.rounded_rectangle(
        (origin + shadow_offset[0], origin + shadow_offset[1], origin + shadow_offset[0] + w, origin + shadow_offset[1] + h),
        radius=radius,
        fill=alpha,
    )
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(blur)))
    base.alpha_composite(shadow, (x1 - origin, y1 - origin))


def circle_crop(image, size):
    image = ImageOps.fit(image.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(image, (0, 0), mask)
    return output


def compact_stat(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0"

    return f"{value:,}".replace(",", ".")


def mixerno_value(items, name, default=None):
    if not isinstance(items, list):
        return default

    for item in items:
        if isinstance(item, dict) and item.get("value") == name:
            return item.get("count", default)

    return default


def fetch_vegadata_stats():
    request = urllib.request.Request(
        VEGADATA_COUNTER_URL,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))

    if not isinstance(data, dict):
        raise RuntimeError("counter API returned an invalid response")

    subscribers = mixerno_value(data.get("counts"), "subscribers")
    if subscribers is None:
        subscribers = mixerno_value(data.get("counts"), "apisubscribers")

    if subscribers is None:
        raise RuntimeError("counter API did not return subscribers")

    return {
        "name": mixerno_value(data.get("user"), "name", "VegaData"),
        "avatar_url": mixerno_value(data.get("user"), "pfp"),
        "subscribers": int(subscribers),
        "views": mixerno_value(data.get("counts"), "views"),
        "videos": mixerno_value(data.get("counts"), "videos"),
        "goal": mixerno_value(data.get("counts"), "goal"),
    }


def fetch_remote_image(url):
    if not url:
        return None

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")

    with urllib.request.urlopen(request, timeout=30) as response:
        return Image.open(BytesIO(response.read())).convert("RGBA")


def draw_youtube_mark(draw, x, y, w, h):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=(255, 0, 0, 255))
    cx = x + w // 2 + 4
    cy = y + h // 2
    draw.polygon([(cx - 13, cy - 17), (cx - 13, cy + 17), (cx + 20, cy)], fill=(255, 255, 255, 255))


def render_vegadata_card(stats):
    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1120, 630
    image = Image.new("RGBA", (width, height), (6, 7, 10, 255))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        r = 6 + int(y * 10 / height)
        g = 7 + int(y * 12 / height)
        b = 10 + int(y * 20 / height)
        draw.line((0, y, width, y), fill=(r, g, b, 255))

    draw.rounded_rectangle((48, 48, width - 48, height - 48), radius=42, fill=(18, 20, 26, 245), outline=(255, 255, 255, 18), width=1)
    draw_rounded_shadow(image, (74, 80, width - 74, height - 76), radius=34, shadow_offset=(0, 14), blur=22, alpha=100)
    draw.rounded_rectangle((74, 80, width - 74, height - 76), radius=34, fill=(25, 27, 34, 255), outline=(255, 255, 255, 22), width=1)

    avatar_image = fetch_remote_image(stats.get("avatar_url"))
    avatar_size = 174
    avatar_x = 116
    avatar_y = 128
    draw.ellipse((avatar_x - 8, avatar_y - 8, avatar_x + avatar_size + 8, avatar_y + avatar_size + 8), fill=(255, 255, 255, 28))

    if avatar_image is not None:
        image.alpha_composite(circle_crop(avatar_image, avatar_size), (avatar_x, avatar_y))
    else:
        draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=(50, 54, 68, 255))
        fallback_font = load_quote_font(64, bold=True)
        initials = avatar_initials(stats.get("name", "VegaData"))
        tw, th = text_size(draw, initials, fallback_font)
        draw.text((avatar_x + (avatar_size - tw) / 2, avatar_y + (avatar_size - th) / 2 - 4), initials, font=fallback_font, fill=(245, 247, 250, 255))

    draw_youtube_mark(draw, 116, 344, 82, 58)

    name_font = load_quote_font(54, bold=True)
    label_font = load_quote_font(26, bold=True)
    big_font = load_quote_font(118, bold=True)
    small_font = load_quote_font(25)
    stat_font = load_quote_font(33, bold=True)

    draw.text((224, 344), stats.get("name") or "VegaData", font=name_font, fill=(248, 249, 252, 255))
    draw.text((224, 405), "youtube.com/@vegadata", font=small_font, fill=(155, 162, 176, 255))

    right_x = 405
    draw.text((right_x, 124), "INSCRITOS", font=label_font, fill=(255, 74, 74, 255))
    draw.text((right_x, 163), compact_stat(stats.get("subscribers")), font=big_font, fill=(255, 255, 255, 255))

    updated = datetime.now().strftime("%d/%m/%Y %H:%M")
    draw.text((right_x, 300), f"Atualizado em {updated}", font=small_font, fill=(139, 145, 158, 255))

    y = 472
    cards = [
        ("VIDEOS", compact_stat(stats.get("videos"))),
        ("VIEWS", compact_stat(stats.get("views"))),
        ("META", f"+{compact_stat(stats.get('goal'))}" if stats.get("goal") is not None else "--"),
    ]
    card_w = 246
    for index, (label, value) in enumerate(cards):
        x = 116 + index * (card_w + 28)
        draw.rounded_rectangle((x, y, x + card_w, y + 84), radius=22, fill=(34, 37, 47, 255), outline=(255, 255, 255, 16), width=1)
        draw.text((x + 22, y + 16), label, font=small_font, fill=(132, 139, 153, 255))
        draw.text((x + 22, y + 45), value, font=stat_font, fill=(240, 242, 246, 255))

    path = QUOTE_DIR / f"vegadata-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.png"
    image.convert("RGB").save(path, "PNG")
    return path


async def send_vegadata(event):
    status = await event.reply(tg_code("fetching @vegadata subscribers..."))
    path = None

    try:
        stats = await asyncio.to_thread(fetch_vegadata_stats)
        path = await asyncio.to_thread(render_vegadata_card, stats)
        caption = f"VegaData\nSubscribers: {compact_stat(stats.get('subscribers'))}\n{VEGADATA_CHANNEL_URL}"
        await client.send_file(
            event.chat_id,
            str(path),
            caption=caption,
            force_document=False,
            reply_to=topic_reply_to(event),
        )
        await status.delete()
        log(f".vegadata sent in chat {event.chat_id}: {stats.get('subscribers')}")
    except Exception as e:
        await status.edit(tg_code(f".vegadata failed: {e}"))
    finally:
        cleanup_files(path)


async def get_export_avatar_data(sender, name, size=36):
    sender_id = getattr(sender, "id", None) or name or "unknown"
    cache_key = (sender_id, size)

    if cache_key in EXPORT_AVATAR_CACHE:
        return EXPORT_AVATAR_CACHE[cache_key]

    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    avatar_path = QUOTE_DIR / f"export-avatar-{sender_id}.jpg"
    data_uri = ""

    try:
        downloaded = await client.download_profile_photo(sender, file=str(avatar_path)) if sender else None

        if downloaded and Path(downloaded).is_file():
            image = Image.open(downloaded).convert("RGB")
            image = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=38, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            data_uri = f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Export avatar failed: {e}")
    finally:
        cleanup_files(avatar_path)

    EXPORT_AVATAR_CACHE[cache_key] = data_uri
    return data_uri


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
            frame = Image.open(frame_path).convert("RGBA")
            cleanup_files(frame_path)
            return frame
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
            image = open_media_image(downloaded)
            cleanup_files(downloaded)
            return image
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
            cleanup_files(downloaded_path)
            return image

        frame = extract_video_frame(downloaded_path)

        if frame is not None:
            cleanup_files(downloaded_path)
            return frame

        cleanup_files(downloaded_path)
        return await download_media_thumbnail(reply)
    except Exception as e:
        print(f"Media download failed: {e}")
        return await download_media_thumbnail(reply)


def run_ffmpeg_144p_gif(input_path, output_path):
    if not shutil.which("ffmpeg"):
        raise FileNotFoundError("ffmpeg")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-filter_complex",
            "[0:v]fps=6,scale=trunc(iw*96/ih/2)*2:96:flags=neighbor,split[a][b];[a]palettegen=max_colors=16:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=8",
            "-an",
            "-loop",
            "0",
            "-f",
            "gif",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def save_image_as_gif(image, output_path):
    image = image.convert("RGBA")
    image = image.resize((max(1, int(image.size[0])), max(1, int(image.size[1]))), Image.Resampling.LANCZOS)
    palette = image.convert("P", palette=Image.ADAPTIVE, colors=128)
    palette.save(output_path, format="GIF", save_all=True, loop=0)


def save_image_as_photo(image, output_path):
    image = image.convert("RGB")
    width, height = image.size
    base = image.resize((max(1, width // 4), max(1, height // 4)), Image.Resampling.NEAREST)
    base = base.resize((width, height), Image.Resampling.NEAREST)
    base = ImageOps.posterize(base, 2)
    base.save(output_path, format="JPEG", quality=2, optimize=False, progressive=False)


def run_ffmpeg_144p_webm(input_path, output_path):
    if not shutil.which("ffmpeg"):
        raise FileNotFoundError("ffmpeg")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-t",
            "2.5",
            "-an",
            "-vf",
            "fps=5,scale=512:512:force_original_aspect_ratio=decrease:flags=neighbor,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000,format=yuva420p",
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "good",
            "-cpu-used",
            "8",
            "-row-mt",
            "1",
            "-auto-alt-ref",
            "0",
            "-crf",
            "63",
            "-b:v",
            "10k",
            "-f",
            "webm",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def save_image_as_sticker(image, output_path):
    image = image.convert("RGBA")
    width, height = image.size
    scale = min(512 / width, 512 / height)
    sticker_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    image = image.resize(sticker_size, Image.Resampling.NEAREST)
    image = ImageOps.posterize(image.convert("RGB"), 2).convert("RGBA")
    pixel_size = (max(1, sticker_size[0] // 8), max(1, sticker_size[1] // 8))
    image = image.resize(pixel_size, Image.Resampling.NEAREST).resize(sticker_size, Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - sticker_size[0]) // 2
    y = (512 - sticker_size[1]) // 2
    canvas.alpha_composite(image, (x, y))
    canvas.save(output_path, "WEBP", lossless=False, quality=1, method=6)


def parse_download_url(raw):
    return next((arg for arg in (raw or "").split() if extract_url(arg)), "")



NAYAN_API_BASE = "https://nayan-video-downloader.vercel.app"
NAYAN_AUDIO_COMMANDS = {"soundcloud", "sc"}

NAYAN_ENDPOINTS = {
    "api": "alldown",
    "all": "alldown",
    "alldl": "alldown",
    "alldown": "alldown",
    "video": "alldown",
    "yt": "ytdown",
    "youtube": "youtube",
    "ytdl": "ytdown",
    "tiktok": "tikdown",
    "tiktol": "tikdown",
    "tt": "tikdown",
    "tik": "tikdown",
    "fb": "fbdown2",
    "facebook": "fbdown2",
    "ig": "instagram",
    "insta": "instagram",
    "instagram": "instagram",
    "x": "twitterdown",
    "twitter": "twitterdown",
    "tweet": "twitterdown",
    "pin": "pintarest",
    "pinterest": "pintarest",
    "soundcloud": "soundcloud",
    "sc": "soundcloud",
    "terabox": "terabox",
    "tera": "terabox",
    "gdrive": "GDLink",
    "drive": "GDLink",
    "gdlink": "GDLink",
    "capcut": "capcut",
    "ndown": "ndown",
}


def nayan_endpoint_for_url(command_name, video_url):
    endpoint = NAYAN_ENDPOINTS.get(command_name, "alldown")

    if command_name not in {"api", "all", "alldl", "alldown", "video", "mp3"}:
        return endpoint

    host = clean_host(urlsplit(video_url).netloc)

    if host_matches(host, "instagram.com"):
        return "instagram"
    if host_matches(host, "tiktok.com"):
        return "tikdown"
    if host_matches(host, "youtube.com") or host_matches(host, "youtu.be"):
        return "ytdown"
    if host_matches(host, "x.com") or host_matches(host, "twitter.com"):
        return "twitterdown"
    if host_matches(host, "pinterest.com") or host == "pin.it":
        return "pintarest"
    if host_matches(host, "facebook.com") or host == "fb.watch":
        return "fbdown2"
    if host_matches(host, "capcut.com"):
        return "capcut"
    if host_matches(host, "soundcloud.com"):
        return "soundcloud"
    if host_matches(host, "terabox.com"):
        return "terabox"
    if host_matches(host, "drive.google.com"):
        return "GDLink"

    return endpoint


def nayan_api_url(endpoint, video_url):
    params = {"url": video_url}

    if endpoint == "fbdown2":
        params["key"] = "nayan"

    return f"{NAYAN_API_BASE}/{endpoint}?{urlencode(params)}"


def fetch_nayan_response(endpoint, video_url):
    request = urllib.request.Request(
        nayan_api_url(endpoint, video_url),
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read().decode("utf-8", errors="replace")

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def nayan_endpoint_candidates(command_name, video_url):
    primary = nayan_endpoint_for_url(command_name, video_url)
    candidates = [primary]

    if primary == "ytdown":
        candidates.append("youtube")
    elif primary == "youtube":
        candidates.append("ytdown")

    candidates.append("alldown")
    unique = []

    for endpoint in candidates:
        if endpoint not in unique:
            unique.append(endpoint)

    return unique


def fetch_nayan_audio_response(command_name, video_url):
    last_data = None

    for endpoint in nayan_endpoint_candidates(command_name, video_url):
        data = fetch_nayan_response(endpoint, video_url)
        last_data = data

        if nayan_best_audio_url(data):
            return data

    return last_data or {}


def collect_media_urls(value, parent_key=""):
    urls = []

    if isinstance(value, dict):
        for key, item in value.items():
            child_key = f"{parent_key}.{key}" if parent_key else str(key)
            urls.extend(collect_media_urls(item, child_key.lower()))
    elif isinstance(value, list):
        for item in value:
            urls.extend(collect_media_urls(item, parent_key))
    elif isinstance(value, str):
        text = value.strip()

        if text.startswith(("http://", "https://")):
            lower = text.lower()
            key = parent_key.lower()
            bad = any(word in key or word in lower for word in ("thumb", "cover", "avatar", "image", "photo", "music", "audio", "mp3"))
            good = any(word in key for word in ("video", "download", "url", "link", "hd", "sd", "nowm", "play"))
            score = 0

            if lower.split("?", 1)[0].endswith((".mp4", ".mov", ".webm", ".mkv")):
                score += 6

            if good:
                score += 4

            if "hd" in key:
                score += 2

            if bad:
                score -= 5

            urls.append((score, text))

    return urls


def nayan_best_media_url(data):
    urls = collect_media_urls(data)

    if not urls:
        return ""

    urls.sort(key=lambda item: item[0], reverse=True)
    return urls[0][1]


def collect_audio_urls(value, parent_key=""):
    urls = []

    if isinstance(value, dict):
        for key, item in value.items():
            child_key = f"{parent_key}.{key}" if parent_key else str(key)
            urls.extend(collect_audio_urls(item, child_key.lower()))
    elif isinstance(value, list):
        for item in value:
            urls.extend(collect_audio_urls(item, parent_key))
    elif isinstance(value, str):
        text = value.strip()

        if text.startswith(("http://", "https://")):
            lower = text.lower().split("?", 1)[0]
            key = parent_key.lower()
            score = 0

            if lower.endswith((".mp3", ".m4a", ".aac", ".ogg", ".wav", ".opus")):
                score += 10

            if any(word in key for word in ("audio", "music", "mp3", "sound", "song", "m4a", "opus")):
                score += 7

            if any(word in key for word in ("play", "stream", "download", "url", "link")):
                score += 2

            if lower.endswith((".mp4", ".mov", ".webm", ".mkv")):
                score -= 6

            if any(word in key or word in lower for word in ("thumb", "cover", "image", "photo", "avatar", "video")):
                score -= 4

            if score > 0:
                urls.append((score, text))

    return urls


def nayan_best_audio_url(data):
    urls = collect_audio_urls(data)

    if not urls:
        return ""

    urls.sort(key=lambda item: item[0], reverse=True)
    return urls[0][1]


def nayan_title(data):
    if isinstance(data, dict):
        for key in ("title", "name", "caption"):
            value = data.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()[:120]

        for value in data.values():
            title = nayan_title(value)

            if title:
                return title
    elif isinstance(data, list):
        for value in data:
            title = nayan_title(value)

            if title:
                return title

    return "video"


def download_remote_media(url, output_dir, filename="video.mp4"):
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(urlsplit(url).path).suffix

    if suffix and len(suffix) <= 8:
        filename = f"video{suffix}"

    path = output_dir / filename
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")

    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as output:
        shutil.copyfileobj(response, output)

    return path


async def nayan_download_link(event, raw_options="", command_name="video"):
    args = (raw_options or "").split()
    audio_mode = command_name in NAYAN_AUDIO_COMMANDS or any(arg.lower() in {"mp3", "audio", "music"} for arg in args)
    cleaned_options = " ".join(arg for arg in args if arg.lower() not in {"mp3", "audio", "music"})
    url = parse_download_url(cleaned_options)

    if not url:
        reply = await event.get_reply_message()
        url = extract_url(getattr(reply, "raw_text", "") if reply else "")

    if not url:
        await event.reply(tg_code(f"Use: .{command_name} [mp3] URL, or reply to a message with URL"))
        return

    endpoint = nayan_endpoint_for_url(command_name, url)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_dir = DOWNLOAD_DIR / f"nayan-{stamp}"
    status = await event.reply(tg_code("fetching audio..." if audio_mode else "fetching video..."))
    downloaded_path = None

    try:
        if audio_mode:
            data = await asyncio.to_thread(fetch_nayan_audio_response, command_name, url)
        else:
            data = await asyncio.to_thread(fetch_nayan_response, endpoint, url)

        media_url = nayan_best_audio_url(data) if audio_mode else nayan_best_media_url(data)

        if not media_url:
            if audio_mode:
                await status.edit(tg_code("API did not return a downloadable audio URL for this link."))
            else:
                await status.edit(tg_code("API did not return a downloadable video URL for this link."))
            return

        caption = nayan_title(data)

        try:
            await client.send_file(
                event.chat_id,
                media_url,
                caption=caption,
                force_document=False,
                reply_to=topic_reply_to(event),
            )
        except Exception:
            filename = "audio.mp3" if audio_mode else "video.mp4"
            downloaded_path = await asyncio.to_thread(download_remote_media, media_url, output_dir, filename)
            await client.send_file(
                event.chat_id,
                str(downloaded_path),
                caption=caption,
                force_document=False,
                reply_to=topic_reply_to(event),
            )

        await status.delete()
        log(f".{command_name} sent in chat {event.chat_id}: {media_url}")
    except Exception as e:
        await status.edit(tg_code(f"Download failed: {e}"))
    finally:
        if downloaded_path:
            cleanup_files(downloaded_path)
        try:
            output_dir.rmdir()
        except OSError:
            pass


async def download_mp3(event, raw_options=""):
    url = parse_download_url(raw_options)

    if not url:
        reply = await event.get_reply_message()
        url = extract_url(getattr(reply, "raw_text", "") if reply else "")

    if not url:
        await event.reply(tg_code("Use: .mp3 URL, or reply to a message with URL"))
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_dir = DOWNLOAD_DIR / f"mp3-{stamp}"
    status = await event.reply(tg_code("fetching mp3..."))
    downloaded_path = None

    try:
        data = await asyncio.to_thread(fetch_nayan_audio_response, "mp3", url)
        audio_url = nayan_best_audio_url(data)

        if not audio_url:
            await status.edit(tg_code("API did not return an audio URL for this link."))
            return

        caption = nayan_title(data)

        try:
            await client.send_file(
                event.chat_id,
                audio_url,
                caption=caption,
                force_document=False,
                reply_to=topic_reply_to(event),
            )
        except Exception:
            downloaded_path = await asyncio.to_thread(download_remote_media, audio_url, output_dir, "audio.mp3")
            await client.send_file(
                event.chat_id,
                str(downloaded_path),
                caption=caption,
                force_document=False,
                reply_to=topic_reply_to(event),
            )

        await status.delete()
        log(f".mp3 API sent in chat {event.chat_id}: {audio_url}")
    except Exception as e:
        await status.edit(tg_code(f"MP3 failed: {e}"))
    finally:
        if downloaded_path:
            cleanup_files(downloaded_path)
        try:
            output_dir.rmdir()
        except OSError:
            pass



async def download_link(event, raw_options=""):
    await nayan_download_link(event, raw_options, "api")


async def send_media_144p(event, raw_options=""):
    reply = await event.get_reply_message()

    if not reply or not getattr(reply, "media", None):
        await event.reply(tg_code("Reply to a photo, sticker or video with .144p"))
        return

    generated_paths = []
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    input_path = MEDIA_DIR / f"input-{reply.id}-{stamp}"
    output_path = MEDIA_DIR / f"144p-{reply.id}-{stamp}.gif"
    status = await event.reply(tg_code("destroying media quality..."))

    try:
        downloaded = await reply.download_media(file=str(input_path))

        if not downloaded:
            await status.edit(tg_code("Failed to download media"))
            return

        downloaded_path = Path(downloaded)
        generated_paths.append(downloaded_path)
        document = getattr(reply, "document", None)
        mime_type = getattr(document, "mime_type", "") if document else ""

        if getattr(reply, "sticker", None):
            if mime_type.startswith("video/") or downloaded_path.suffix.lower() == ".webm":
                webm_output = output_path.with_suffix(".webm")
                generated_paths.append(webm_output)
                await asyncio.to_thread(run_ffmpeg_144p_webm, downloaded_path, webm_output)
                await client.send_file(
                    event.chat_id,
                    str(webm_output),
                    force_document=False,
                    mime_type="video/webm",
                    attributes=[
                        DocumentAttributeSticker(alt="💬", stickerset=InputStickerSetEmpty()),
                        DocumentAttributeVideo(duration=1.5, w=384, h=384, nosound=True),
                    ],
                    reply_to=topic_reply_to(event),
                )
            else:
                image = open_media_image(downloaded_path)

                if image is None:
                    image = await download_media_thumbnail(reply)

                if image is None:
                    await status.edit(tg_code("Unsupported sticker for .144p"))
                    return

                sticker_output = output_path.with_suffix(".webp")
                generated_paths.append(sticker_output)
                await asyncio.to_thread(save_image_as_sticker, image, sticker_output)
                await client.send_file(
                    event.chat_id,
                    str(sticker_output),
                    force_document=False,
                    attributes=[DocumentAttributeSticker(alt="💬", stickerset=InputStickerSetEmpty())],
                    reply_to=topic_reply_to(event),
                )
        elif getattr(reply, "photo", None):
            image = open_media_image(downloaded_path)

            if image is None:
                await status.edit(tg_code("Unsupported photo for .144p"))
                return

            photo_output = output_path.with_suffix(".jpg")
            generated_paths.append(photo_output)
            await asyncio.to_thread(save_image_as_photo, image, photo_output)
            await client.send_file(event.chat_id, str(photo_output), force_document=False, mime_type="image/jpeg", reply_to=topic_reply_to(event))
        elif getattr(reply, "video", None) or mime_type.startswith("video/"):
            generated_paths.append(output_path)
            await asyncio.to_thread(run_ffmpeg_144p_gif, downloaded_path, output_path)
            await client.send_file(event.chat_id, str(output_path), force_document=False, mime_type="image/gif", reply_to=topic_reply_to(event))
        else:
            image = open_media_image(downloaded_path)

            if image is None:
                await status.edit(tg_code("Unsupported media type for .144p"))
                return

            generated_paths.append(output_path)
            await asyncio.to_thread(save_image_as_gif, image, output_path)
            await client.send_file(event.chat_id, str(output_path), force_document=False, mime_type="image/gif", reply_to=topic_reply_to(event))

        await status.delete()
        log(f".144p sent in chat {event.chat_id}")
    except FileNotFoundError:
        await status.edit(tg_code("ffmpeg is not installed"))
    except subprocess.CalledProcessError as e:
        error = (e.stderr or "").strip().splitlines()[-1:] or ["unknown ffmpeg error"]
        await status.edit(tg_code(f"Failed to convert media to GIF: {error[0]}"))
    except Exception as e:
        await status.edit(tg_code(f"144p failed: {e}"))
    finally:
        cleanup_files(*generated_paths)


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
    name_font = load_quote_font(34, bold=True)
    text_font = load_quote_font(38)
    time_font = load_quote_font(22)

    text = fit_quote_text(text, max_chars=850)
    avatar_size = 104
    gap = 16
    max_content_w = 690
    bubble_pad_x = 30
    bubble_pad_top = 24
    bubble_pad_bottom = 28
    line_spacing = 11

    dummy = Image.new("RGBA", (1, 1))
    measure = ImageDraw.Draw(dummy)
    wrapped = wrap_text_to_width(measure, text, text_font, max_content_w) if text else ""
    media = fit_media_image(media_image, max_width=max_content_w, max_height=430) if media_image is not None else None

    text_w, text_h = multiline_size(measure, wrapped, text_font, spacing=line_spacing) if wrapped else (0, 0)
    name_w, name_h = text_size(measure, author, name_font)
    media_w, media_h = media.size if media else (0, 0)
    content_w = max(text_w, media_w, min(name_w, max_content_w), 260)
    bubble_w = min(max_content_w + bubble_pad_x * 2, max(360, content_w + bubble_pad_x * 2))
    content_w = bubble_w - bubble_pad_x * 2

    if text_w > content_w and wrapped:
        wrapped = wrap_text_to_width(measure, text, text_font, content_w)
        text_w, text_h = multiline_size(measure, wrapped, text_font, spacing=line_spacing)

    media_gap = 18 if media and wrapped else 0
    text_gap = 12 if wrapped else 0
    footer_h = 22
    bubble_h = bubble_pad_top + name_h + 12 + media_h + media_gap + text_h + text_gap + footer_h + bubble_pad_bottom
    width = 18 + avatar_size + gap + bubble_w + 20
    height = max(avatar_size + 30, bubble_h + 34)

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bubble_x = 18 + avatar_size + gap
    bubble_y = 14
    bubble_box = (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h)
    bubble_fill = (30, 31, 36, 248)
    draw_rounded_shadow(image, bubble_box, radius=34, shadow_offset=(0, 9), blur=18, alpha=115)
    draw.rounded_rectangle(bubble_box, radius=34, fill=bubble_fill)
    draw.rounded_rectangle((bubble_x + 1, bubble_y + 1, bubble_x + bubble_w - 1, bubble_y + bubble_h - 1), radius=33, outline=(255, 255, 255, 18), width=1)
    draw.polygon(
        [
            (bubble_x + 10, bubble_y + bubble_h - 48),
            (bubble_x - 18, bubble_y + bubble_h - 25),
            (bubble_x + 18, bubble_y + bubble_h - 22),
        ],
        fill=bubble_fill,
    )

    avatar_x = 14
    avatar_y = bubble_y + bubble_h - avatar_size - 8
    draw.ellipse((avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3), fill=(255, 255, 255, 32))
    avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    image.alpha_composite(avatar, (avatar_x, avatar_y))

    x = bubble_x + bubble_pad_x
    y = bubble_y + bubble_pad_top
    safe_author = author.strip() or "User"
    if text_size(measure, safe_author, name_font)[0] > content_w:
        while safe_author and text_size(measure, safe_author + "...", name_font)[0] > content_w:
            safe_author = safe_author[:-1]
        safe_author = safe_author.rstrip() + "..."

    draw.text((x, y), safe_author, font=name_font, fill=author_color(author))
    y += name_h + 12

    if media:
        image.alpha_composite(media, (x, y))
        y += media_h + media_gap

    if wrapped:
        draw.multiline_text((x, y), wrapped, font=text_font, fill=(246, 247, 249, 255), spacing=line_spacing)
        y += text_h + text_gap

    timestamp = datetime.now().strftime("%H:%M")
    time_w, time_h = text_size(measure, timestamp, time_font)
    draw.text(
        (bubble_x + bubble_w - time_w - 24, bubble_y + bubble_h - time_h - 16),
        timestamp,
        font=time_font,
        fill=(152, 156, 166, 230),
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
    generated_paths = []
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

    generated_paths.append(png_path)

    try:
        if send_png:
            await event.reply(file=str(png_path))
            log(f".q PNG sent in chat {event.chat_id}")
            return

        sticker_path = create_quote_sticker(png_path)
        generated_paths.append(sticker_path)
        await event.reply(
            file=str(sticker_path),
            force_document=False,
            attributes=[DocumentAttributeSticker(alt="💬", stickerset=InputStickerSetEmpty())],
        )
        log(f".q sticker sent in chat {event.chat_id}")
    finally:
        cleanup_files(*generated_paths)


def export_media_label(message):
    media = getattr(message, "media", None)

    if not media:
        return ""

    media_name = type(media).__name__

    if media_name == "MessageMediaWebPage":
        return ""

    if media_name == "MessageMediaPhoto":
        return "Photo"

    if media_name == "MessageMediaPoll":
        return "Poll"

    if media_name in {"MessageMediaGeo", "MessageMediaGeoLive", "MessageMediaVenue"}:
        return "Location"

    if media_name == "MessageMediaContact":
        return "Contact"

    if media_name == "MessageMediaDocument":
        document = getattr(media, "document", None)
        attributes = getattr(document, "attributes", None) or []

        for attribute in attributes:
            attr_name = type(attribute).__name__

            if attr_name == "DocumentAttributeSticker":
                return "Sticker"

            if attr_name == "DocumentAttributeAnimated":
                return "GIF"

            if attr_name == "DocumentAttributeVideo":
                if getattr(attribute, "round_message", False):
                    return "Video message"
                return "Video"

            if attr_name == "DocumentAttributeAudio":
                if getattr(attribute, "voice", False):
                    return "Voice message"
                return "Audio"

        return "Document"

    return "Media"


def message_topic_value(message):
    reply_header = getattr(message, "reply_to", None)

    if not reply_header:
        return None

    return getattr(reply_header, "reply_to_top_id", None) or getattr(reply_header, "reply_to_msg_id", None)


def message_matches_topic(message, selected_topic):
    if not selected_topic:
        return True

    return message.id == selected_topic or message_topic_value(message) == selected_topic


def safe_export_filename(title):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", title.strip())[:70].strip("-.")

    if not safe:
        safe = "chat"

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{safe}-{stamp}.html"


def export_target_from_text(raw_target, default_chat_id):
    target_text = raw_target.strip().split(maxsplit=1)[0] if raw_target.strip() else ""

    if not target_text:
        return default_chat_id, ""

    try:
        return int(target_text), target_text
    except ValueError:
        return target_text, target_text


def export_key(chat_id, selected_topic=None):
    return chat_id, selected_topic


def export_message_text(message):
    text = (message.raw_text or "").strip()

    if text:
        return text

    media = export_media_label(message)

    if media:
        return f"[{media}]"

    if getattr(message, "action", None):
        return "[service message]"

    return ""


def export_initials(name):
    parts = [part for part in re.split(r"\s+", str(name or "").strip()) if part]

    if not parts:
        return "?"

    return "".join(part[0].upper() for part in parts[:2])[:2]

def build_chat_export_html(chat_title, scope_title, messages, users):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_messages = len(messages)
    total_users = len(users)
    user_items = []

    for user_id, user in sorted(users.items(), key=lambda item: (-item[1]["count"], item[1]["name"].lower())):
        username = f"@{user['username']}" if user.get("username") else "No username"
        search_text = f"{user['name']} {username}".lower()
        initials = html.escape(export_initials(user['name']))
        avatar = html.escape(user.get("avatar") or "", quote=True)
        avatar_html = f"<img src=\"{avatar}\" alt=\"\">" if avatar else initials
        user_items.append(
            "<button class=\"user-item\" type=\"button\" "
            f"data-user=\"{html.escape(str(user_id), quote=True)}\" "
            f"data-search=\"{html.escape(search_text, quote=True)}\">"
            f"<i>{avatar_html}</i>"
            "<span>"
            f"<b>{html.escape(user['name'])}</b>"
            f"<small>{html.escape(username)}</small>"
            "</span>"
            f"<em>{user['count']}</em>"
            "</button>"
        )

    message_rows = []
    last_day = None

    for item in messages:
        day = item["date"].strftime("%Y-%m-%d") if item.get("date") else "Unknown date"

        if day != last_day:
            message_rows.append(f"<div class=\"day\" data-day=\"1\">{html.escape(day)}</div>")
            last_day = day

        when = item["date"].strftime("%H:%M") if item.get("date") else "--:--"
        author = html.escape(item["author"])
        body = html.escape(item["text"]).replace("\n", "<br>")
        username = html.escape(item.get("username") or "")
        username_html = f"<span>{username}</span>" if username else ""
        search_text = f"{item['author']} {item.get('username') or ''} {item['text']}".lower()
        initials = html.escape(export_initials(item['author']))
        avatar = html.escape(item.get("avatar") or "", quote=True)
        avatar_html = f"<img src=\"{avatar}\" alt=\"\">" if avatar else initials
        message_rows.append(
            "<article class=\"message\" "
            f"data-user=\"{html.escape(str(item.get('user_id') or ''), quote=True)}\" "
            f"data-search=\"{html.escape(search_text, quote=True)}\">"
            f"<div class=\"avatar\">{avatar_html}</div>"
            "<div class=\"bubble\">"
            "<div class=\"message-top\">"
            f"<strong>{author}</strong>"
            f"{username_html}"
            "</div>"
            f"<p>{body}</p>"
            f"<time>{when}</time>"
            "</div>"
            "</article>"
        )

    users_html = "".join(user_items) or "<p class=\"empty\">No users found.</p>"
    messages_html = "".join(message_rows) or "<p class=\"empty\">No messages found.</p>"
    return """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{title} export</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: rgb(14, 22, 33); color: rgb(232, 235, 239); font-family: Arial, Helvetica, sans-serif; }}
header {{ background: rgb(23, 33, 43); color: white; padding: 10px 16px; border-bottom: 1px solid rgb(15, 23, 32); position: sticky; top: 0; z-index: 5; }}
.topbar {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(220px, 430px); gap: 16px; align-items: center; }}
.chat-title {{ min-width: 0; }}
header h1 {{ margin: 0 0 3px; font-size: 18px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
header p {{ margin: 0; color: rgb(143, 161, 176); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.layout {{ display: grid; grid-template-columns: 330px minmax(0, 1fr); min-height: calc(100vh - 61px); }}
aside {{ border-right: 1px solid rgb(15, 23, 32); background: rgb(23, 33, 43); padding: 14px; position: sticky; top: 61px; height: calc(100vh - 61px); overflow: auto; }}
main {{ min-width: 0; padding: 18px 16px 46px; background: radial-gradient(circle at top left, rgba(42, 82, 112, .26), transparent 380px), rgb(14, 22, 33); }}
.summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; max-width: 860px; margin: 0 auto 16px; }}
.summary div {{ background: rgba(23, 33, 43, .92); border: 1px solid rgba(91, 188, 255, .13); border-radius: 6px; padding: 12px 14px; }}
.summary b {{ display: block; font-size: 21px; margin-bottom: 2px; }}
.summary span {{ color: rgb(143, 161, 176); font-size: 13px; }}
.search {{ width: 100%; border: 1px solid rgb(45, 61, 76); background: rgb(36, 47, 61); color: rgb(232, 235, 239); border-radius: 999px; padding: 11px 14px; outline: none; }}
.search:focus {{ border-color: rgb(82, 176, 232); }}
.user-list {{ display: grid; gap: 4px; }}
.user-item {{ width: 100%; display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 10px; border: 0; background: transparent; color: inherit; border-radius: 8px; padding: 8px; cursor: pointer; text-align: left; }}
.user-item:hover, .user-item.active {{ background: rgb(42, 57, 72); }}
.user-item i, .avatar {{ width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; background: linear-gradient(135deg, rgb(61, 151, 216), rgb(46, 185, 137)); color: white; font-style: normal; font-size: 13px; font-weight: 700; flex: 0 0 auto; overflow: hidden; }}
.user-item img, .avatar img {{ width: 100%; height: 100%; display: block; object-fit: cover; }}
.user-item span {{ min-width: 0; }}
.user-item b, .user-item small {{ display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.user-item b {{ font-size: 14px; }}
.user-item small {{ color: rgb(143, 161, 176); margin-top: 3px; font-size: 12px; }}
.user-item em {{ color: rgb(143, 161, 176); font-style: normal; font-size: 12px; }}
.user-item.hidden, .message.hidden, .day.hidden {{ display: none; }}
.filter-all {{ margin-bottom: 10px; }}
.sidebar-title {{ color: rgb(143, 161, 176); font-size: 12px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; margin: 2px 8px 10px; }}
.results {{ color: rgb(143, 161, 176); max-width: 860px; margin: 0 auto 14px; font-size: 13px; }}
#messages {{ max-width: 860px; margin: 0 auto; }}
.day {{ width: fit-content; color: rgb(207, 217, 226); background: rgba(54, 70, 84, .78); border-radius: 999px; font-size: 12px; font-weight: 700; margin: 18px auto 12px; padding: 6px 12px; }}
.message {{ display: flex; align-items: flex-end; gap: 8px; margin: 0 0 8px; }}
.bubble {{ max-width: min(720px, calc(100vw - 430px)); background: rgb(24, 37, 51); border-radius: 12px 12px 12px 3px; padding: 8px 11px 6px; box-shadow: 0 1px 1px rgba(0, 0, 0, .18); }}
.message-top {{ display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; margin-bottom: 2px; }}
.message-top strong {{ color: rgb(82, 176, 232); font-size: 13px; }}
.message-top span {{ color: rgb(143, 161, 176); font-size: 12px; }}
.message time {{ float: right; color: rgb(121, 145, 164); font-size: 11px; margin: 5px 0 0 12px; }}
.message p {{ margin: 0; line-height: 1.38; white-space: normal; overflow-wrap: anywhere; font-size: 14px; }}
.empty {{ max-width: 860px; margin: 0 auto; padding: 18px; color: rgb(143, 161, 176); }}
@media (max-width: 850px) {{ header {{ position: static; }} .topbar {{ grid-template-columns: 1fr; gap: 10px; }} .layout {{ grid-template-columns: 1fr; }} aside {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid rgb(15, 23, 32); }} main {{ padding: 14px 10px 34px; }} .summary {{ grid-template-columns: 1fr; }} .bubble {{ max-width: calc(100vw - 72px); }} }}
</style>
</head>
<body>
<header>
<div class=\"topbar\">
<div class=\"chat-title\">
<h1>{heading}</h1>
<p>{scope} - {total_messages} messages - {total_users} users - exported at {generated}</p>
</div>
<input id=\"search\" class=\"search\" type=\"search\" placeholder=\"Search users or messages\" autocomplete=\"off\">
</div>
</header>
<div class=\"layout\">
<aside>
<div class=\"sidebar-title\">Users</div>
<button id=\"allUsers\" class=\"user-item filter-all active\" type=\"button\" data-user=\"\"><i>All</i><span><b>All users</b><small>Full export</small></span><em>{total_messages}</em></button>
<div id=\"users\" class=\"user-list\">{users_html}</div>
</aside>
<main>
<section class=\"summary\">
<div><b>{total_messages}</b><span>messages</span></div>
<div><b>{total_users}</b><span>users</span></div>
<div><b>{scope}</b><span>scope</span></div>
</section>
<p id=\"results\" class=\"results\"></p>
<section id=\"messages\">{messages_html}</section>
</main>
</div>
<script>
const search = document.getElementById('search');
const resultText = document.getElementById('results');
const userButtons = Array.from(document.querySelectorAll('.user-item'));
const messages = Array.from(document.querySelectorAll('.message'));
const days = Array.from(document.querySelectorAll('.day'));
let selectedUser = '';
function normalize(value) {{ return (value || '').toLowerCase().trim(); }}
function applyFilters() {{
  const query = normalize(search.value);
  let visible = 0;
  userButtons.forEach(button => {{
    const isAll = button.dataset.user === '';
    const matches = isAll || !query || normalize(button.dataset.search).includes(query);
    button.classList.toggle('hidden', !matches);
    button.classList.toggle('active', button.dataset.user === selectedUser);
  }});
  messages.forEach(message => {{
    const userMatch = !selectedUser || message.dataset.user === selectedUser;
    const textMatch = !query || normalize(message.dataset.search).includes(query);
    const show = userMatch && textMatch;
    message.classList.toggle('hidden', !show);
    if (show) visible += 1;
  }});
  days.forEach(day => {{
    let next = day.nextElementSibling;
    let hasVisible = false;
    while (next && !next.dataset.day) {{
      if (next.classList && next.classList.contains('message') && !next.classList.contains('hidden')) {{ hasVisible = true; break; }}
      next = next.nextElementSibling;
    }}
    day.classList.toggle('hidden', !hasVisible);
  }});
  resultText.textContent = `${{visible}} visible messages`;
}}
userButtons.forEach(button => button.addEventListener('click', () => {{ selectedUser = button.dataset.user || ''; applyFilters(); }}));
search.addEventListener('input', applyFilters);
applyFilters();
</script>
</body>
</html>
""".format(
        title=html.escape(chat_title),
        heading=html.escape(chat_title),
        scope=html.escape(scope_title),
        generated=html.escape(generated_at),
        total_messages=total_messages,
        total_users=total_users,
        users_html=users_html,
        messages_html=messages_html,
    )


async def iter_export_messages(chat, selected_topic=None):
    if selected_topic:
        try:
            async for message in client.iter_messages(chat, reverse=True, reply_to=selected_topic, wait_time=0):
                yield message
            return
        except Exception:
            pass

    async for message in client.iter_messages(chat, reverse=True, wait_time=0):
        if message_matches_topic(message, selected_topic):
            yield message


async def send_export_file(event, chat_title, scope_title, messages, users, partial=False):
    content = build_chat_export_html(chat_title, scope_title, messages, users)
    filename = safe_export_filename(chat_title)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".html", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    final_path = tmp_path.with_name(filename)
    tmp_path.replace(final_path)

    caption_prefix = "Partial export" if partial else "Export"

    try:
        await client.send_file(
            event.chat_id,
            str(final_path),
            caption=f"{caption_prefix}: {chat_title} ({len(messages)} messages)",
            reply_to=getattr(getattr(event, "message", None), "id", None),
            force_document=True,
        )
    finally:
        cleanup_files(final_path)


async def send_export_snapshot(event, state, partial=True):
    lock = state.get("lock")

    if lock is None:
        lock = asyncio.Lock()
        state["lock"] = lock

    async with lock:
        if partial and state.get("partial_sent"):
            return False

        messages = list(state.get("messages") or [])
        users = {key: value.copy() for key, value in (state.get("users") or {}).items()}
        chat_title = state.get("chat_title") or "chat"
        scope_title = state.get("scope_title") or "full chat"
        await send_export_file(event, chat_title, scope_title, messages, users, partial=partial)

        if partial:
            state["partial_sent"] = True

        return True


async def export_chat_html(event, raw_target=""):
    target, target_text = export_target_from_text(raw_target, event.chat_id)
    selected_topic = topic_id(event) if not target_text else None
    status = await event.reply(tg_code("Exporting chat..."))

    try:
        chat = await client.get_entity(target)
        active_key = export_key(getattr(chat, "id", target), selected_topic)
        previous_export = ACTIVE_EXPORTS.get(active_key)

        if previous_export:
            previous_stop = previous_export.get("stop_event") if isinstance(previous_export, dict) else previous_export
            previous_stop.set()

        stop_event = asyncio.Event()
        chat_title = display_name(chat, str(target))
        scope_title = f"topic {selected_topic}" if selected_topic else "full chat"
        messages = []
        users = {}
        export_state = {
            "stop_event": stop_event,
            "messages": messages,
            "users": users,
            "chat_title": chat_title,
            "scope_title": scope_title,
            "lock": asyncio.Lock(),
            "partial_sent": False,
        }
        ACTIVE_EXPORTS[active_key] = export_state
        sender_cache = {}
        cancelled = False

        async for message in iter_export_messages(chat, selected_topic):
            if stop_event.is_set():
                cancelled = True
                break

            sender_id = getattr(message, "sender_id", None) or 0

            if sender_id not in sender_cache:
                sender = getattr(message, "sender", None)

                if sender is None:
                    try:
                        sender = await message.get_sender()
                    except Exception:
                        sender = None

                sender_cache[sender_id] = sender

            sender = sender_cache.get(sender_id)
            author = display_name(sender, "Unknown")
            username = getattr(sender, "username", None) or ""
            text = export_message_text(message)

            if not text:
                continue

            if sender_id not in users:
                avatar = await get_export_avatar_data(sender, author)
                users[sender_id] = {"name": author, "username": username, "count": 0, "avatar": avatar}

            users[sender_id]["count"] += 1
            messages.append({
                "date": getattr(message, "date", None),
                "author": author,
                "username": f"@{username}" if username else "",
                "text": text,
                "user_id": sender_id,
                "avatar": users[sender_id].get("avatar", ""),
            })

            if len(messages) % 2000 == 0:
                await status.edit(tg_code(f"Exporting chat... {len(messages)} messages"))

        if cancelled:
            if export_state.get("partial_sent"):
                await status.delete()
                log(f".exportchat cancelled after partial export with {len(messages)} messages from {chat_title}")
                return

            await status.edit(tg_code(f"Export cancelled. Sending partial HTML with {len(messages)} messages..."))
        else:
            await status.edit(tg_code(f"Sending export with {len(messages)} messages..."))

        await send_export_snapshot(event, export_state, partial=cancelled)
        await status.delete()

        if cancelled:
            log(f".exportchat sent partial export with {len(messages)} messages from {chat_title}")
        else:
            log(f".exportchat exported {len(messages)} messages from {chat_title}")
    except Exception as e:
        await status.edit(tg_code(f"Export failed:\n{e}"))

    finally:
        if "active_key" in locals() and "stop_event" in locals():
            active_export = ACTIVE_EXPORTS.get(active_key)
            active_stop = active_export.get("stop_event") if isinstance(active_export, dict) else active_export

            if active_stop is stop_event:
                ACTIVE_EXPORTS.pop(active_key, None)


async def cancel_chat_export(event, raw_target=""):
    target, target_text = export_target_from_text(raw_target, event.chat_id)
    selected_topic = topic_id(event) if not target_text else None
    export_states = []

    try:
        chat = await client.get_entity(target)
        active_key = export_key(getattr(chat, "id", target), selected_topic)
        active_export = ACTIVE_EXPORTS.get(active_key)

        if active_export:
            export_states.append(active_export)
        elif not selected_topic:
            target_id = getattr(chat, "id", target)
            export_states.extend(
                active_export
                for (chat_id, _), active_export in ACTIVE_EXPORTS.items()
                if chat_id == target_id
            )
    except Exception:
        active_export = ACTIVE_EXPORTS.get(export_key(event.chat_id, selected_topic))

        if active_export:
            export_states.append(active_export)

    if not export_states:
        await event.reply(tg_code("No export running in this chat/topic."))
        return

    ack = await event.reply(tg_code("Export cancel requested. Sending partial HTML..."))
    sent = 0
    errors = []

    for state in export_states:
        if isinstance(state, dict):
            stop_event = state.get("stop_event")
        else:
            stop_event = state

        if stop_event:
            stop_event.set()

        if isinstance(state, dict):
            try:
                if await send_export_snapshot(event, state, partial=True):
                    sent += 1
            except Exception as e:
                errors.append(str(e))

    if errors:
        await ack.edit(tg_code("Export cancel requested, but partial send failed:\n" + "\n".join(errors[:3])))
    elif sent:
        await ack.edit(tg_code("Export cancelled. Partial HTML sent."))
    else:
        await ack.edit(tg_code("Export cancel requested. Partial HTML was already sent."))


async def clear_own_messages(event):
    selected_topic = topic_id(event)
    chat_id = event.chat_id
    deleted = 0
    batch = []

    async def flush_batch():
        nonlocal deleted, batch

        if not batch:
            return

        current = batch
        batch = []
        await client.delete_messages(chat_id, current, revoke=True)
        deleted += len(current)

    async def scan_messages(use_topic_filter):
        kwargs = {"from_user": "me"}

        if use_topic_filter and selected_topic:
            kwargs["reply_to"] = selected_topic

        async for message in client.iter_messages(chat_id, **kwargs):
            if selected_topic and not use_topic_filter and not message_matches_topic(message, selected_topic):
                continue

            batch.append(message.id)

            if len(batch) >= 100:
                await flush_batch()

    try:
        try:
            await scan_messages(use_topic_filter=True)
        except Exception:
            batch.clear()
            await scan_messages(use_topic_filter=False)

        await flush_batch()
        scope = f"topic {selected_topic}" if selected_topic else "chat"
        await client.send_message("me", tg_code(f".cl deleted {deleted} messages from {scope} {chat_id}"))
        log(f".cl deleted {deleted} messages in chat {chat_id}")
    except Exception as e:
        await client.send_message("me", tg_code(f".cl failed in chat {chat_id}:\n{e}"))


async def handle_telegram_terminal(event):
    name, _ = parse_command(event.raw_text, TERMINAL_PREFIX)

    if not name:
        return False

    # The embedded telegram-terminal registers the real $ handlers on startup.
    # This fallback keeps $help working even if that module fails to register.
    if name == "help":
        await event.reply(tg_code(TELEGRAM_TERMINAL_HELP))
        return True

    return False


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    if (event.raw_text or "").startswith(TERMINAL_PREFIX):
        return

    name, rest = parse_command(event.raw_text)

    if not name:
        return

    if name == "help":
        await event.reply(tg_code(TOPUSER_HELP))
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
    elif name == "vegadata":
        if rest.strip():
            await event.reply(tg_code("Use only: .vegadata"))
            return

        await send_vegadata(event)
    elif name == "download":
        await download_link(event, rest)
    elif name == "mp3":
        await download_mp3(event, rest)
    elif name in {"spotify", "spotifydl"}:
        await event.reply(tg_code("Spotify is not returning downloadable links from the Nayan API right now."))
    elif name in NAYAN_ENDPOINTS:
        await nayan_download_link(event, rest, name)
    elif name == "144p":
        await send_media_144p(event, rest)
    elif name == "exportchat":
        await export_chat_html(event, rest)
    elif name == "cancelexport":
        await cancel_chat_export(event, rest)
    elif name == "cl":
        await clear_own_messages(event)
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
    elif name == "q":
        await quote_message(event, rest)


async def main():
    keep_online = ask_keep_online()
    print_startup_console()
    await client.start()
    log("Telegram client started")

    if keep_online:
        asyncio.create_task(keep_account_online())
        log(f"online presence refresh enabled every {ONLINE_REFRESH_SECONDS}s")
    else:
        log("online presence refresh disabled")

    if TELEGRAM_TERMINAL and hasattr(TELEGRAM_TERMINAL, "start"):
        await TELEGRAM_TERMINAL.start(client)
        log("telegram-terminal embedded")

    await client.send_message("me", startup_notice_text())
    log("startup notice sent to Saved Messages")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
