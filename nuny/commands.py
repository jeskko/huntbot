import datetime,logging,asyncio
from time import mktime

import nuny.config
import nuny.db_utils
import nuny.discord_utils

from nuny.log_utils import bot_log,scout_log
from nuny.misc_utils import speculate,mapping,health,parse_parameters,parse_world,set_status,get_statuses,get_history,maintenance_reboot
from nuny.sonar import sonar_stats,sonarreset

async def log_cmd(ctx):
    await bot_log(f"{ctx.message.author.display_name} {ctx.message.channel.name}:  {ctx.message.content}")

@nuny.discord_utils.bot.command(name='speculate',help='Speculate about status of a certain world')
async def spec(ctx,world,expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='mapping', aliases=["map",], help='Check mapping data from Sonar')
async def map(ctx,world,expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='health', help='Check last seen data from Sonar')
async def hlth(ctx,world,expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='scout', aliases=['sc','scouting'],help='Begin scouting.')
async def scouting(ctx, world, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='scouted', aliases=['scdone','scend'],help='End scouting.')
async def scoutend(ctx, world, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='start', aliases=['begin','run','go'],help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def begintrain(ctx, world, time=None, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name='end', aliases=['done','dead','finish'],help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def endtrain(ctx, world, time=None, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name="status", aliases=['getstatus','stat'],help='Get train status')
async def getstatus(ctx, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name="history", aliases=['hist'],help='Get status history')
async def gethistory(ctx, world, expansion=nuny.config.conf["def_exp"]):
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

@nuny.discord_utils.bot.command(name="undo",help="Undo a previous status.")
async def undo(ctx,id):
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
    
@nuny.discord_utils.bot.command(name="adjust",aliases=['fix'],help="Adjust timestamp of a previous status.")
async def adjust(ctx,id,time):

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
    
@nuny.discord_utils.bot.command(name="reboot",help="Set reboot timer after maintenance.")
async def reboot(ctx,time):

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

@nuny.discord_utils.bot.command(name="sonarcleanup",help="Clean up sonar data that is older than parameter time.")
async def sonarboot(ctx,time):

    if ctx.channel.id!=nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await log_cmd(ctx)
    time,exp=parse_parameters(time,7)

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
 

@nuny.discord_utils.bot.command(name="cleanup",help="Manually clean up over 7 days old statuses.")
async def cleanup(ctx):

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
async def advertise(ctx, world, start, expansion=nuny.config.conf["def_exp"]):
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