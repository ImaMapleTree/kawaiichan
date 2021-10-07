import discord
from discord.ext.commands.bot import Bot

class ReactChan(): #Probably a 1 instance class created in the backend
    DEFAULT_JSON = {"auto_roles": {}}

    def __init__(self, client, react_cache):
        self.client = client
        self.react_cache = react_cache

    async def add_react_message(self, message):
        self.react_cache["messages"].append(message)
        if message.guild.id not in self.react_cache:
            self.react_cache["guilds"][str(message.guild.id)] = ReactChan.DEFAULT_JSON


    async
