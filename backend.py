import music
import builtins

guild_mps = []


def get_music_player(ctx, message=None):
    guild = ctx.guild if ctx else message.guild
    if guild.id not in guild_mps: guild_mps[guild.id] = mp = music.MusicPlayer(builtins.client)
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