import asyncio
import os
from datetime import datetime, timedelta

from pytz import timezone
import discord
from discord.ext import commands
import hookcord
import utils
import builtins

import sys

from datastasis import Stasis


tz = timezone('US/Eastern')
client = hookcord.Bot(intents=discord.Intents.all(), command_prefix=commands.when_mentioned_or("k!"))
builtins.client = client

global guild_settings
global uptime
guild_settings_path = os.path.join(os.getcwd(), "guild_settings.json")
guild_settings = utils.JOpen(guild_settings_path, "r+")
if guild_settings is None: guild_settings = {}
builtins.guild_settings = guild_settings

import backend

slash = hookcord.SlashCommand(client, sync_commands=True)


@client.event
async def on_ready():
    guild_ids = [guild.id for guild in client.guilds]
    utils.get_emoji_list(client)
    client.loop.create_task(minutetick())
    s = Stasis(name="MusicPlayerMemory")
    if s.has_memory():
        mpm = s.access()
        await backend.reconstruct_players(mpm)
        s.terminate()
    print("Ready!")


@client.event
async def on_raw_reaction_add(payload):
    global guild_settings
    channel = await client.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = payload.emoji
    if payload.user_id == client.user.id: return

    if await backend.process_reaction(payload.member, message, emoji): return

    if channel.name != "song-requests":
        return
    if message.author != client.user:
        return
    valid_reaction = await utils.validate_reactions(message, emoji)
    if valid_reaction is None:
        return

    user = await client.fetch_user(payload.user_id)
    await valid_reaction.remove(user)

    gs = guild_settings.get(str(channel.guild.id))
    if gs:
        if [r for r in payload.member.roles if r.id == gs.get("music_role")] == [] and gs.get("music_role"):
            return

    emoji = emoji.name
    if emoji == '⏯️': await backend.pause(None, message)
    if emoji == '⏹️': await backend.stop(None, message)
    if emoji == '⏭️': await backend.skip(None, message)
    if emoji == '🔁': await backend.loop(None, message)
    if emoji == '🔀': await backend.shuffle(None, message)


@client.event
async def on_guild_join(guild):
    channel = await guild.create_text_channel("song-requests")
    msg = await channel.send(
        content="**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.",
        embed=utils.default_embed)
    await utils.validate_reactions(msg, discord.PartialEmoji.from_str('😀'))


@client.event
async def on_message(message: discord.Message):
    global guild_settings
    await client.process_commands(message)
    if message.channel.name == "song-requests":
        if message.author == client.user:
            return
        await message.delete()

        if not await message.channel.history().flatten():
            msg = await message.channel.send(
                content="**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.",
                embed=utils.default_embed)
            await utils.validate_reactions(msg, '😀')

        gs = guild_settings.get(str(message.author.guild.id))
        if gs:
            if [r for r in message.author.roles if r.id == gs.get("music_role")] == [] and gs.get("music_role"):
                return

        if message.content.startswith("-queue_image"):
            await backend.music_player_preference(None, "queue_image", message.content.replace("-queue_image ", ""),
                                                  message=message)
        elif message.content.startswith("-queue_description"):
            await backend.music_player_preference(None, "queue_description",
                                                  message.content.replace("-queue_description ", ""), message=message)
        elif message.content.startswith("-queue_color"):
            await backend.music_player_preference(None, "queue_color",
                                                  int(message.content.replace("-queue_color ", "")), message=message)
        else:
            await backend.play(None, message.content, message=message)

@client.command(pass_context=True)
async def restart(ctx):
    if ctx.message.author.id not in [211664640831127553]: return
    backend.dump_mps()
    # print([sys.executable] + [os.path.abspath(os.path.join(os.getcwd(), sys.argv[0]))])
    # os.execv(sys.executable, [sys.executable] + [os.path.abspath(os.path.join(os.getcwd(), sys.argv[0]))])
    os.execv(sys.executable, [sys.argv[0]])

@client.command(name="playlist", pass_context=True)
async def _playlist(ctx, name):
    await backend.playlist(ctx, name)





@client.command(pass_context=True)
async def whatis(ctx, variable, do_repr=False):
    variables = globals().copy()
    variables.update(locals())
    varis = variable.split(".")
    variable = variables.get(varis[0])

    if variable not in variables:
        res = backend.whatis(varis[0])

    for v in varis:
        res = getattr(res, v)

    if do_repr:
        await ctx.send(repr(res))
    else:
        await ctx.send(res)


@client.command(pass_context=True)
async def execute(ctx, *args):
    if ctx.message.author.id not in [211664640831127553]: return
    cmds = " ".join(args).split(" | ")
    for command in cmds:
        await ctx.send(str(exec(command)))

@client.command(pass_context=True)
async def status(ctx):
    global uptime
    if ctx.message.author.id not in [211664640831127553]: return
    await ctx.send(embed=backend.get_status(uptime))



async def minutetick():
    global uptime
    uptime = 0
    while True:
        if uptime % 240 == 0 and uptime != 0:
            backend._reload_music()
            # print("RESTARTING")
            # backend.dump_mps()
            # os.execv(sys.executable, ['python'] + [os.path.abspath(sys.argv[0])])
        await backend.expire_players()
        await backend.mark_alone()
        await backend.check_calendar()
        await backend.tick(uptime)
        await asyncio.sleep(60)
        uptime += 1


if __name__ == "__main__":
    secrets = utils.JOpen("cache/secrets.json", "r+")
    client.run(secrets["main-bot"]) #Main bot
    #client.run(secrets["test-bot"])  # Test bot (Ezreal)
