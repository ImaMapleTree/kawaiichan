import discord
from discord.ext.commands.bot import Bot
import random
import copy

class ReactChan(): #Probably a 1 instance class created in the backend
    DEFAULT_JSON = {"auto_roles": {}, "reaction_type": {}}
    EMOJI_LIST= ["😀","😃","😄","😁","😆","😅","🤣","😂","🙂","🙃","😉","😊","😇","🥰","😍","🤩","😘","😗","☺️","😚","😙","😋","😛","😜","🤪","😝","🤑","🤗","🤭","🤫","🤔","🤐","🤨","😐","😑","😶","😶‍","🌫️","😏","😒","🙄","😬","😮","‍💨","🤥","😌","😔","😪","🤤","😴","😷","🤒","🤕","🤢","🤮","🤧","🥵","🥶","🥴","😵","😵‍","💫","🤯","🤠","🥳","😎","🤓","🧐","😕","😟","🙁","☹️","😮","😯","😲","😳","🥺","😦","😧","😨","😰","😥","😢","😭","😱","😖","😣","😞","😓","😩","😫","🥱","😤","😡","😠","🤬","😈","👿","💀","☠️","💩","🤡","👹","👺","👻","👽","👾","🤖","😺","😸","😹","😻","😼","😽","🙀","😿","😾","🙈","🙉","🙊","💋","💌","💘"]

    embed = discord.Embed(title="Reaction Manager", description="Add a reaction to get started!\nUse /react message help for more info!", color=0xfc8403)

    def __init__(self, client, react_cache):
        self.client = client
        self.react_cache = react_cache

    async def create_react_message(self, channel, title=None, description=None):
        title = ReactChan.embed.title if not title else title
        description = ReactChan.embed.description if not description else description
        new_embed = discord.Embed(title=title, description=description, color=ReactChan.embed.color)
        gid = str(channel.guild.id)
        cid = str(channel.id)
        if gid not in self.react_cache["guilds"]:
            self.react_cache["guilds"][gid] = {"channels": {}}
        if cid not in self.react_cache["guilds"][gid]["channels"]:
            self.react_cache["guilds"][gid]["channels"][cid] = copy.deepcopy(ReactChan.DEFAULT_JSON)
        channel_object = self.react_cache["guilds"][gid]["channels"][cid]
        if channel_object.get("message"):
            return "This channel already has a react message, use /react message delete to remove it!"
        message = await channel.send(embed=new_embed)
        self.react_cache["messages"].append(message.id)
        self.react_cache["guilds"][gid]["channels"][cid]["message"] = message.id
        self.react_cache.save()
        return "Created react message!"


    async def add_auto_role(self, channel, role, emoji=None):
        guild = channel.guild
        self.react_cache.get("guilds", {})
        channel_object = self.get_channel_object(guild, channel)
        if not channel_object:
            return "There must be a react-message present in this channel to use this command. Create one through /react message create"
        message : discord.Message = await channel.fetch_message(channel_object["message"])

        if not emoji:
            re = 0
            emoji = random.choice(ReactChan.EMOJI_LIST)
            while re < 10 and emoji in channel_object["auto_roles"].values():
                emoji = random.choice(ReactChan.EMOJI_LIST)
                re += 1
            if re == 10: return

        await message.add_reaction(emoji)

        channel_object["auto_roles"][emoji] = role.id
        channel_object["reaction_type"][emoji] = "auto_roles"
        self.react_cache.save()
        roles = [f"{emoji} = **{guild.get_role(role).name}**" for emoji, role in channel_object["auto_roles"].items()]

        embed = message.embeds[0]
        new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
        new_embed.add_field(name="Roles:", value="\n".join(roles))
        await message.edit(embed=new_embed)
        return "Successfully added new reaction"

    async def delete_react_message(self, channel):
        guild = channel.guild
        channel_object = self.get_channel_object(guild, channel)
        if not channel_object: return "Reaction message not found."
        message_id = channel_object["message"]
        message = await channel.fetch_message(message_id)
        self.react_cache["guilds"][str(channel.guild.id)]["channels"].pop(str(channel.id))
        self.react_cache["messages"].pop(self.react_cache["messages"].index(message_id))
        self.react_cache.save()
        await message.delete()
        return "Successfully deleted reaction message."

    def is_react_message(self, message):
        return message.id in self.react_cache["messages"]

    def get_channel_object_from_message(self, message):
        return self.get_channel_object(message.guild, message.channel)

    def get_channel_object(self, guild, channel):
        gid = guild.id
        guild_object = self.react_cache["guilds"].get(str(gid))
        if not guild_object: return None
        if not (guild_object.get("channels")): return None
        channel_object = guild_object["channels"].get(str(channel.id))
        return channel_object

    async def process_raw_reaction(self, member : discord.Member, message, emoji):
        emoji = str(emoji)
        channel_object = self.get_channel_object_from_message(message)
        if not channel_object:
            return None
        reaction_type = channel_object["reaction_type"].get(emoji)
        if not reaction_type: return None
        if reaction_type == "auto_roles":
            role_id = channel_object["auto_roles"].get(emoji)
            if not role_id: return
            role = message.guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
            else:
                await member.add_roles(role)

    async def remove_reaction(self, channel, emoji):
        guild = channel.guild
        channel_object = self.get_channel_object(guild, channel)
        if not channel_object: return "Reaction message not found."
        reaction_type = channel_object["reaction_type"].get(emoji)
        if not reaction_type: return "Reaction not found."
        channel_object["reaction_type"].pop(emoji)
        channel_object[reaction_type].pop(emoji)
        self.react_cache.save()
        message = channel_object["message"]
        message = await channel.fetch_message(message)
        await message.clear_reaction(emoji)
        await self.update_embed(message, channel_object)
        return "Successfully removed reacton"

    async def update_embed(self, message, channel_object):
        embed = message.embeds[0]
        roles = [f"{emoji} = **{message.guild.get_role(role).name}**" for emoji, role in channel_object["auto_roles"].items()]
        new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
        if roles:
            new_embed.add_field(name="Roles:", value="\n".join(roles))
        await message.edit(embed=new_embed)

