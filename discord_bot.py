import os
from typing import Final

# from responses import get_response
from dotenv import load_dotenv
from discord import Intents, Client, Message
from utils.rag import RAG
import logging

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
BOT_ID = int(os.getenv("DISCORD_BOT_ID"))
# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True  # NOQA
client: Client = Client(intents=intents)
baobot: RAG = RAG()


# STEP 2: MESSAGE FUNCTIONALITY
async def reply_message(message: Message) -> None:
    if not message.content:
        return
    try:
        response: str = await baobot.chat(message.content, str(message.author))
        (
            await message.author.send(response)
            if message.channel.type.name == "private"
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
    if BOT_ID in message.raw_role_mentions or message.channel.type.name == "private":
        await reply_message(message)


# STEP 5: MAIN ENTRY POINT
def main() -> None:
    client.run(token=TOKEN)


if __name__ == "__main__":
    main()
