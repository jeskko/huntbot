import datetime,logging,asyncio
from time import mktime

import nuny.config
import nuny.discord_utils

from nuny.sheet_utils import update_from_sheets_to_chat,update_from_sheets_to_compact_chat
from nuny.sheet_utils import worldStatusLoc,worldTimeLoc,fetch_sheet,update_sheet,update_channel
from nuny.log_utils import bot_log,scout_log
from nuny.misc_utils import speculate,mapping,parse_parameters,parse_world
from nuny.sonar import sonar_stats

@nuny.discord_utils.bot.command(name='speculate',help='Speculate about status of a certain world')
async def spec(ctx,world,legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg=speculate(world,legacy)
    await ctx.send(msg)

@nuny.discord_utils.bot.command(name='mapping', aliases=["map",], help='Check mapping data from Sonar')
async def spec(ctx,world,legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg=mapping(world,legacy)
    await ctx.send(msg)


@nuny.discord_utils.bot.command(name='scout', aliases=['sc','scouting'],help='Begin scouting.')
async def scouting(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()
    
    parm=parse_parameters(time,legacy)
    time=0
    l=parm[1]
    stb=parm[2]
    if stb==0:
        statuscell="Up Times!"+worldStatusLoc(world,l)
        status=fetch_sheet(statuscell)[0][0]
        if status=="Dead":
            await ctx.send("Scouting a dead world, adjusting timer.")
            timecell="Up Times!"+worldTimeLoc(world,l)
            time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])+datetime.timedelta(hours=6)    
        await update_sheet(world,"Scouting",time,l)
        await update_channel(world,"Scouting",l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@nuny.discord_utils.bot.command(name='scoutcancel', aliases=['cancel', 'sccancel', 'scc'], help="Cancel scouting. Return server to up status.")
async def scoutcancel(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    l=parm[1]
    stb=parm[2]
    status="Up"
    if stb==0:
        timecell="Up Times!"+worldTimeLoc(world,l)
        time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])
        if time>datetime.datetime.utcnow():
            time=time-datetime.timedelta(hours=6)
            status="Dead"
            await ctx.send("Adjusting time -6h and status to dead because timestamp in future.")
        else:
            time=0
        await update_sheet(world,status,time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@nuny.discord_utils.bot.command(name='scouted', aliases=['scdone','scend'],help='End scouting.')
async def scoutend(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=0
    l=parm[1]
    stb=parm[2]
    if stb==0:
        await update_sheet(world,"Scouted",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@nuny.discord_utils.bot.command(name='start', aliases=['begin','run','go'],help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def begintrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]
    stb=parm[2]

    if stb==0:
        await update_sheet(world,"Running",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@nuny.discord_utils.bot.command(name='end', aliases=['done','dead','finish'],help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def endtrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]
    stb=parm[2]
    if stb==0:
        await update_sheet(world,"Dead",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")
    if nuny.config.conf["sonar"]["enable"]==True:    
        await scout_log(sonar_stats(world,l))

@nuny.discord_utils.bot.command(name="status", aliases=['getstatus','stat'],help='Get train status')
async def getstatus(ctx, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    leg=0
    if legacy[0].capitalize() == "L":
        leg=1
    msg=await update_from_sheets_to_chat(leg)
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")

@nuny.discord_utils.bot.command(name="cstatus", aliases=['compactstatus','cstat','cs'],help='Get compact train status')
async def getstatus(ctx):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    msg=await update_from_sheets_to_compact_chat()
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")

@nuny.discord_utils.bot.command(name="advertise", 
                                aliases=['ad','shout','sh'],
                                help='''Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). 
                                        Additionally will set the server status to running.''',
                                ignore_extra=False)

async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
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

    parm=parse_parameters(None,legacy)
    l=parm[1]
    stb=parm[2]
    if l==0:
        msg=f"About to send this notification to various servers: ```@Dawntrail_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to various servers: ```@Endwalker_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if stb==1:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
 
    msg1=await ctx.send(msg)
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
        if res:
            reaction, user=res
            logging.debug(reaction.emoji)

            for i in nuny.discord_utils.bot.guilds:
                emoji=nuny.discord_utils.discord.utils.get(i.emojis, name="doggospin")
            await msg1.add_reaction(emoji)

            expansion=6
            if l==1:
                expansion=5
            if stb==1:
                expansion=4
            
            msg=f"**[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
            await nuny.discord_utils.post_webhooks(msg,expansion)
            
            time=parm[0]
            if stb==0: 
                await update_sheet(world,"Running",time,l)

            await msg1.delete()
            await ctx.message.add_reaction('✅')

@nuny.discord_utils.bot.command(name="advmanual", 
                                aliases=['adm','mshout','msh'],
                                help='''Advertise your train. 
                                        Put multi-part parameters in quotes (eg. .mshout "[Twintania] Hunt train starting in 10 minutes at Fort Jobb")''',
                                ignore_extra=False)

async def madvertise(ctx, message, legacy="0"):
    if ctx.channel.id != nuny.config.conf["discord"]["channels"]["bot"]:
        return
    username=ctx.message.author.display_name
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    if len(message)<6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Message needs to be over 5 characters.")
        return

    parm=parse_parameters(None,legacy)
    l=parm[1]
    stb=parm[2]
    if l==0:
        msg=f"About to send this notification to various servers: ```@Dawntrail_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to various servers: ```@Endwalker_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
    if stb==1:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."

    msg1=await ctx.send(msg)
    await msg1.add_reaction("✅")

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

            expansion=6
            if l==1:
                expansion=5
            if stb==1:
                expansion=4
            
            msg=f"{message} (Conductor: {username})."
            await nuny.discord_utils.post_webhooks(msg,expansion)

            await msg1.delete()
            await ctx.message.add_reaction('✅')
            if stb!=1:
                await scout_log("Please set the server running manually if needed.")