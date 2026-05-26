# personal quotly userbot

A personal Telegram userbot for creating Quotly-style quote stickers.

## Commands

- `.q` quotes the replied message as a sticker
- `.quote` same as `.q`
- `.quotly` same as `.q`
- `.q --png` sends the quote as PNG instead of sticker
- `.q custom text` creates a quote from custom text
- `.phelp` shows help
- `.pping` checks latency

Forwarded messages try to use the original forwarded author. Static images and stickers are embedded in the quote. Videos use one static frame if `ffmpeg` is installed.

## Run

Get `api_id` and `api_hash` from https://my.telegram.org/apps.

```bash
python3 -m venv remoteenv
source remoteenv/bin/activate
pip install -r requirements.txt
TG_API_ID=123456 TG_API_HASH=your_api_hash python3 personal-userbot.py
```
