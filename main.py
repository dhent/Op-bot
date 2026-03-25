import threading
from bot import Bot
from config import API_KEYS

bots = []

for i, key in enumerate(API_KEYS):
    if key.strip():
        bots.append(Bot(key.strip(), name=f"Bot-{i+1}"))

threads = []

for bot in bots:
    t = threading.Thread(target=bot.run)
    t.start()
    threads.append(t)

for t in threads:
    t.join()