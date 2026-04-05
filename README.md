# Email Agent

A Discord bot that manages your Gmail inbox using natural language commands, powered by Claude AI.

## Architecture

```
Discord DM → Discord Bot → Claude (tool calling) → Gmail API → Action
```

## Features

- **Read inbox** — fetch your most recent emails
- **Read email** — get the full body of any email
- **Send email** — compose and send HTML-formatted emails
- **Reply** — reply to emails in-thread
- **Label** — apply Gmail labels (creates them if they don't exist)
- **Mark as read** — remove the unread flag from an email
- Confirmation gate before any destructive action (send/reply/label)
- Per-user conversation history so follow-up commands work naturally

## Getting Started

### Prerequisites

- Python 3.12+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A Google Cloud project with the Gmail API enabled and an OAuth 2.0 Desktop client

### Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Linux/Mac: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_key
DISCORD_BOT_TOKEN=your_discord_bot_token
```

### Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Enable **Gmail API**
2. Create an OAuth 2.0 Client ID (Desktop) and download it as `credentials.json` to the project root
3. Add yourself as a test user under OAuth consent screen
4. Run the one-time auth flow:

```bash
python auth.py
```

This saves `token.json` which the bot uses for all Gmail requests. Both `credentials.json` and `token.json` are gitignored.

### Run the bot

```bash
python run.py
```

### Run tests

```bash
pytest tests/ -v
```

## Keeping the Bot Running

The bot is managed by [PM2](https://pm2.keymetrics.io/). Requires Node.js.

```bash
# Install PM2
npm install -g pm2

# Start the bot
pm2 start run.py --name email-bot --interpreter .venv/Scripts/python.exe --cwd /path/to/email-agent

# Save process list (survives crashes, auto-restarts)
pm2 save
```

To auto-start on Windows login, run once in an admin PowerShell:

```powershell
schtasks /Create /TN "EmailBotPM2" /TR "C:\path\to\email-agent\start-bot.bat" /SC ONLOGON /RU "YOUR_USERNAME" /F
```

Useful PM2 commands:

```bash
pm2 status              # check if running
pm2 logs email-bot      # tail live logs
pm2 restart email-bot
pm2 stop email-bot
```

## Example Commands

Send these as Discord DMs to the bot:

```
show me my last 5 emails
read the email from Alice
send an email to bob@example.com about the meeting tomorrow
reply to that email saying "Got it, thanks"
label that email as urgent
mark that email as read
```

Destructive actions (send, reply, label) will ask for confirmation before executing. Reply `YES` to proceed.

## Project Structure

```
app/
  bot/
    client.py         # Discord bot, per-user conversation history
  services/
    agent.py          # Claude agentic loop + Gmail tool definitions
    gmail_tools.py    # Gmail API functions
  config.py           # Environment variable loading
run.py                # Standalone bot entrypoint
tests/
  test_bot.py
  test_gmail_tools.py
```
