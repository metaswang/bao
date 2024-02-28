from dotenv import load_dotenv

load_dotenv()
import logging
from typing import Final
from discord import Client, Intents, Message
from bao.discord_client.discord_chat import DiscordChat
from bao.di import global_injector
from bao.settings.settings import Settings

logger = logging.getLogger()

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
settings = global_injector.get(Settings)
TOKEN: Final[str] = settings.discord.discord_token  # type: ignore
BOT_ID = settings.discord.bot_id
# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True  # NOQA
client: Client = Client(intents=intents)
chat_chain = global_injector.get(DiscordChat)


# STEP 2: MESSAGE FUNCTIONALITY
async def reply_message(message: Message) -> None:
    if not message.content:
        return
    try:
        response: str = await chat_chain.chat(message.content, str(message.author))
        (
            await message.author.send(response)
            if message.channel.type.name == "private"  # type: ignore
            else await message.channel.send(response)
        )
    except Exception as e:
        logging.exception("Exception when bot reply: ", e)


# STEP 3: HANDLING THE STARTUP FOR OUR BOT
@client.event
async def on_ready() -> None:
    print(f"{client.user} is now running!")


# STEP 4: HANDLING INCOMING MESSAGES
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    if (
        BOT_ID in [_.id for _ in message.mentions]
        or message.channel.type.name == "private"  # type: ignore
    ):
        await reply_message(message)


# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)

def run_as_daemon_service():
  """
  Starts the daemon service in a background thread.
  """
  import threading
  thread = threading.Thread(target=main)
  thread.daemon = True  # Set the thread as a daemon
  thread.start()    


if __name__ == "__main__":
    main()
