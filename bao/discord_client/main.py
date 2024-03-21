from pydoc import cli
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
    if message.channel.type.name == "private":  # type: ignore
        sender = message.author
    elif not settings.discord.limit_channel:  # no channel constrain for the bot
        sender = message.channel
    elif (
        message.channel.id in settings.discord.limit_channel
    ):  # limited to the given channel id
        sender = message.channel
    else:
        logger.warning("Not supported chatting channel for the bot!")
        return
    try:
        response: str = await chat_chain.chat(message.content, str(message.author))
        if settings.discord.reply_mode:
            await sender.send(response, reference=message)
        else:
            await sender.send(response)
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


# handling message editting
@client.event
async def on_message_edit(before: Message, after: Message) -> None:
    if after.author == client.user or before.content.strip() == after.content.strip():
        return
    await on_message(after)


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
