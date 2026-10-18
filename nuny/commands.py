import datetime,logging,asyncio
from time import mktime

import nuny.config
import nuny.db_utils
import nuny.discord_utils

import aiohttp

from typing import Optional

from discord import app_commands
from discord.ext import commands

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

bot=nuny.discord_utils.bot

async def log_cmd(ctx: commands.Context):
    if ctx.interaction is not None:
        args = " ".join(str(value) for _, value in ctx.interaction.namespace)
        await bot_log(f"{ctx.author.display_name}: {ctx.command.qualified_name}: {args}")
    else:
        await bot_log(f"{ctx.message.author.display_name} {ctx.message.channel.name}:  {ctx.message.content}")
    return



async def cmd_verifier(
        ctx: commands.Context, 
        expansion: int | None = None, 
        exprange: range | None = None, 
        id: int | None = None,
        silent: bool = False
):
    """Verify parameters for a command, complain if necessary,
    and log the command. Returns True if parameters are valid, False otherwise.
    
    Parameters
    ----------
    ctx: commands.Context
        The command context
    expansion: int | None
        The expansion to verify
    exprange: range | None
        The valid range of expansions
    id: int | None
        The ID to verify
    silent: bool
        Whether to send the response ephemeral
    """
    
    is_slash = ctx.interaction is not None

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        if is_slash:
            await ctx.send("This command is unavailable on this channel.", ephemeral=True)
        return False

    await log_cmd(ctx)

    if exprange is not None and expansion not in exprange:
        await ctx.send("Untracked expansion", ephemeral = silent)
        if not is_slash:
            await ctx.message.add_reaction("❓")
        return False

    if id is not None:
        try:
            id=int(id)
        except ValueError:
            await ctx.message.add_reaction("❓")
            await ctx.send("Invalid ID.", ephemeral = silent)
            return False

    return True



@bot.hybrid_command(name='speculate',help='Speculate about status of a certain world')
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.describe(world="World", expansion="Expansion")
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def speculate_cmd(
    ctx: commands.Context,
    world: str,
    expansion: int = nuny.config.conf["def_exp"],
    silent: bool = False,
):
    """Speculate about the status of a certain world. 

    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=silent)

    if not await cmd_verifier(ctx,expansion=expansion,exprange=range(5,8),silent=silent):
        return

    msg=speculate(world, expansion)
    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(msg, ephemeral=silent)
    return    



@bot.hybrid_command(name="map", aliases=['mapping'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=allexpansionchoices)
async def map_cmd(
    ctx: commands.Context,
    world: str, 
    expansion: int = nuny.config.conf["def_exp"],
    silent: bool = False
):
    """Check mapping data from Sonar for a world and expansion.
    
    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=silent)

    if not await cmd_verifier(ctx,expansion=expansion,exprange=range(2,8),silent=silent):
        return

    try:
        msg=mapping(world, expansion)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=True)
        return
    
    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(msg, ephemeral=silent)



@bot.hybrid_command(name="health")
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=allexpansionchoices)
async def hlth_cmd(
    ctx: commands.Context,
    world: str, 
    expansion: int = nuny.config.conf["def_exp"],
    silent: bool = False
):
    """Check last seen data from Sonar for a world and expansion.
    
    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=silent)

    if not await cmd_verifier(ctx,expansion=expansion,exprange=range(2,8),silent=silent):
        return

    try:
        msg=health(world, expansion)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=silent)
        return()

    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(msg, ephemeral=silent)



@bot.hybrid_command(name="scout", aliases=['sc', 'scouting'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def scouting_cmd(
    ctx: commands.Context,
    world: str, 
    expansion: int = nuny.config.conf["def_exp"],
):
    """Begin scouting. This will set the world to Scouting.
    
    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=False):
        return

    try:
        world=parse_world(world)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=False)
        return()

    try:
        set_status(world,"Scouting",expansion,"last")
        await nuny.discord_utils.ok_reaction(ctx)
        await ctx.send(f"{world} {expansion}.0 scouting started.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send(f"Error: {ex}", ephemeral=False)



@bot.hybrid_command(name="scend", aliases=['scdone','scouted'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def scoutend_cmd(
    ctx: commands.Context,
    world: str, 
    expansion: int = nuny.config.conf["def_exp"],
):
    """End scouting.
    
    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=False):
        return

    try:
        world=parse_world(world)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=False)
        return()

    try:
        set_status(world,"Scouted",expansion,"last")
        await nuny.discord_utils.ok_reaction(ctx)
        await ctx.send(f"{world} {expansion}.0 scouting complete.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send(f"Error: {ex}", ephemeral=False)



@bot.hybrid_command(name="run",aliases=['begin','start','go'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def begintrain_cmd(
    ctx: commands.Context, 
    world: str, 
    time: str | None,
    expansion: int = nuny.config.conf["def_exp"],
):
    """Start train. Time can be manually set in form "+15" (minutes) or "15:24" (server time)

    Parameters
    ----------
    world: str
        World
    time: str | None
        Start time (optional, UTC/ST)
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=False):
        return

    try:
        world=parse_world(world)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=False)
        return()
    
    try:
        (time,expansion)=parse_parameters(time,expansion)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid parameters.", ephemeral=False)
        return()

    timetext=f"<t:{int(time.timestamp())}:R>"

    try:
        set_status(world,"Running",expansion,time)
        await nuny.discord_utils.ok_reaction(ctx)
        await ctx.send(f"{world} {expansion}.0 set to running {timetext}.")
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send(f"Error: {ex}", ephemeral=False)



@bot.hybrid_command(name="end", aliases=['done','dead','finish'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def endtrain_cmd(
    ctx: commands.Context, 
    world: str, 
    time: str | None, 
    expansion: int = nuny.config.conf["def_exp"],
):
    """End train. Time can be manually set in form "+15" (minutes) or "15:24" (server time)
    
    Parameters
    ----------
    world: str
        World
    time: str | None
        Start time (optional, UTC/ST)
    expansion: int
        Expansion
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=False):
        return

    try:
        world=parse_world(world)
    except ValueError as ex:
        await bot_log(f"ValueError: {ex}")
        await ctx.send("Invalid world.", ephemeral=False)
        return()
    try:
        (time,expansion)=parse_parameters(time,expansion)
        set_status(world,"Dead",expansion,time)
        await nuny.discord_utils.ok_reaction(ctx)

        timetext=f"<t:{int(time.timestamp())}:R>"

        if nuny.config.conf["sonar"]["enable"]==True:
            await ctx.send(f"{world} {expansion}.0 set to Dead {timetext}.\n{sonar_stats(world,expansion)}")
        else:
            await ctx.send(f"{world} {expansion}.0 set to Dead {timetext}.")
    except ValueError as ex:
        await ctx.send(f"Error: {ex}", ephemeral=True)
        await bot_log(f"ValueError: {ex}")



@bot.hybrid_command(name="status", aliases=['getstatus','stat'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(expansion=expansionchoices)
async def getstatus_cmd(
    ctx: commands.Context,
    expansion: int = nuny.config.conf["def_exp"],
    silent: bool = False
):
    """Get train status for an expansion.
    
    Parameters
    ----------
    expansion: int
        Expansion
    silent: bool
        Silent mode
    """

    await ctx.defer(ephemeral=silent)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=silent):
        return

    try:
        msg=get_statuses(expansion)
        await nuny.discord_utils.ok_reaction(ctx)
        await ctx.send(msg, ephemeral = silent)
    except ValueError as ex:
        await ctx.send(f"Error: {ex}", ephemeral = silent)
        await bot_log(f"ValueError: {ex}")



@bot.hybrid_command(name="history", aliases=['hist'])
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=worldchoices, expansion=expansionchoices)
async def gethistory_cmd(
    ctx: commands.Context,
    world: str,
    expansion: int = nuny.config.conf["def_exp"],
    silent: bool = False
):
    """Get command history for a world.
    
    Parameters
    ----------
    world: str
        World
    expansion: int
        Expansion
    silent: bool
        Silent mode
    """

    await ctx.defer(ephemeral=silent)

    if not await cmd_verifier(ctx, expansion=expansion, exprange=range(5,8), silent=silent):
        return

    try:
        world=parse_world(world)
        await nuny.discord_utils.ok_reaction(ctx)
    except ValueError as ex:
        await ctx.message.add_reaction("❓")
        await ctx.send(f"Error: {ex}", ephemeral = silent)
        await bot_log(f"ValueError: {ex}")
        return
    
    msg=get_history(world,expansion)
    await ctx.send(msg, ephemeral = silent)



@bot.hybrid_command(name="undo")
@app_commands.guilds(nuny.discord_utils.guild)
async def undo_cmd(
    ctx: commands.Context, 
    status: int
):
    """Undo a previous status.
    
    Parameters
    ----------
    status: int
        Status ID (get this with /history)
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, id=status, silent=False):
        return

    nuny.db_utils.delstatus(status)
    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(f"Status #{status} deleted.")



@bot.hybrid_command(name="adjust", aliases=['fix'])
@app_commands.guilds(nuny.discord_utils.guild)
async def adjust_cmd(
    ctx: commands.Context,
    status: int, 
    time: str
):
    """Adjust timestamp of a previous status.
    
    Parameters
    ----------
    status: int
        Status ID (get this with /history)
    time: str
        Time (UTC/ST)
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, id=status, silent=False):
        return

    time,exp=parse_parameters(time,7)
    nuny.db_utils.settime(status,time)
    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(f"Status #{status} adjusted to {time}.")
    


@bot.hybrid_command(name="reboot")
@app_commands.guilds(nuny.discord_utils.guild)
@app_commands.choices(world=[app_commands.Choice(name="All", value="All")] + worldchoices)
async def reboot_cmd(
    ctx: commands.Context, 
    time: str, 
    world: str = 'All'
):
    """Set reboot timer after maintenance. Also clean up pre-maintenance Sonar data.

    Parameters
    ----------
    time: str
        Estimated server reset time (UTC/ST)
    world: str
        World
    """

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, silent=False):
        return

    time,exp=parse_parameters(time,7)

    if world == 'All':
        msg1 = await ctx.send(f"About to set all worlds maintenance end to time {time} and clean up Sonar history. Confirm by reacting to this with a ✅.")
    else:
        try:
            parsed_world = parse_world(world)
        except ValueError as ex:
            await ctx.message.add_reaction("❓")
            await ctx.send(f"Error: {ex}", ephemeral = False)
            await bot_log(f"ValueError: {ex}")
            return
        msg1 = await ctx.send(f"About to set world '{parsed_world}' maintenance end to time {time} and clean up Sonar history. Confirm by reacting to this with a ✅.")

    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.edit(content="❌ Timed out. Servers are not reset.")
        await msg1.clear_reactions()
        
    else:
        if world == 'All':
            maintenance_reboot(time)
            sonarreset(time)
            await msg1.edit(content=f"All servers adjusted for server reboot at {time}.")
        else:
            maintenance_reboot(time, parsed_world)
            sonarreset(time, parsed_world)
            await msg1.edit(content=f"World server '{parsed_world}' adjusted for server reboot at {time}.")
        await msg1.clear_reactions()
        await nuny.discord_utils.ok_reaction(ctx)


 
@bot.hybrid_command(name="cleanup", guild=nuny.discord_utils.guild)
async def cleanup_tree(
    ctx: commands.Context
):
    """Manually clean up over 7 days old statuses. (For staff use)"""

    await ctx.defer(ephemeral=False)

    if not await cmd_verifier(ctx, silent=False):
        return

    r=nuny.db_utils.cleanup()
    await nuny.discord_utils.ok_reaction(ctx)
    await ctx.send(f"{r} entries were deleted.")
                


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

    tenmin=datetime.timedelta(minutes=10)+datetime.datetime.now(datetime.timezone.utc)
    timestamp=int(tenmin.timestamp())

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
            tenmin=datetime.timedelta(minutes=10)+datetime.datetime.now(datetime.timezone.utc)
            timestamp=int(tenmin.timestamp())
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
                timestamp=int(mktime(datetime.datetime.now(datetime.timezone.utc).timetuple()))
                await bot_log(f"Sending train advertisement:\n```{msg}```")
                await msg1.edit(content="<a:doggospin:1227235974535446628> Sending message to many servers.")

                if world != None:
                    print(world)
                    if expansion in range(5,8):
                        set_status(parse_world(world),"Running",expansion)
                
                await nuny.discord_utils.post_webhooks(msg,expansion)
                
                await msg1.edit(content=f"✅ Messages for {username}'s {expansion}.0 train sent <t:{timestamp}:R>.")
                await msg1.clear_reactions()
        
    shoutbox.on_submit=on_submit
       
    await interaction.response.send_modal(shoutbox)
 