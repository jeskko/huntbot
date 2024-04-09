import discord,aiohttp,logging
import sys,traceback

from discord.ext import commands

import nuny.config
import nuny.state
from nuny.log_utils import bot_log

discord.VoiceClient.warn_nacl=False

intents=discord.Intents.default()
intents.message_content=True

async def on_command_error(ctx: commands.Context, error):
    # Handle your errors here
    if isinstance(error, commands.TooManyArguments):
        await ctx.message.add_reaction('❌')
        await ctx.send("Too many arguments. You might have forgot to put the message in \"\".")

    if isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction('❌')
        await ctx.send("Command not found. Check your typing.")

    else:
        # All unhandled errors will print their original traceback
        print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

bot = commands.Bot(command_prefix=".",intents=intents)
bot.on_command_error=on_command_error

async def post_webhooks(msg, expansion):
    """Send a message using webhook to multiple Discord servers."""
    logging.debug("post_webhooks start")
    await bot_log("post_webhooks start")
    for w in nuny.config.conf["webhooks"]:
        wh=w["webhook"]
        r=w["roles"][expansion]
        if r!=0:
            rtxt=""
            if r>1:
                rtxt=f"<@&{r}> "                
            logging.debug(f'Sending to {w["name"]}')
            await bot_log(f'Sending to {w["name"]}')
            msgtxt=f"{rtxt}{msg}"
            async with aiohttp.ClientSession() as session:
                webhook=discord.Webhook.from_url(w["webhook"], session=session)
                try:
                    await webhook.send(content=msgtxt,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")                        
                except (discord.errors.HTTPException,discord.errors.NotFound) as e:
                    logging.error(f'Unable to send message to {w["name"]}: {e}')
                    bot_log(f'Unable to send message to {w["name"]}: {e}')
                    pass
    await bot_log("post_webnhooks end")
                
async def check_messages():
    """Verify that status messages exist on every server channel and make new ones if needed."""
    print("Checking status messages",end="")
    for channel,msg_id in nuny.state.state["statuses"].items():
        chan=bot.get_channel(channel)
        try:
            msg=await chan.fetch_message(msg_id)
        except discord.errors.NotFound:
            msg=await chan.send("foo")
            nuny.state.state["statuses"][channel]=msg.id
            nuny.state.savestate()
        print(".",end="")
    print(" done")

async def update_message(world,legacy,text):
    """Update a status message"""
    if legacy=="l":
        l=5
    else:
        l=6
    try:
        w=[w for w in nuny.config.conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    channel=w[l]["channel"]
    msg_id=nuny.state.state["statuses"][channel]
    chan=bot.get_channel(channel)
    try: 
        msg=await chan.fetch_message(msg_id)
    except discord.errors.NotFound:
        msg=await chan.send(text)
        nuny.state.state["statuses"][channel]=msg.id
        nuny.state.savestate()
    await msg.edit(content=text)