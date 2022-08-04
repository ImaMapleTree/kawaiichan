import asyncio
import collections
import math

import discord
import yt_dlp as youtube_dl
#import youtube_dl
import time
import random

import utils
import spotify

youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': '(bestvideo+bestaudio/bestvideo)[protocol!*=http_dash_segments]/bestvideo+bestaudio/best',
    'nocheckcertificate': True,
    'restrictfilenames': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'cachedir': False,
    "username": "kawaiichanbot@gmail.com",
    "password": "shinxshinx6820",
}

beforeArgs = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

ffmpeg_options = {
    'options': '-vn'
}

global ytdl
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


async def validate_voice_client(ctx):
    author = ctx.message.author if not hasattr(ctx, "interaction_id") else ctx.author

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(author.voice.channel)

    return await author.voice.channel.connect()


class PseudoContext:
    def __init__(self, message):
        self.guild = message.guild
        self.voice_client = message.guild.voice_client
        self.channel = message.channel
        self.message = message

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

    async def validate(self):
        if not self.voice_client or self.voice_client.channel != self.message.author.voice.channel:
            self.voice_client = await validate_voice_client(self)
            return self.voice_client
        return self.voice_client

class RestartContext:
    def __init__(self, client: discord.Client, guild_id, text_channel_id, voice_channel_id):
        self.client = client
        self.guild : discord.Guild = client.get_guild(guild_id)
        self.channel : discord.TextChannel = self.guild.get_channel(text_channel_id)
        self.voice_channel : discord.VoiceChannel = self.guild.get_channel(voice_channel_id)
        self.voice_client = self.guild.voice_client

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

    async def validate(self):
        if not self.voice_client:
            if self.client.get_guild(self.channel.guild.id).voice_client:
                self.voice_client = self.client.get_guild(self.channel.guild.id).voice_client
            else:
                self.voice_client = await self.voice_channel.connect()
        return self.voice_client


class MusicList(list):
    def __init__(self, callback=None, *args, **kwargs):
        super(MusicList, self).__init__(*args, **kwargs)
        self.change_callback = callback

    def append(self, item):
        super().append(item)
        if self.change_callback: self.change_callback(item)

    def pop(self, index):
        item = super().pop(index)
        if self.change_callback: self.change_callback(item)
        return item


class MusicPlayer:
    def __init__(self, client, looped=False, shuffled=False, preferences={}):
        self._player_volume = 1
        self._source_volume = 0.5
        self.queue = collections.deque()
        self.history = collections.deque(maxlen=5)
        self.current_song = None
        self.client = client
        self.persistent_message = None
        self.paused = False
        self.looped = looped
        self.shuffled = shuffled
        self.current_embed = None
        self.last_song_timestamp = time.time()
        self.marks = 0

        self.update_preferences(preferences)

    @classmethod
    def from_dict(cls, mp_dict):
        mp = cls(mp_dict["client"], mp_dict["looping"], mp_dict["shuffling"], mp_dict["preferences"])
        mp.queue = collections.deque(mp_dict["queue"])
        mp.history = collections.deque(mp_dict["history"], maxlen=5)
        mp.persistent_message = mp_dict["p_message"]
        mp.paused = mp_dict["paused"]
        mp.current_embed = mp_dict["embed"]
        return mp

    @classmethod
    def from_restart(cls, client, guild_id, re_dict):
        mp = cls(client, re_dict["looping"], re_dict["shuffling"], re_dict["preferences"])
        qq = re_dict["queue"]
        mp.queue = collections.deque([[q[0], q[1], RestartContext(client, guild_id, q[2][0], q[2][1])] for q in qq])
        qq = re_dict["history"]
        mp.history = collections.deque([[q[0], q[1], RestartContext(client, guild_id, q[2][0], q[2][1])] for q in qq])
        mp.paused = re_dict["paused"]
        mp.current_embed = re_dict["embed"]

        return mp


    async def _ctx_wrapper(self, ctx, message):
        if not ctx and message:
            ctx = PseudoContext(message)
            await ctx.validate()
        else:
            await validate_voice_client(ctx)
        return ctx

    async def _play_song(self, song_container):
        def is_me(m):
            return m.author == self.client.user

        try:
            self.current_embed = self._set_status(song_container[1])
            await self.persistent_message.edit(embed=self.current_embed)
        except:
            pass
        if not song_container[2].voice_client: self._end_song(self.persistent_message, self._reconstruct(song_container))
        else: song_container[2].voice_client.play(song_container[0].prepare(), after=lambda x: self._end_song(self.persistent_message, self._reconstruct(song_container)))

    @staticmethod
    def _reconstruct(song_container):
        return [song_container[0].copy(), song_container[1], song_container[2]]

    def _end_song(self, msg, song_container):
        if time.time() - self.last_song_timestamp < 0.2:
            print("Caught out-of control loop!")
            self.looped = False #Catching system in-case the video errors while looping and starts to queue a billion times.
        self.current_song = None
        if self.looped:
            self.queue.append(song_container)
        self.history.appendleft(song_container)
        self.client.loop.create_task(self.check_song(message=msg))
        self.last_song_timestamp = time.time()

    def _set_status(self, embed):
        embed.set_footer(text=f"Looping: {self.looped} | Shuffling: {self.shuffled}", icon_url="https://static.wikia.nocookie.net/maid-dragon/images/5/57/Kanna_Anime.png")
        return embed

    async def play(self, ctx, query, message=None, initialize=True):
        ctx = await self._ctx_wrapper(ctx, message)
        async for message in self.get_music_room(ctx).history():
            if not message.content.startswith("**__Queue List__:**"):
                await message.delete()
            else:
                self.persistent_message = message

        player = await YTDLSource.from_query(query, loop=self.client.loop, stream=True, volume=self._source_volume, initialize=initialize)
        self.queue.append([player, self.get_context(player), ctx])
        await self.check_song(ctx)
        if player.others is not None:
            i = 0;
            chunk_size = math.ceil(len(player.others)/9)
            for subdata in player.others:
                imitation = ImitationSource(subdata, stream=True, volume=self._source_volume); i+= 1
                self.queue.append([imitation, self.get_context(imitation), ctx])
                if i % chunk_size == 0: await self.update_queue_info()
            await self.update_queue_info()

    async def play_spotify(self, ctx, query, message=None):
        spl = spotify.smart_parse(query)
        await self.play(ctx, spl.pop(0), message)

        for song in spl:
            await self.play(ctx, song, message, initialize=False)

    # TODO: When playing big playlists cache the data from player.others and have fake entries that get resolved on queue

    async def abandon(self):
        self.queue.clear()
        self.history.clear()
        if not self.persistent_message: return
        if not self.persistent_message.guild.voice_client: return
        await self.persistent_message.guild.voice_client.disconnect()


    async def check_song(self, message=None):
        if message and len(self.queue) == 0:
            no_embed = self._set_status(self.default_embed)
            await message.edit(embed=no_embed)
            self.current_embed = no_embed

        if not self.current_song:  # No song is playing
            if self.queue:
                index = 0 if not self.shuffled else random.randint(0, len(self.queue)-1)
                if not self.shuffled: self.current_song = self.queue.popleft()
                else: self.current_song = self.queue[index]; self.queue.remove(self.current_song)
                await self._play_song(self.current_song)

        await self.update_queue_info()

    def check_time(self):
        if not self.persistent_message: return self.last_song_timestamp
        if not self.persistent_message.guild.voice_client: return self.last_song_timestamp
        if self.persistent_message.guild.voice_client.is_playing(): return time.time()
        return self.last_song_timestamp

    async def is_alone(self):
        if not self.persistent_message: return False
        return len(await utils.get_members_in_call(self.client, self.persistent_message.guild)) <= 1

    async def loop(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.looped = True if not self.looped else False
        if self.current_embed:
            await self.persistent_message.edit(embed=self._set_status(self.current_embed))

    def memory_dict(self, exclude=[]):
        memory = {}
        if "client" not in exclude: memory["client"] = self.client
        if "looping" not in exclude: memory["looping"] = self.looped
        if "shuffling" not in exclude: memory["shuffling"] = self.shuffled
        if "queue" not in exclude: memory["queue"] = self.queue
        if "history" not in exclude: memory["history"] = self.history
        if "p_message" not in exclude: memory["p_message"] = self.persistent_message
        if "embed" not in exclude: memory["embed"] = self.current_embed
        if "paused" not in exclude: memory["paused"] = self.paused
        if "preferences" not in exclude: memory["preferences"] = self.preferences
        return memory

    def pickle_dict(self):
        memory = self.memory_dict(exclude=["client", "p_message"])
        memory["queue"] = [[ImitationSource(source[0].data), source[1], [source[2].channel.id, source[2].voice_client.channel.id]] for source in self.queue]
        memory["history"] = [
            [ImitationSource(source[0].data), source[1], [source[2].channel.id, source[2].voice_client.channel.id]] for
            source in self.history]
        return memory


    async def pause(self, ctx, message=None):
        self.paused = True if not self.paused else False
        ctx = await self._ctx_wrapper(ctx, message)
        if self.paused: ctx.voice_client.pause()
        else: ctx.voice_client.resume()

    async def previous(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.queue.insert(0, self.history.popleft())
        ctx.voice_client.stop()
        await asyncio.sleep(0.5)
        self.queue.insert(0, self.history.popleft())
        await self.update_queue_info()

    async def shuffle(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.shuffled = True if not self.shuffled else False
        if self.current_embed:
            await self.persistent_message.edit(embed=self._set_status(self.current_embed))

    async def skip(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        ctx.voice_client.stop()

    async def stop(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.queue.clear()
        ctx.voice_client.stop()

    async def source_volume(self, ctx, message=None, volume=0.5):
        self._source_volume = volume

    async def volume(self, ctx, message=None, volume=1):
        self._player_volume = volume
        ctx.voice_client.volume = volume

    @staticmethod
    async def get_persistent_message(guild):
        channels = [channel for channel in guild.channels if channel.name == "song-requests"]
        channel = channels[0] if channels else []

        async for message in channel.history():
            if not message.content.startswith("**__Queue List__:**"):
                await message.delete()
            else:
                persistent_message = message
        return persistent_message

    @staticmethod
    def get_music_room(ctx):
        guild = ctx.guild
        if not guild: return ctx.channel
        channels = [channel for channel in guild.channels if channel.name == "song-requests"]
        channel = channels[0] if channels else ctx.channel
        return channel

    def get_context(self, player):
        data = player.data
        url = data.get('webpage_url') if data.get('webpage_url') else "https://www.youtube.com/watch?v=gu--kSPMh9g"
        title = data.get('title') if data.get('title') else "No Title Available"
        thumbnail = data.get('thumbnail') if data.get(
            "thumbnail") else "https://cdn.discordapp.com/attachments/369000441117147137/887229873419087882/kawaiisong2.png"
        views = data.get('view_count') if data.get('view_count') else "N/A"
        duration = data.get('duration') if data.get('duration') else "00:00:00"

        duration = time.strftime('%H:%M:%S', time.gmtime(duration)) if duration != "00:00:00" else duration
        duration = str(duration).replace("00:", "", 1) if str(duration).find("00") >= 0 else str(duration)
        views = "{:,}".format(int(views)) if views != "N/A" else views
        embed = discord.Embed(title=title, description=f"**Duration:** {duration} | **Views:** {views}",
                              colour=self.queue_color, url=url)
        embed.set_image(url=thumbnail)
        return embed

    async def update_queue_info(self, _=None):
        content = "**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.\n"
        new_content = ""
        for i in range(len(self.queue)):
            entry = self.queue[i][0]

            duration = entry.data.get('duration', 0)
            duration = time.strftime('%H:%M:%S', time.gmtime(duration)) if duration != "00:00:00" else duration
            duration = str(duration).replace("00:", "", 1) if str(duration).find("00") >= 0 else str(duration)
            new_string = f"{i+1}. {entry.data.get('title', 'N/A')} [{duration}]\n"
            if len(new_string+new_content+content) > 2000: break
            new_content = new_string + new_content
            content.replace("\n", "", -1)
            i += 1
        content = content + new_content
        await self.persistent_message.edit(content=content)

    def update_preferences(self, preferences):
        self.preferences = preferences
        self.queue_description = preferences.get("queue_description", "But I still love you **nuzzle~**")
        self.queue_image = preferences.get("queue_image",
                                       "https://cdn.discordapp.com/attachments/369000441117147137/887225852780224552/kawiisong.png")
        self.queue_color = preferences.get("color", 0xfc8403)
        self.default_embed = utils.create_default_embed(description=self.queue_description,
                                                        url=self.queue_image, color=self.queue_color)



class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5, others=None, filename=None):
        self.initialized = False
        if source is not None:
            super().__init__(source, volume)
            self.initialized = True

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

        self.others = others
        self.filename = filename
        self.volume = volume

    @classmethod
    async def from_query(cls, url, *, loop=None, stream=True, volume=0.5, initialize=True):
        loop = loop or asyncio.get_event_loop()
        ytdl.cache.remove()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        other_data = None
        if 'entries' in data and len(data['entries'] > 0):
            # take first item from a playlist
            subdata = data['entries'].pop(0)
            other_data = data['entries']
        else:
            subdata = data
        filename = subdata['formats'][3]['url'] if stream else ytdl.prepare_filename(subdata)
        if not initialize:
            return cls(None, data=subdata, volume=volume, others=other_data, filename=filename)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=subdata,
                   volume=volume, others=other_data, filename=filename)


    @classmethod
    def from_subdata(cls, data, stream=True, volume=0.5):
        filename = data['formats'][3]['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data,
                   volume=volume, filename=filename)

    def copy(self):
        return YTDLSource(discord.FFmpegPCMAudio(self.filename, **ffmpeg_options), data=self.data, volume=self.volume, filename=self.filename)

    def prepare(self):
        if not self.initialized:
            return YTDLSource.from_subdata(data=self.data, stream=True, volume=self.volume)
        return self

    def cleanup(self, *args, **kwargs):
        try: super().cleanup()
        except AttributeError: pass

class ImitationSource():
    def __init__(self, data, stream=True, volume=0.5):
        self.data = data
        self.stream = stream
        self.volume = volume
        self.url = None

    def prepare(self):
        return YTDLSource.from_subdata(self.data, stream=self.stream, volume=self.volume)

    def copy(self):
        return ImitationSource(self.data, self.stream, self.volume)
