import asyncio
import os

import discord
from discord.ext import commands
import hookcord
import utils
import builtins

client = hookcord.Bot(intents=discord.Intents.default(), command_prefix=commands.when_mentioned_or("k!"))
builtins.client = client
import backend

slash = hookcord.SlashCommand(client, sync_commands=True)

global guild_settings
guild_settings_path = os.path.join(os.getcwd(), "guild_settings.json")
guild_settings = utils.JOpen(guild_settings_path, "r+")
if guild_settings is None: guild_settings = {}


@client.event
async def on_ready():
    print("Ready!")
    guild_ids = [guild.id for guild in client.guilds]
    utils.get_emoji_list(client)
    client.loop.create_task(minutetick())


@client.event
async def on_raw_reaction_add(payload):
    global guild_settings
    channel = await client.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = payload.emoji

    if payload.user_id == client.user.id: return
    if channel.name != "song-requests": return
    if message.author != client.user: return

    valid_reaction = await utils.validate_reactions(message, emoji)
    if valid_reaction is None: return

    user = await client.fetch_user(payload.user_id)
    await valid_reaction.remove(user)

    gs = guild_settings.get(str(channel.guild.id))
    if gs:
        if [r for r in payload.member.roles if r.id == gs.get("music_role")] == [] and gs.get("music_role"): return

    emoji = emoji.name
    if emoji == '⏯️': await backend.pause(None, message)
    if emoji == '⏹️': await backend.stop(None, message)
    if emoji == '⏮️': await backend.previous(None, message)
    if emoji == '⏭️': await backend.skip(None, message)
    if emoji == '🔁': await backend.loop(None, message)
    if emoji == '🔀': await backend.shuffle(None, message)
    if emoji == '⭐': await backend.add_to_playlist(None, message)
    if emoji == '❌': await backend.remove_from_playlist(None, message)


@client.event
async def on_guild_join(guild):
    channel = await guild.create_text_channel("song-requests")
    msg = await channel.send(
        content="**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.",
        embed=utils.default_embed)
    await utils.validate_reactions(msg, '😀')


@client.event
async def on_message(message):
    global guild_settings
    if message.channel.name == "song-requests":
        if message.author == client.user: return
        await message.delete()

        if not await message.channel.history().flatten():
            msg = await message.channel.send(
                content="**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.",
                embed=utils.default_embed)
            await utils.validate_reactions(msg, '😀')

        gs = guild_settings.get(str(message.author.guild.id))
        if gs:
            if [r for r in message.author.roles if r.id == gs.get("music_role")] == [] and gs.get("music_role"): return

        await backend.play(None, message.content, message=message)


@slash.subcommand(base="set", **utils.command_generator("set_dj_role"))
async def use_dj_role(ctx, role=None):  # Defines a new "context" (ctx) command called "ping."
    global guild_settings
    if not ctx.author.permissions_in(ctx.channel).administrator: return await ctx.send(
        "You don't have permission for that (Administrator only)", hidden=True)
    id = str(ctx.author.guild.id)
    if not id in guild_settings: guild_settings[id] = {}
    if not role:
        guild_settings[id]["music_role"] = None
        utils.JOpen(guild_settings_path, "w+", guild_settings)
        return await ctx.send("Removed music role", hidden=True)
    guild_settings[id]["music_role"] = role.id
    print(guild_settings, id)
    utils.JOpen(guild_settings_path, "w+", guild_settings)
    return await ctx.send(f"Set music role as **{role}**", hidden=True)


async def minutetick():
    uptime = 0
    while True:
        if uptime % 240 == 0 and uptime != 0:
            backend._reload_music()
        await backend.expire_players()
        await backend.mark_alone()
        await asyncio.sleep(60)
        uptime += 1


#client.run('MjAwNDgwMTg1MDQ3MzE4NTI4.V33luA.HHJucLwp1FAqiXxX-4-hO3TiabQ') #Main bot
client.run('MjAwOTkyNTc3MTc5MjIyMDE2.V3_C7A.4d4DaKOALJDo4HqANVe6PJDkQl8')  # Test bot (Ezreal)
