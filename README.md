# TopUser

```text
 _______          __  __
|__   __|        | | | |
   | | ___  _ __ | | | |___  ___ _ __
   | |/ _ \| '_ \| | | / __|/ _ \ '__|
   | | (_) | |_) | |_| \__ \  __/ |
   |_|\___/| .__/ \___/|___/\___|_|
            | |
            |_|
```

TopUser is a Telegram userbot with two command sets running in the same session.

- Personal Userbot uses the `.` prefix and is shown with `.help`.
- Telegram Terminal uses the `$` prefix and is shown with `$help`.

`TopUser.py` is fully unified and does not need `telegram-terminal.py` to run. The separate `telegram-terminal.py` file is included only for people who want to run Telegram Terminal by itself, without TopUser.

## Install

```bash
python3 -m venv remoteenv
source remoteenv/bin/activate
pip install -r requirements.txt
```

System tools:

```bash
sudo apt install ffmpeg
```

`bash` is required for Telegram Terminal. `ffmpeg` is required for video/media commands such as `.144p` and video quote previews. Link downloads use the Nayan Video Downloader API and do not require `yt-dlp`.

## Run

Run the unified TopUser bot:

```bash
TG_API_ID=123456 TG_API_HASH=your_api_hash python3 TopUser.py
```

Optional standalone Telegram Terminal only:

```bash
TG_API_ID=123456 TG_API_HASH=your_api_hash python3 telegram-terminal.py
```

You do not need `telegram-terminal.py` when running `TopUser.py`.

Get `TG_API_ID` and `TG_API_HASH` from https://my.telegram.org/apps.

## Startup

When TopUser starts, it asks whether it should keep your account online while the Python process is running:

```text
Keep account online while TopUser is running? [yes/no]:
```

Answer `yes` to enable it, or `no` to leave presence normal. When enabled, TopUser refreshes online status every 10 seconds by default. Change the interval with `TOPUSER_ONLINE_REFRESH_SECONDS`; values below 10 seconds are raised to 10 seconds.

For real 24/7 uptime, keep the Python process running on a VPS, tmux, screen, systemd, or another process manager.

Saved Messages receives:

```text
🟢 TopUser is online

Personal Userbot
Prefix: .
Help: .help

Telegram Terminal
Prefix: $
Help: $help
```

The local terminal is cleared and becomes a log view:

```text
TopUser running
Personal Userbot: prefix . | help .help
Telegram Terminal: prefix $ | help $help
Logs:
```

## Personal Userbot

Bot

```text
.help                 show Personal Userbot help
.pping                latency check
```

Quotes

```text
.q                    quote the replied message as sticker
.q --png              send quote as PNG instead of sticker
.q N                  quote N messages, max 10
.q custom text        make a quote from custom text
.q on selected quote  quote only selected Telegram quote text
```

Spam

```text
.spam text N          send text N times, max 1000
.spam N               reply to media and resend it N times
.unspam               stop spam in this chat/topic
```

Links

```text
.cleanurl URL         remove tracking params from URL
.vegadata            show @vegadata YouTube subscribers
.download URL         download video with Nayan API
.mp3 URL              get audio using API when available
add mp3 after any API shortcut to request audio
.api URL              download with Nayan API for supported sites
.yt/.ig/.fb/.x URL    API shortcuts for social links
.pin/.capcut/.soundcloud URL and more API shortcuts
```

Media

```text
.144p                 reply to media and send a low quality version
```

Chat

```text
.exportchat           export current chat/topic as HTML
.exportchat ID/@user  export another chat as HTML
.cancelexport         stop export and send partial HTML
.cl                   delete your messages in this chat/topic
```

`.exportchat` creates a dark HTML archive with messages grouped by day, a user menu, and search/filter controls. It works in normal groups and topic groups. `.cancelexport` stops the running export and sends the partial HTML collected so far.

Generated `.q`, `.144p`, `.download`, `.exportchat`, and API shortcut fallback files are deleted after they are sent to Telegram.

## Telegram Terminal

Shell

```text
$<command>            run command in persistent bash
$ttinput <text>       send one input line
$ttpaste <text>       paste raw text without Enter
```

Terminal Keys

```text
$ctrlc / $ctrl c      send Ctrl+C
$ctrlb / $ctrl b      send Ctrl+B, useful for tmux prefix
$ctrla / $ctrl a      send Ctrl+A
$ctrld                send Ctrl+D
$ctrlz                send Ctrl+Z
$enter                send Enter
$tab                  send Tab
$up / $down           send arrow keys
$left / $right        send arrow keys
$key esc|backspace|delete|home|end|pgup|pgdn|space
$key f1..f12          send function keys
```

Screenshots

```text
$shot                 screenshot current terminal screen
$shot 80              screenshot last 80 text-buffer lines
$shot wide            wider terminal screenshot
$shot clear           screenshot, then clear screen/buffer
$shot live N          readable animated screenshot, 1-10 seconds
$shot run <cmd>       run command and send screenshot
$shot theme [...]     black, green, white, amber
$shot title <text>    set screenshot title
$tt size [COLSxROWS]  show or resize terminal dimensions
```

Buffers

```text
$buf tail [lines|full]  show session output buffer
$buf send [file.txt]    send session buffer as .txt
$buf save <file.txt>    save session buffer on server
$buf clear              clear session buffer and shot screen
$buf status             show buffer status
```

Files

```text
$ttget <file>         send file from server
$ttput <path>         upload attached document to path
```

Editor

```text
$ttedit open <file>   open file
$ttedit show          show editor buffer
$ttedit set N <text>  replace line N
$ttedit insert N <text>
$ttedit append <text>
$ttedit delete N[-M]
$ttedit undo
$ttedit find <text>
$ttedit replace old new
$ttedit replace-all old new
$ttedit save
$ttedit cancel
```

History / Logs

```text
$cmd history [N]      show command history
$cmd last             show last command
$cmd rerun N          rerun command by history number
$out log on|off|status
```

Terminal Bot

```text
$help                 show Telegram Terminal help
$tt status            shell/editor status
$tt restart           restart persistent bash
$tt reset             clear terminal runtime state
$tt version           show version
$tt ping              latency check
$tt uptime            bot and system uptime
$tt about             summary
```

## Project Layout

```text
TopUser.py            unified combined userbot
telegram-terminal.py  optional standalone Telegram Terminal only
requirements.txt      dependencies
README.md             documentation
.gitignore            ignored local/runtime files
```

## Notes

This is a userbot and runs on your Telegram account. Keep session files private. The repository ignores virtualenvs, Telegram sessions, caches, downloads, and logs.

`.download`, `.mp3`, `.api`, and shortcuts such as `.yt`, `.tiktok`, `.ig`, `.fb`, `.x`, `.pin`, `.capcut`, `.soundcloud`, `.terabox`, `.gdrive`, and `.ndown` use the Nayan Video Downloader API. Platform shortcuts use the matching API endpoints when available, including `/instagram` for Instagram links. Audio mode is API-only: use `.mp3 URL` or add `mp3` after any API shortcut; the API may return MP3, M4A, AAC, OGG, WAV, or OPUS depending on the source. Credit for downloader responses goes to the Nayan API service.
