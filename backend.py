import time
import os
from datetime import datetime

import psutil
from pytz import timezone

import reactions

tz = timezone('US/Eastern')

import discord

import kalendar
import music
import builtins

import random
import importlib

import utils


from datastasis import Stasis

guild_mps = {}
guild_cache = {}
global alone_list
alone_list = []

guild_settings_path = os.path.join(os.getcwd(), "guild_settings.json")
guild_settings = builtins.guild_settings

react_cache_path = os.path.join(os.getcwd(), "cache/react_cache.json")
react_cache = utils.JOpen(react_cache_path, "r+", forced=True)
react_cache.get("messages", [])
react_cache.get("guilds", {})
react_manager = reactions.ReactChan(builtins.client, react_cache)

global status_message
global test_channel
test_channel = None
status_message = None

def _reload_music():
    for gid in guild_mps.keys():
        if not guild_cache.get(gid): guild_cache[gid] = {}
        guild_cache[gid]["cached_player"] = guild_mps[gid].memory_dict()
    guild_mps.clear()
    importlib.reload(music)
    for gid in list(guild_cache.keys()):
        if not guild_cache[gid].get("cached_player"): continue
        memory = guild_cache[gid].get("cached_player")
        guild_mps[gid] = music.MusicPlayer.from_dict(memory)
        guild_cache[gid].pop("cached_player")


def get_music_player(ctx, message=None):
    guild = ctx.guild if ctx else message.guild
    if guild.id not in guild_mps:
        cached = guild_cache.get(guild.id)
        looped, shuffled = False, False
        if cached:
            looped = cached["mp_cookies"][0] if cached.get("mp_cookies") else False
            shuffled = cached["mp_cookies"][1] if cached.get("mp_cookies") else False
        pref = {}
        if guild_settings.get(str(guild.id)):
            pref = guild_settings.get(str(guild.id)).get("preferences", {})
        guild_mps[guild.id] = music.MusicPlayer(builtins.client, looped=looped, shuffled=shuffled, preferences=pref)
    return guild_mps[guild.id]

async def add_auto_role(channel, role, emoji):
    return await react_manager.add_auto_role(channel, role, emoji)

async def calendar(ctx, month, year):
    kalendar.display(month, year, ctx.message.author.id)
    await ctx.message.author.send(file=discord.File(os.path.join(os.getcwd(), "assets/temp_calendar.png")))

async def check_calendar():
    now = datetime.now(tz=tz)
    cht = now.strftime("%I")
    if cht[0] == "0": cht = cht[1:]
    ctime = cht + now.strftime(":%M%p").lower()
    tasks = kalendar.get_plans(now.month, now.year, now.day, ctime)
    for uid in tasks.keys():
        user = await builtins.client.fetch_user(int(uid))
        for task in tasks[uid]:
            await user.send(task)

async def create_react_message(channel, name, description):
    return await react_manager.create_react_message(channel, name, description)

async def delete_reaction(channel, emoji):
    channel_object = react_manager.get_channel_object(channel.guild, channel)
    if not channel_object: return "Reaction message not found."
    message = channel_object.get("message")
    if not message: return "Reaction message not found."
    message = await channel.fetch_message(message)
    return await react_manager.remove_reaction(channel, emoji)

async def delete_react_message(channel):
    return await react_manager.delete_react_message(channel)

async def plan(ctx, date, task, ctime):
    if ctime == None:
        now = datetime.now(tz=tz)
        cht = now.strftime("%I")
        if cht[0] == "0": cht = cht[1:]
        ctime = cht + now.strftime(":%M%p")
    ctime = ctime.lower()
    kalendar.schedule(task, date, ctime, ctx.message.author.id)
    return ctime

async def play(ctx, query, message=None):
    if query.find("spotify") != -1:
        await get_music_player(ctx, message).play_spotify(ctx, query, message=message)
    else:
        await get_music_player(ctx, message).play(ctx, query, message=message)


async def pause(ctx, message=None):
    await get_music_player(ctx, message).pause(ctx, message)

async def process_reaction(member, message, emoji):
    if not react_manager.is_react_message(message): return False
    reaction = utils.validate_reaction(message, emoji)
    if not reaction: return False
    try: await react_manager.process_raw_reaction(member, message, emoji)
    except discord.errors.Forbidden: pass
    user = await builtins.client.fetch_user(member.id)
    await reaction.remove(user)
    return True

async def stop(ctx, message=None):
    await get_music_player(ctx, message).stop(ctx, message)

async def music_player_preference(ctx, setting, value, message=None):
    guild = ctx.guild if ctx else message.guild
    gid = guild.id
    if not str(gid) in guild_settings: guild_settings[str(gid)] = {}
    GS = guild_settings[str(gid)]
    if not "preferences" in GS: GS["preferences"] = {}
    if value: GS["preferences"][setting] = value
    else:
        if hasattr(GS, setting): GS.pop(setting)
    utils.JOpen(guild_settings_path, "w+", guild_settings)
    get_music_player(ctx, message).update_preferences(GS)


async def previous(ctx, message=None):
    await get_music_player(ctx, message).previous(ctx, message)


async def skip(ctx, message=None):
    await get_music_player(ctx, message).skip(ctx, message)


async def loop(ctx, message=None):
    await get_music_player(ctx, message).loop(ctx, message)


async def shuffle(ctx, message=None):
    await get_music_player(ctx, message).shuffle(ctx, message)


async def add_to_playlist(ctx, message=None):
    pass


async def remove_from_playlist(ctx, message=None):
    pass

async def source_volume(ctx, message=None, volume=0.5):
    await get_music_player(ctx, message).source_volume(ctx, message=message, volume=volume)
    try: await ctx.send(f"Source volume set to: **{volume}**")
    except: pass

async def player_volume(ctx, message=None, volume=0.5):
    await get_music_player(ctx, message).volume(ctx, message=message, volume=volume)
    try: await ctx.send(f"Player volume set to: **{volume}**")
    except: pass

async def expire_players():
    st = time.time()
    minutes = 10
    pop_list = []
    for gid in guild_mps.keys():
        if st - guild_mps[gid].check_time() >= minutes*60:
            pop_list.append(gid)
            await destroy_player(gid)

    [guild_mps.pop(gid) for gid in pop_list]
    pop_list.clear()

async def mark_alone():
    global alone_list
    if not alone_list: alone_list = list(guild_mps.keys())
    for i in range(1000):
        if not alone_list: break
        gid = alone_list.pop(random.randint(0, len(alone_list)-1))
        mp = guild_mps[gid]
        mp.marks = mp.marks + 1 if await mp.is_alone() else 0
        if mp.marks >= 2:
            await destroy_player(gid)
            guild_mps.pop(gid)

async def destroy_player(gid):
    mp = guild_mps[gid]
    if gid not in guild_cache: guild_cache[gid] = {}
    guild_cache[gid]["mp_cookies"] = [mp.looped, mp.shuffled]
    await mp.abandon()

async def reconstruct_players(restart_list):
    for key in restart_list:
        mp = music.MusicPlayer.from_restart(builtins.client, key, restart_list[key])
        mp.persistent_message = await music.MusicPlayer.get_persistent_message(builtins.client.get_guild(key))
        [await q[2].validate() for q in mp.queue]
        [await q[2].validate() for q in mp.history]
        guild_mps[key] = mp
        await mp.check_song()

def dump_mps():
    t = {}
    for key in guild_mps.keys():
        t[key] = guild_mps[key].pickle_dict()
    s = Stasis(name="MusicPlayerMemory")
    s.store(t)

def get_status(uptime, interval=1):
    dt = datetime.now().strftime("%I:%M:%S %p")
    embed = discord.Embed(tile="Status", description=f"**Uptime: {round(uptime / 60, 2)} hours** | **Current Tme:** {dt}", color=0xfc8403)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/895721446054166599/895721488777347132/kawii-chan.png")
    embed.add_field(name="Music Players", value=len(guild_mps.keys()), inline=False)
    ctp = psutil.cpu_times_percent(interval=interval)
    embed.add_field(name="Current CPU Usage",
                    value=f"**Processes:** {ctp.user}% | **System:** {ctp.system}% | **Idle:** {ctp.idle}%  ", inline=False)
    try:
        loadavg = [f"**{x / psutil.cpu_count() * 100}%**" for x in psutil.getloadavg()]
    except OSError:
        loadavg = ["**N/A**", "**N/A**", "**N/A**"]
    embed.add_field(name="CPU 1-Min", value=loadavg[0])
    embed.add_field(name="CPU 5-Min", value=loadavg[1])
    embed.add_field(name="CPU 15-Min", value=loadavg[2])

    embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().percent}%")
    embed.add_field(name="Disk Usage", value=f"{psutil.disk_usage('/').percent}%")

    process = psutil.Process()
    pstatus = f"**State:** {process.status()} | **Started:** {datetime.fromtimestamp(process.create_time()).strftime('%B %d, %I:%M:%S %p')}"
    embed.add_field(name="Process Status", value=pstatus, inline=False)
    embed.add_field(name=f"Working Path", value=process.cwd(), inline=False)
    embed.add_field(name=f"Python Path", value=process.exe(), inline=False)
    return embed

async def tick(uptime):
    await expire_players()
    await mark_alone()
    await check_calendar()
    await update_status(uptime)

async def update_status(uptime):
    global status_message
    global test_channel
    if not test_channel:
        test_channel = builtins.client.get_channel(896683147968786442)
    if not status_message:
        status_message = await test_channel.fetch_message(896683300008120350)
    await status_message.edit(embed=get_status(uptime, 0))

