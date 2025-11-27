import datetime,logging,asyncio
from time import mktime

import nuny.config
import nuny.db_utils
import nuny.discord_utils

import aiohttp

from typing import Optional

from discord import app_commands

from nuny.log_utils import bot_log,scout_log
from nuny.misc_utils import speculate,mapping,health,parse_parameters,parse_world,set_status,get_statuses,get_history,maintenance_reboot
from nuny.sonar import sonar_stats,sonarreset

worldchoices=[]     
for w in nuny.config.conf["worlds"]:
    worldchoices.append(app_commands.Choice(name=w["name"], value=w["short"][0]))

expansionchoices=[
    app_commands.Choice(name="DT", value=7),
    app_commands.Choice(name="EW", value=6),
    app_commands.Choice(name="SHB", value=5)]

allexpansionchoices=[
    app_commands.Choice(name="DT", value=7),
    app_commands.Choice(name="EW", value=6),
    app_commands.Choice(name="SHB", value=5),
    app_commands.Choice(name="STB", value=4),
    app_commands.Choice(name="HW", value=3),
    app_commands.Choice(name="ARR", value=2)]

async def log_cmd(ctx):
    await bot_log(f"{ctx.message.author.display_name} {ctx.message.channel.name}:  {ctx.message.content}")

@nuny.discord_utils.bot.tree.command(name="speculate", description='Speculate about status of a certain world', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def spec_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], expansion: app_commands.Choice[int], silent: bool = False):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: speculate: {world.value} {expansion.value}")

    if expansion.value in range(5,8):
        msg=speculate(world.value,expansion.value)
    else:
        await interaction.response.send_message("Untracked expansion", ephemeral=True)
        return
    await interaction.response.send_message(msg,ephemeral=silent)

@nuny.discord_utils.bot.command(name='speculate',help='Speculate about status of a certain world')
async def spec_cmd(ctx,world,expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await log_cmd(ctx)
    if expansion in range(5,8):
        msg=speculate(world,expansion)
    else:
        await ctx.send("Untracked expansion")
        await ctx.message.add_reaction("❓")
        return
    await ctx.message.add_reaction("✅")
    await ctx.send(msg)

@nuny.discord_utils.bot.tree.command(name="map", description='Check mapping data from Sonar', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def map_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], expansion: app_commands.Choice[int], silent: bool = False):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: mapping: {world.value} {expansion.value}")

    try:
        msg=mapping(world.value, expansion.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()

    await interaction.response.send_message(msg, ephemeral=silent)

@nuny.discord_utils.bot.command(name='mapping', aliases=["map",], help='Check mapping data from Sonar')
async def map_cmd(ctx,world,expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
    try:
        msg=mapping(world, expansion)
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)
        return()
    await ctx.message.add_reaction("✅")
    await ctx.send(msg)

@nuny.discord_utils.bot.tree.command(name="health", description='Check last seen data from Sonar', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def hlth_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], expansion: app_commands.Choice[int], silent: bool = False):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: health: {world.value} {expansion.value}")

    try:
        msg=health(world.value, expansion.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()

    await interaction.response.send_message(msg, ephemeral=silent)

@nuny.discord_utils.bot.command(name='health', help='Check last seen data from Sonar')
async def hlth_cmd(ctx,world,expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
    try:
        msg=health(world, expansion)
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)
        return()
    await ctx.message.add_reaction("✅")
    await ctx.send(msg)

@nuny.discord_utils.bot.tree.command(name="scout", description='Begin scouting', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def scouting_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], expansion: app_commands.Choice[int]):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: scout: {world.value} {expansion.value}")

    try:
        world=parse_world(world.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()

    try:
        set_status(world,"Scouting",expansion.value,"last")
        await interaction.response.send_message(f"✅ {world} {expansion.name} scouting started.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message(f"Error: {ex}", ephemeral=True)

@nuny.discord_utils.bot.command(name='scout', aliases=['sc','scouting'],help='Begin scouting.')
async def scouting_cmd(ctx, world, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    try:
        set_status(world,"Scouting",expansion, "last")
        await ctx.message.add_reaction("✅")
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)

@nuny.discord_utils.bot.tree.command(name="scend", description='End scouting', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def scoutend_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], expansion: app_commands.Choice[int]):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: scend: {world.value} {expansion.value}")

    try:
        world=parse_world(world.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()

    try:
        set_status(world,"Scouted",expansion.value,"last")
        await interaction.response.send_message(f"✅ {world} {expansion.name} scouting complete.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message(f"Error: {ex}", ephemeral=True)

@nuny.discord_utils.bot.command(name='scouted', aliases=['scdone','scend'],help='End scouting.')
async def scoutend_cmd(ctx, world, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
 
    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    try:
        set_status(world,"Scouted",expansion,"last")
        await ctx.message.add_reaction("✅")
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)

@nuny.discord_utils.bot.tree.command(name="run", description='Start train.\n Time can be manually set in form "+15" (minutes) or "15:24" (server time)', guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(time="Start time (optional)")
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def begintrain_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], time: str | None, expansion: app_commands.Choice[int]):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: start: {world.value} {expansion.value} {time}")

    try:
        world=parse_world(world.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()

    if time != None:
        timetext=f" at time {time}"
    else:
        timetext=""

    try:
        set_status(world,"Running",expansion.value,time)
        await interaction.response.send_message(f"✅ {world} {expansion.name} set to running{timetext}.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message(f"Error: {ex}", ephemeral=True)


@nuny.discord_utils.bot.command(name='start', aliases=['begin','run','go'],help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def begintrain_cmd(ctx, world, time=None, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
 
    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    try:
        set_status(world,"Running",expansion,time)
        await ctx.message.add_reaction("✅")
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)
   
@nuny.discord_utils.bot.tree.command(name="end", description="End train", guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(time="End time (optional)")
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def endtrain_tree(interaction: nuny.discord_utils.discord.Interaction, world: app_commands.Choice[str], time: str | None, expansion: app_commands.Choice[int]):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: end: {world.value} {expansion.value} {time}")

    try:
        world=parse_world(world.value)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await interaction.response.send_message("Invalid world.", ephemeral=True)
        return()
    try:
        set_status(world,"Dead",expansion.value,time)
        if time != None:
            timetext=f" at time {time}"
        else:
            timetext=""
        if nuny.config.conf["sonar"]["enable"]==True:
            await interaction.response.send_message(f"✅ {world} {expansion.name} set to Dead{timetext}.\n{sonar_stats(world,expansion.value)}")
        else:
            await interaction.response.send_message(f"✅ {world} {expansion.name} set to Dead{timetext}.")
    except ValueError as ex:
        await interaction.response.send_message(f"Error: {ex}", ephemeral=True)
        await bot_log(f"ValueError: {ex}")


@nuny.discord_utils.bot.command(name='end', aliases=['done','dead','finish'],help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def endtrain_cmd(ctx, world, time=None, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    try:
        set_status(world,"Dead",expansion,time)
        await ctx.message.add_reaction("✅")
        if nuny.config.conf["sonar"]["enable"]==True:
            (time,expansion)=parse_parameters(time,expansion) 
            await scout_log(sonar_stats(world,expansion))
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(ex)

@nuny.discord_utils.bot.tree.command(name="status", description="Get train status", guild=nuny.discord_utils.guild)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def getstatus_tree(interaction: nuny.discord_utils.discord.Interaction, expansion: app_commands.Choice[int], silent: bool = False):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: status {expansion.value}")
    try:
        if int(expansion.value) in range(5,8):
            msg=get_statuses(expansion.value)
            await interaction.response.send_message(msg, ephemeral = silent)
        else:
            await interaction.response.send_message("Invalid expansion", ephemeral = True)
    except ValueError as ex:
        await interaction.response.send_message(f"Error: {ex}", ephemeral = True)
        await bot_log(f"ValueError: {ex}")

@nuny.discord_utils.bot.command(name="status", aliases=['getstatus','stat'],help='Get train status')
async def getstatus_cmd(ctx, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
    try:
        if int(expansion) in range(5,8):
            msg=get_statuses(expansion)
            await ctx.send(msg)
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❓")
            await ctx.send("Invalid expansion")
    except ValueError:
        await ctx.send("Invalid expansion")

@nuny.discord_utils.bot.tree.command(name="history", description="Get command history for a world", guild=nuny.discord_utils.guild)
@app_commands.describe(world="World")
@app_commands.choices(world=worldchoices)
@app_commands.describe(expansion="Expansion")
@app_commands.choices(expansion=expansionchoices)
async def getstatus_tree(interaction: nuny.discord_utils.discord.Interaction, expansion: app_commands.Choice[int], world: app_commands.Choice[str], silent: bool = False):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: history {expansion.value} {world.value}")
    try:
        world=parse_world(world.value)
    except ValueError as ex:
        await interaction.response.send_message(f"Error: {ex}", ephemeral = True)
        await bot_log(f"ValueError: {ex}")
        return
    
    if expansion.value in range(5,8):
        msg=get_history(world,expansion.value)
        await interaction.response.send_message(msg, ephemeral = silent)
    else:
        await interaction.response.send_message("Invalid expansion",ephemeral=True)

@nuny.discord_utils.bot.command(name="history", aliases=['hist'],help='Get status history')
async def gethistory_cmd(ctx, world, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await log_cmd(ctx)

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()
    
    if expansion in range(5,8):
        msg=get_history(world,expansion)
        await ctx.send(msg)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.send("Invalid expansion")
        await ctx.message.add_reaction("❓")

@nuny.discord_utils.bot.tree.command(name="undo", description="Undo a previous status", guild=nuny.discord_utils.guild)
@app_commands.describe(status="Status ID")
async def undo_tree(interaction: nuny.discord_utils.discord.Interaction, status: int):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: undo {status}")

    nuny.db_utils.delstatus(status)
    await interaction.response.send_message(f"✅ Status #{status} deleted.")

@nuny.discord_utils.bot.command(name="undo",help="Undo a previous status.")
async def undo_cmd(ctx,id):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)

    try:
        id=int(id)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid ID.")
        return()

    nuny.db_utils.delstatus(id)
    await ctx.message.add_reaction("✅")

@nuny.discord_utils.bot.tree.command(name="adjust", description="Adjust timestamp of a previous status.", guild=nuny.discord_utils.guild)
@app_commands.describe(status="Status ID")
async def adjust_tree(interaction: nuny.discord_utils.discord.Interaction, status: int, time: str):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: adjust {status} {time}")

    time,exp=parse_parameters(time,7)
    nuny.db_utils.settime(status,time)
    interaction.response.send_message(f"✅ Status #{status} adjusted to {time}.")
    
@nuny.discord_utils.bot.command(name="adjust",aliases=['fix'],help="Adjust timestamp of a previous status.")
async def adjust_cmd(ctx,id,time):

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)

    try:
        id=int(id)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid ID.")
        return()

    time,exp=parse_parameters(time,7)
    nuny.db_utils.settime(id,time)
    await ctx.message.add_reaction("✅")

@nuny.discord_utils.bot.tree.command(name="reboot", description="Set reboot timer after maintenance.", guild=nuny.discord_utils.guild)
@app_commands.describe(time="Estimated server reset time (UTC)")
async def reboot_tree(interaction: nuny.discord_utils.discord.Interaction, time: str):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: reboot {time}")

    time,exp=parse_parameters(time,7)

    await interaction.response.send_message(f"About to reset all worlds maintenance end to time {time}. Confirm by reacting to this with a ✅.")
    msg1= await interaction.original_response()
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == interaction.user.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.edit(content="❌ Timed out. Servers are not reset.")
        await msg1.clear_reactions()
        
    else:
        maintenance_reboot(time)
        await msg1.edit(content=f"✅ All servers adjusted for server reboot at {time}.")
        await msg1.clear_reactions()
    
@nuny.discord_utils.bot.command(name="reboot",help="Set reboot timer after maintenance.")
async def reboot_cmd(ctx,time):

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await log_cmd(ctx)
    time,exp=parse_parameters(time,7)

    msg1=await ctx.send(f"About to reset all worlds maintenance end to time {time}. Confirm by reacting to this with a ✅.")
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        
    else:
        maintenance_reboot(time)
        await msg1.delete()
        await ctx.message.add_reaction("✅")
        await ctx.send(f"All servers adjusted for server reboot at {time}.")

@nuny.discord_utils.bot.tree.command(name="sonarcleanup", description="Clean up sonar data that is older than parameter time.", guild=nuny.discord_utils.guild)
@app_commands.describe(time="Time (UTC)")
async def sonarboot_tree(interaction: nuny.discord_utils.discord.Interaction, time: str):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: sonarcleanup {time}")
    
    try:
        time,exp=parse_parameters(time,7)
    except ValueError:
        await interaction.response.send_message("❌ invalid time value.")
        return

    await interaction.response.send_message(f"About to erase all sonar info older than {time}. Confirm by reacting to this with a ✅.")
    msg1= await interaction.original_response()
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == interaction.user.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.edit(content="❌ Timed out. Sonar data not reset.")
        await msg1.clear_reactions()
        
    else:
        sonarreset(time)
        await msg1.edit(content=f"✅ All sonar data older than {time} removed.")
        await msg1.clear_reactions()

@nuny.discord_utils.bot.command(name="sonarcleanup",help="Clean up sonar data that is older than parameter time.")
async def sonarboot_cmd(ctx,time):

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await log_cmd(ctx)
    try:
        time,exp=parse_parameters(time,7)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid time.")
        return()

    msg1=await ctx.send(f"About to erase all sonar info older than {time}. Confirm by reacting to this with a ✅.")
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        
    else:
        sonarreset(time)
        await msg1.delete()
        await ctx.message.add_reaction("✅")
        await ctx.send(f"All sonar data older than {time} removed.")
 
@nuny.discord_utils.bot.tree.command(name="cleanup", description="Manually clean up over 7 days old statuses.", guild=nuny.discord_utils.guild)
async def cleanup_tree(interaction: nuny.discord_utils.discord.Interaction):

    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: cleanup")

    r=nuny.db_utils.cleanup()
    await interaction.response.send_message(f"✅ {r} entries were deleted.")

@nuny.discord_utils.bot.command(name="cleanup",help="Manually clean up over 7 days old statuses.")
async def cleanup_cmd(ctx):

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)

    r=nuny.db_utils.cleanup()
    await ctx.send(f"{r} entries were deleted.")
    await ctx.message.add_reaction("✅")
                
@nuny.discord_utils.bot.command(name="advertise", 
                                aliases=['ad','shout','sh'],
                                help='''Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). 
                                        Additionally will set the server status to running.''',
                                ignore_extra=False)
async def advertise_cmd(ctx, world, start, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
 
    username=ctx.message.author.display_name

    if len(start)<6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Start location needs to be over 5 characters.")
        return

    tenmin=datetime.timedelta(minutes=10)+datetime.datetime.now()
    timestamp=int(mktime(tenmin.timetuple()))

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()


    try:
        expansion=int(expansion)
    except ValueError:
        await ctx.send("Invalid expansion")
        return
    if expansion not in range(2,8):
        await ctx.send("Invalid expansion")
        return

    if expansion==7:
        msg=f"About to send this notification to various servers: ```@Dawntrail_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if expansion==6:
        msg=f"About to send this notification to various servers: ```@Endwalker_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if expansion==5:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if expansion in range(2,5):
        msg=f"About to send this notification to various servers: ```@Old_train_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
        
    try:  
        msg1=await ctx.send(msg)
        await msg1.add_reaction("✅")
    except (nuny.discord_utils.commands.errors.CommandInvokeError, nuny.discord_utils.discord.errors.HTTPException) as exc:
        await ctx.message.add_reaction('❌')
        await ctx.send(f"Error sending preview: {exc}")
        return

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
    
        
    else:
        if res:
            reaction, user=res
            logging.debug(reaction.emoji)

            for i in nuny.discord_utils.bot.guilds:
                emoji=nuny.discord_utils.discord.utils.get(i.emojis, name="doggospin")
            await msg1.add_reaction(emoji)
            
            msg=f"**[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            await nuny.discord_utils.post_webhooks(msg,expansion)
            
            if expansion in range(5,8):
                set_status(world,"Running",expansion)
            await ctx.send(f"Messages for **[{world}]** {expansion}.0 train sent. Train start scheduled <t:{timestamp}:R>.")
            
            await msg1.delete()
            await ctx.message.add_reaction('✅')

@nuny.discord_utils.bot.command(name="advmanual", 
                                aliases=['adm','mshout','msh'],
                                help='''Advertise your train. 
                                        Put multi-part parameters in quotes (eg. .mshout "[Twintania] Hunt train starting in 10 minutes at Fort Jobb")''',
                                ignore_extra=False)

async def madvertise(ctx, message, expansion=nuny.config.conf["def_exp"]):
    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return

    await log_cmd(ctx)
 
    username=ctx.message.author.display_name
    
    if len(message)<6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Message needs to be over 5 characters.")
        return


    try:
        expansion=int(expansion)
    except ValueError:
        await ctx.send("Invalid expansion")
        return
    if expansion not in range(2,8):
        await ctx.send("Invalid expansion")
        return

    if expansion==7:
        msg=f"About to send this notification to various servers: ```@Dawntrail_role {message} (Conductor: {username}).``` React with ✅ to send or wait 30 seconds to cancel."
    if expansion==6:
        msg=f"About to send this notification to various servers: ```@Endwalker_role {message} (Conductor: {username}).``` React with ✅ to send or wait 30 seconds to cancel."
    if expansion==5:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role {message} (Conductor: {username}).``` React with ✅ to send or wait 30 seconds to cancel."
    if expansion in range(2,5):
        msg=f"About to send this notification to various servers: ```@Old_train_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
    
    try:  
        msg1=await ctx.send(msg)
        await msg1.add_reaction("✅")
    except (nuny.discord_utils.commands.errors.CommandInvokeError, nuny.discord_utils.discord.errors.HTTPException) as exc:
        await ctx.message.add_reaction('❌')
        await ctx.send(f"Error sending preview: {exc}")
        return

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug ("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            logging.debug (reaction.emoji)

            for i in nuny.discord_utils.bot.guilds:
                emoji=nuny.discord_utils.discord.utils.get(i.emojis, name="doggospin")
            await msg1.add_reaction(emoji)
          
            msg=f"{message} (Conductor: {username})."
            await nuny.discord_utils.post_webhooks(msg,expansion)

            await msg1.delete()
            await ctx.message.add_reaction('✅')
            await scout_log("Messages sent.")
            
@nuny.discord_utils.bot.tree.command(name="shout", description="Advertise your train.", guild=nuny.discord_utils.guild)
async def dvertise_tree(interaction: nuny.discord_utils.discord.Interaction):
    if interaction.channel_id!=nuny.config.conf["discord"]["channels"]["bot"]:
        await interaction.response.send_message("This command is unavailable on this channel.", ephemeral=True)
        return

    await bot_log(f"{interaction.user.display_name}: newshout")
 
    username=interaction.user.display_name

    worldch=[]     
    for w in nuny.config.conf["worlds"]:
        worldch.append(nuny.discord_utils.discord.SelectOption(label=w["name"], value=w["short"][0]))

    expch=[
        nuny.discord_utils.discord.SelectOption(label="DT", value=7),
        nuny.discord_utils.discord.SelectOption(label="EW", value=6),
        nuny.discord_utils.discord.SelectOption(label="SHB", value=5),
        nuny.discord_utils.discord.SelectOption(label="STB", value=4),
        nuny.discord_utils.discord.SelectOption(label="HW", value=3),
        nuny.discord_utils.discord.SelectOption(label="ARR", value=2)]

    shoutbox=nuny.discord_utils.discord.ui.Modal(title="Train advertisement")
    
    expselect=nuny.discord_utils.discord.ui.Select(options=expch,placeholder="Select Expansion",required=True,max_values=1)
    async def expselect_callback(select_interaction: nuny.discord_utils.discord.Interaction):
        await select_interaction.response.defer()
        
    expselect.callback=expselect_callback
    
    explabel=nuny.discord_utils.discord.ui.Label(text="Expansion",component=expselect)
    
    shoutbox.add_item(explabel)    

    wselect=nuny.discord_utils.discord.ui.Select(options=worldch,placeholder="Select World",required=False)
    async def wselect_callback(select_interaction: nuny.discord_utils.discord.Interaction):
        await select_interaction.response.defer()
        
    wselect.callback=expselect_callback
    
    wlabel=nuny.discord_utils.discord.ui.Label(text="World",component=wselect,description="Leave empty if you want custom shout")
    
    shoutbox.add_item(wlabel)    

    mbox=nuny.discord_utils.discord.ui.TextInput(label="Message", placeholder="Advertisement message (any non-standard emojis in 'forced' mode)", required=True, style=nuny.discord_utils.discord.TextStyle.paragraph)

    shoutbox.add_item(mbox)
    
    async def on_submit(modal_interaction: nuny.discord_utils.discord.Interaction):
        expansion = expselect.values[0]
        if wselect.values:
            world=wselect.values[0]
            wname = list(filter(lambda w: w['short'][0] == world, nuny.config.conf["worlds"]))[0]["name"]
        else:
            world=None

        message = mbox.value

        if len(message)<11:
            await modal_interaction.response.send_message("❌ Message needs to be over 10 characters.",ephemeral=True)
            return

        expansion=int(expansion)
        if expansion not in range(2,8):
            await modal_interaction.response.send_message("❌ Invalid expansion", ephemeral=True)
            return

        if world==None:
            msg=f"{message} (Conductor: {username})."
        else:
            tenmin=datetime.timedelta(minutes=10)+datetime.datetime.now()
            timestamp=int(mktime(tenmin.timetuple()))
            msg=f"**[{wname}]** Hunt train starting <t:{timestamp}:R> at {message} (Conductor: {username})."

        await modal_interaction.response.send_message(f"About to following message to many servers. Confirm by reacting to this with a ✅ or wait for timeout.")
        msg1= await modal_interaction.original_response()
        await msg1.add_reaction("✅")
        
        async with aiohttp.ClientSession() as session:
            webhook=nuny.discord_utils.discord.Webhook.from_url(nuny.config.conf["discord"]["preview_webhook"], session=session)
            try:
                await webhook.send(content=f"**@{expansion}.0A** "+msg,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")                        
            except (nuny.discord_utils.discord.errors.HTTPException,nuny.discord_utils.discord.errors.NotFound) as e:
                pass

        def check(reaction, user):
            return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == interaction.user.id

        try:
            res=await nuny.discord_utils.bot.wait_for("reaction_add", check=check,timeout=30)
        except asyncio.TimeoutError:
            logging.debug("Timed out while waiting for reaction.")
            await msg1.edit(content="❌ Timed out. Message not sent.")
            await msg1.clear_reactions()
        else:
            if res:
                timestamp=int(mktime(datetime.datetime.now().timetuple()))
                await bot_log(f"Sending train advertisement:\n```{msg}```")
                await msg1.edit(content="<a:doggospin:1227235974535446628> Sending message to many servers.")

                if world != None:
                    if expansion in range(5,8):
                        set_status(world,"Running",expansion)
                
                await nuny.discord_utils.post_webhooks(msg,expansion)
                
                await msg1.edit(content=f"✅ Messages for {username}'s {expansion}.0 train sent <t:{timestamp}:R>.")
                await msg1.clear_reactions()
        
    shoutbox.on_submit=on_submit
       
    await interaction.response.send_modal(shoutbox)
 