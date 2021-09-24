import asyncio
import pickle
import time
import os
from datetime import datetime
from pytz import timezone
tz = timezone('EST')

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


async def calendar(ctx, month, year):
    kalendar.display(month, year, ctx.message.author.id)
    await ctx.message.author.send(file=discord.File(os.path.join(os.getcwd(), "assets/temp_calendar.png")))

async def check_calendar():
    now = datetime.now(tz)
    cht = now.strftime("%I")
    if cht[0] == "0": cht = cht[1:]
    ctime = cht + now.strftime(":%M%p").lower()
    print(now.month, now.year, now.day, ctime)
    tasks = kalendar.get_plans(now.month, now.year, now.day, ctime)
    for uid in tasks.keys():
        user = await builtins.client.fetch_user(int(uid))
        for task in tasks[uid]:
            await user.send(task)

async def plan(ctx, date, task, ctime):
    if ctime == None:
        now = datetime.now(tz)
        cht = now.strftime("%I")
        if cht[0] == "0": cht = cht[1:]
        ctime = cht + now.strftime(":%M%p")
    ctime = ctime.lower()
    kalendar.schedule(task, date, ctime, ctx.message.author.id)
    await ctx.send(f"**{task}** scheduled for **{date}** at **{ctime}**")

async def play(ctx, query, message=None):
    if query.find("spotify") != -1:
        await get_music_player(ctx, message).play_spotify(ctx, query, message=message)
    else:
        await get_music_player(ctx, message).play(ctx, query, message=message)


async def pause(ctx, message=None):
    await get_music_player(ctx, message).pause(ctx, message)


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

