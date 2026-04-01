import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
