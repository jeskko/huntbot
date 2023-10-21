import discord,aiohttp,logging

from discord.ext import commands

import nuny.config

discord.VoiceClient.warn_nacl=False

intents=discord.Intents.default()
intents.message_content=True

bot = commands.Bot(command_prefix=".",intents=intents)

async def post_webhooks(msg, expansion):
    """Send a message using webhook to multiple Discord servers."""
    logging.debug("post_webhooks start")
    for w in nuny.config.conf["webhooks"]:
        wh=w["webhook"]
        r=w["roles"][expansion]
        if r!=0:
            rtxt=""
            if r>1:
                rtxt=f"<@&{r}> "                
            logging.debug(f'Sending to {w["name"]}')
            msgtxt=f"{rtxt}{msg}"
            async with aiohttp.ClientSession() as session:
                webhook=discord.Webhook.from_url(w["webhook"], session=session)
                try:
                    await webhook.send(content=msgtxt,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")                        
                except discord.errors.HTTPException as e:
                    logging.error(f'Unable to send message to {w["name"]}: {e}')
                    pass