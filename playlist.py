from hookcord import HookedContext
import discord

async def playlist_add(ctx: HookedContext, playlist_name):
    playlist_categories = [category for category in ctx.guild.categories if category.name == "playlist"]
    if not playlist_categories:
        playlist_category = await ctx.guild.create_category("playlist", position=9999)
        await playlist_category.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
    else:
        playlist_category = playlist_categories[0]
    channel_query = [channel for channel in playlist_category.text_channels if channel.topic == str(ctx.author.id) and channel.name == playlist_name]
    if not channel_query:
        playlist_channel = await playlist_category.create_text_channel(playlist_name, topic=str(ctx.author.id))
        await playlist_channel.set_permissions(ctx.author, read_messages=True)
    else:
        playlist_channel = channel_query[0]
    name = ctx.author.display_name if ctx.author.display_name else ctx.author.name
    embed = discord.Embed(title=f"{playlist_name}", description=f"**Songs: 0**",
                          colour=0xfc8403)
    embed.set_author(name=f"{name}'s Playlist", icon_url=ctx.author.display_avatar.url)
    msg = await playlist_channel.send(content="Ignore Me")
    await msg.edit(content="", embed=embed)