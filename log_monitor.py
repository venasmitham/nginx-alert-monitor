import asyncio
import aiofiles
import aiohttp
import os
import json
import time
import re
from datetime import datetime

# Configuration
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'app.log')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', 60))
MAX_ALERTS = int(os.getenv('MAX_ALERTS_PER_WINDOW', 5))

alert_history = []

async def send_discord_alert(line):
    global alert_history
    now = time.time()
    alert_history = [t for t in alert_history if now - t < RATE_LIMIT_WINDOW]
    
    if len(alert_history) >= MAX_ALERTS:
        return

    alert_history.append(now)
    try:
        data = json.loads(line)
        embed = {
            "title": "🚨 5xx Error Detected",
            "fields": [
                {"name": "Status", "value": str(data.get('status', 'N/A')), "inline": True},
                {"name": "Timestamp", "value": data.get('timestamp', datetime.now().isoformat()), "inline": True},
                {"name": "Message", "value": str(data.get('message', 'No message provided'))}
            ]
        }
        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except Exception as e:
        print(f"Failed to send alert: {e}")

async def tail_file():
    while True:
        try:
            async with aiofiles.open(LOG_FILE_PATH, mode='r') as f:
                await f.seek(0, os.SEEK_END)
                while True:
                    line = await f.readline()
                    if not line:
                        if not os.path.exists(LOG_FILE_PATH) or os.path.getsize(LOG_FILE_PATH) < await f.tell():
                            break
                        await asyncio.sleep(0.1)
                        continue
                    
                    try:
                        data = json.loads(line)
                        status = int(data.get('status', 0))
                        if 500 <= status <= 599:
                            await send_discord_alert(line)
                    except:
                        pass
        except FileNotFoundError:
            await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(tail_file())