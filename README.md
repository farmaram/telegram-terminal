# personal quotly userbot

A personal Telegram userbot for creating Quotly-style quote stickers.

## Features

- Creates quote stickers with `.q`, `.quote` or `.quotly`
- Uses a dark Quotly-style bubble with transparent sticker background
- Uses the sender profile photo when available
- Tries to use the original author for forwarded messages
- Embeds static images and stickers inside the quote
- Uses one static video frame when `ffmpeg` is installed

## Commands

- `.q` quotes the replied message as a sticker
- `.quote` same as `.q`
- `.quotly` same as `.q`
- `.q --png` sends the quote as PNG instead of sticker
- `.q custom text` creates a quote from custom text
- `.phelp` shows help
- `.pping` checks latency

## Telegram API Setup

Get your Telegram API credentials from https://my.telegram.org/apps.

Steps:

- Open https://my.telegram.org/apps
- Log in with your Telegram phone number
- Create an application
- Copy the `api_id` and `api_hash`

You can pass them with environment variables when starting the userbot:

```bash
TG_API_ID=123456 TG_API_HASH=your_api_hash python3 personal-userbot.py
```

Or edit them directly in `personal-userbot.py`.

## Linux Installation

Install system packages first. Package names vary by distro, but you need:

- Python 3
- `python3-venv` or equivalent
- `pip`
- FreeType/JPEG/zlib libraries for Pillow
- `ffmpeg` if you want video quotes

Clone and install:

```bash
git clone <YOUR_REPO_URL>
cd quotly-userbot
python3 -m venv remoteenv
source remoteenv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Run:

```bash
TG_API_ID=123456 TG_API_HASH=your_api_hash python3 personal-userbot.py
```

On first run, Telegram will ask for login confirmation and create a local session file.

## Termux Installation

Install packages:

```bash
pkg update
pkg install python git freetype libjpeg-turbo zlib ffmpeg clang make pkg-config
```

Clone and install:

```bash
git clone <YOUR_REPO_URL>
cd quotly-userbot
python -m venv remoteenv
source remoteenv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If Pillow fails to build or cannot load fonts, install Termux Pillow instead:

```bash
pip uninstall -y pillow
deactivate
pkg install python-pillow
python -m venv --system-site-packages remoteenv
source remoteenv/bin/activate
pip install telethon
```

Run:

```bash
TG_API_ID=123456 TG_API_HASH=your_api_hash python personal-userbot.py
```

## Notes

This is a userbot: it runs on your Telegram account. Keep it personal and avoid spam or automated public abuse.

Generated quote files and Telegram session files are ignored by git.
