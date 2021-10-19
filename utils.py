import epyconfig as ecfg
import discord
from discord_slash.utils.manage_commands import create_option, create_choice
import datetime
import dateutil.relativedelta
from datetime import date
import time
import os
from os import path
import codecs
import json


default_embed = discord.Embed(title="No song currently playing", description="But I still love you **nuzzle~**", colour=0xfc8403)
default_embed.set_image(url="https://cdn.discordapp.com/attachments/369000441117147137/887225852780224552/kawiisong.png")
default_embed.set_footer(text="Looping: False | Shuffling: False", icon_url="https://static.wikia.nocookie.net/maid-dragon/images/5/57/Kanna_Anime.png")

def create_default_embed(description="To add a song to queue, type a title in the chat.", url="https://cdn.discordapp.com/attachments/369000441117147137/887225852780224552/kawiisong.png", color=0xfc8403):
    embed = discord.Embed(title="No song currently playing", description=description, colour=color)
    embed.set_image(url=url)
    embed.set_footer(text="Looping: False | Shuffling: False", icon_url="https://static.wikia.nocookie.net/maid-dragon/images/5/57/Kanna_Anime.png")
    return embed

async def validate_reactions(message, emoji):
    expected_reactions = ['⏯️', '⏹️', '⏮️', '⏭️', '🔁', '🔀', '⭐', '❌']
    actual_reactions = [reaction.emoji for reaction in message.reactions]
    i = 0
    reactions = actual_reactions if len(actual_reactions) > len(expected_reactions) else expected_reactions
    while i < len(reactions):
        if i >= len(expected_reactions):
            [await message.reactions[i].remove(user) async for user in message.reactions[i].users()]
        elif i >= len(actual_reactions):
            await message.add_reaction(expected_reactions[i])
        else:
            if actual_reactions[i] != expected_reactions[i]:
                [await message.reactions[i].remove(user) async for user in message.reactions[i].users()]
                actual_reactions[i] = expected_reactions[i]
                await message.add_reaction(expected_reactions[i])
        i += 1
    if emoji.name in expected_reactions:
        return [reaction for reaction in message.reactions if reaction.emoji == emoji.name][0]
    return None

def validate_reaction(message, emoji):
    try_reactions = [reaction for reaction in message.reactions if reaction.emoji == emoji.name]
    if try_reactions == []:
        try_reactions = [reaction for reaction in message.reactions if reaction.emoji == emoji]
    valid_reaction = try_reactions[0] if len(try_reactions) >= 1 else None
    return valid_reaction

async def get_members_in_call(client, guild):
    if not guild.voice_client: return []
    if len(guild.voice_client.channel.members) >= len(guild.voice_client.channel.voice_states):
        return guild.voice_client.channel.members
    return [await guild.fetch_member(member_id) for member_id in guild.voice_client.channel.voice_states.keys()]

def parse_date_string(string_date):
    days = 1
    split_date = string_date.replace(" - ", "/").replace("-", "/").split("/")
    if len(split_date) == 4:
        split_date.insert(2, "2021")
    if len(split_date) == 2 or len(split_date) == 5:
        split_date.append("2021")
    if len(split_date) > 3:
        d1 = date(int(split_date[2]), int(split_date[0]), int(split_date[1]))
        d2 = date(int(split_date[5]), int(split_date[3]), int(split_date[4]))
        delta = d2 - d1
        days = delta.days + 1
    pass_date = date(int(split_date[2]), int(split_date[0]), int(split_date[1]))
    return pass_date, days


def shorten_source(source):
    i = source.rfind("\\")
    if i == -1: return source
    d = source.rfind(".")
    return source[i + 1:d]


def JOpen(location, mode, savee=None, forced=False):
    if mode == 'r' or mode == 'r+':
        if not path.exists(location) and not forced: return (None)  # Checks if path exists, if not returns false.
        elif not path.exists(location):
            return ForceDict(path=location)
        TOP = codecs.open(location, "r", "utf-8")
        quick_json = json.load(TOP)
        TOP.close()
        if forced:
            return ForceDict(quick_json, path=location)
        return SaveDict(quick_json, path=location)
    elif mode == 'w' or mode == 'w+':
        with open(location, mode) as TOP:
            json.dump(savee, TOP, indent=3)
            TOP.close()
        return()

class ForceDict(dict):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path") if "path" in kwargs else None
        super(ForceDict, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            self[key] = None
        return None

    def get(self, key, default=None):
        try: return super().__getitem__(key)
        except KeyError:
            self[key] = default
        return default

    def save(self):
        if self.path:
            JOpen(self.path, "w+", self)

class SaveDict(dict):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path") if "path" in kwargs else None
        super(SaveDict, self).__init__(*args, **kwargs)

    def save(self):
        if self.path:
            JOpen(self.path, "w+", self)


class UUID:
    def __init__(self):
        self.time = time.time()
        self.divisor = self.time / 1000000000
        self.uuid = int(id(self.time) / self.divisor)

    def __str__(self):
        return str(self.uuid)

    def __repr__(self):
        return f"<UUID(self.uuid)>"


def greater_find(string, term):
    s = string.find(term)
    return s + len(term)


def find(string, term):
    found = True if string.find(term) != -1 else False
    return found


def timestamp_readable(epoch):
    return time.strftime("%Mm %Ss", time.gmtime(epoch))


def timestamp_readable2(epoch):
    return time.strftime("%M:%S", time.gmtime(epoch))


def date_readable(epoch):
    return datetime.datetime.fromtimestamp(epoch / 1000).strftime("%m/%d/%Y")


def current_epoch_difference(epoch):
    return epoch_difference(epoch, datetime.datetime.now().timestamp())


def epoch_difference(epoch1, epoch2):
    dt1 = datetime.datetime.fromtimestamp(epoch1)  # 1973-11-29 22:33:09
    dt2 = datetime.datetime.fromtimestamp(epoch2)
    rd = dateutil.relativedelta.relativedelta(dt2, dt1)
    if rd.years > 1:
        difference = "1+ Years"
    elif rd.years == 1:
        difference = "1 Year"
    elif rd.months > 2:
        difference = f'{rd.months} Months {rd.days} Days'
    elif rd.months == 1:
        difference = f'{rd.months} Month {rd.days} Days'
    elif rd.days == 1:
        difference = f'{rd.days} Day {rd.hours} Hours'
    elif rd.days > 1:
        difference = f'{rd.days} Days {rd.hours} Hours'
    elif rd.hours != 1:
        difference = f'{rd.hours} Hours'
    else:
        difference = f'{rd.hours} Hour'
    return difference


def get_emoji_list(client):
    global emojis
    emojis = {}

    def fast_add(emojis, l):
        def collapse(emojis, emoji):
            emojis[emoji.name.lower()] = emoji

        [collapse(emojis, emoji) for emoji in l]

    [fast_add(emojis, guild.emojis) for guild in client.guilds if
     guild.name.startswith("RiotServer") and guild.owner_id in CONFIG["owner_ids"]]
    return emojis


def get_emoji(input, emoji_dict=None):
    if not emoji_dict:
        try:
            emoji_dict = emojis
        except NameError:
            return None
    name = str(input)
    name = name.lower().replace(" ", "").replace("'", "").replace(".", "")
    emoji = emoji_dict.get(name)
    if emoji != None: return emoji
    matches = [emoji_name for emoji_name in emoji_dict.keys() if emoji_name.startswith(name)]
    if matches: return emoji_dict[matches[0]]
    return input


def command_generator(name):
    details = COMMAND_DETAILS[name].copy()
    options = details.get("options")
    if options:
        for option in options:
            if "choices" in option:
                option["choices"] = [create_choice(**choice) for choice in option["choices"]]
        details["options"] = [create_option(**option) for option in options]
    return details


def cmd_gen(name):
    return command_generator(name)


cmd_path = path.join(os.getcwd(), "commands")
COMMAND_DETAILS = ecfg.load_all(path.join(os.getcwd(), "commands"))
CONFIG = ecfg.load()
