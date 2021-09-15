import asyncio
import time

import music
import builtins

import random

guild_mps = {}
guild_cache = {}
global alone_list
alone_list = []


def get_music_player(ctx, message=None):
    guild = ctx.guild if ctx else message.guild
    if guild.id not in guild_mps:
        cached = guild_cache.get(guild.id)
        looped, shuffled = False, False
        if cached:
            looped = cached["mp_cookies"][0] if cached.get("mp_cookies") else False
            shuffled = cached["mp_cookies"][1] if cached.get("mp_cookies") else False
        guild_mps[guild.id] = music.MusicPlayer(builtins.client, looped=looped, shuffled=shuffled)
    return guild_mps[guild.id]

async def play(ctx, query, message=None):
    await get_music_player(ctx, message).play(ctx, query, message=message)


async def pause(ctx, message=None):
    await get_music_player(ctx, message).pause(ctx, message)


async def stop(ctx, message=None):
    await get_music_player(ctx, message).stop(ctx, message)


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
        mp.marks = mp.marks + 1 if mp.is_alone() else 0
        if mp.marks >= 2:
            await destroy_player(gid)
            guild_mps.pop(gid)

async def destroy_player(gid):
    mp = guild_mps[gid]
    if gid not in guild_cache: guild_cache[gid] = {}
    guild_cache[gid]["mp_cookies"] = [mp.looped, mp.shuffled]
    await mp.abandon()