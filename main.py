import discord
import hookcord
import utils
import builtins
import sys

builtins.client = hookcord.Bot(intents=discord.Intents.default(), command_prefix="k!")
client = builtins.client
import backend
slash = hookcord.SlashCommand(client, sync_commands=True)


@client.event
async def on_ready():
    print("Ready!")
    guild_ids = [guild.id for guild in client.guilds]
    utils.get_emoji_list(client)

@client.event
async def on_raw_reaction_add(payload):
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
    await channel.send(content="**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.", embed=utils.default_embed)

@client.event
async def on_message(message):
    if message.channel.name == "song-requests":
        if message.author == client.user: return
        await message.delete()
        await backend.play(None, message.content, message=message)

@slash.slash(**utils.cmd_gen("play"))
async def slash_play(ctx, song):
    await ctx.defer()
    await backend.play(ctx, song)

@client.command(pass_context=True)
async def join(ctx):
    """Joins the same voice channel as the user whom called the command"""

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(ctx.message.author.voice.channel)

    await ctx.message.author.voice.channel.connect()

@client.command(pass_context=True)
async def shutdown(ctx):
    sys.exit(2)

client.run('MjAwNDgwMTg1MDQ3MzE4NTI4.V33luA.HHJucLwp1FAqiXxX-4-hO3TiabQ')
