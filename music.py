import asyncio
import collections
import datetime
import discord
import youtube_dl
import time
import random

import utils

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'nocheckcertificate': True,
    'restrictfilenames': True,
    'ignoreerrors': True,
    'logtostderr': False,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "dump-user-agent": True,
    'quiet': False,
    'no_warnings': True,
    'forceipv4': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
    'no-cache-dir': True,
    'rm-cache-dir': True,
    'nocachedir': True,
    'rmcachedir': True
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
    def __init__(self, client):
        self._player_volume = 1
        self._source_volume = 0.5
        self.queue = []
        self.history = collections.deque(maxlen=5)
        self.current_song = None
        self.client = client
        self.persistent_message = None
        self.paused = False
        self.looped = False
        self.shuffled = False

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
            await self.persistent_message.edit(embed=song_container[1])
        except:
            pass
        song_container[2].voice_client.play(song_container[0], after=lambda x: self._end_song(self.persistent_message, self._reconstruct(song_container)))

    @staticmethod
    def _reconstruct(song_container):
        return [song_container[0].copy(), song_container[1], song_container[2]]

    def _end_song(self, msg, song_container):
        self.current_song = None
        if self.looped:
            self.queue.append(song_container)
        self.history.appendleft(song_container)
        self.client.loop.create_task(self.check_song(message=msg))

    async def play(self, ctx, query, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        async for message in self.get_music_room(ctx).history():
            if not message.content.startswith("**__Queue List__:**"):
                await message.delete()
            else:
                self.persistent_message = message

        player = await YTDLSource.from_query(query, loop=self.client.loop, stream=True, volume=self._source_volume)
        self.queue.append([player, self.get_context(player), ctx])
        await self.check_song(ctx)
        if player.others is not None:
            for subdata in player.others:
                await asyncio.sleep(0.1)
                player = await YTDLSource.from_subdata(subdata, stream=True, volume=self._source_volume)
                self.queue.append([player, self.get_context(player), ctx])
            self.update_queue_info()

    async def check_song(self, ctx=None, message=None):
        if message and len(self.queue) == 0: await message.edit(embed=utils.default_embed)

        if not self.current_song:  # No song is playing
            if self.queue:
                index = 0 if not self.shuffled else random.randint(0, len(self.queue)-1)
                self.current_song = self.queue.pop(index)
                await self._play_song(self.current_song)

        self.update_queue_info()

    async def loop(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.looped = True if not self.looped else False

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
        self.update_queue_info()

    async def shuffle(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.shuffled = True if not self.shuffled else False

    async def skip(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        ctx.voice_client.stop()

    async def stop(self, ctx, message=None):
        ctx = await self._ctx_wrapper(ctx, message)
        self.queue.clear()
        ctx.voice_client.stop()

    async def source_volume(self, ctx, message=None, volume=0.5):
        #ctx = await self._ctx_wrapper(ctx, message)
        self._source_volume = volume

    async def volume(self, ctx, message=None, volume=1):
        #ctx = await self._ctx_wrapper(ctx, message)
        self._player_volume = volume
        ctx.voice_client.volume = volume

    @staticmethod
    def get_music_room(ctx):
        guild = ctx.guild
        if not guild: return ctx.channel
        channels = [channel for channel in guild.channels if channel.name == "song-requests"]
        channel = channels[0] if channels else ctx.channel
        return channel

    @staticmethod
    def get_context(player, bias=None):
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
                              colour=0xfc8403, url=url)
        embed.set_image(url=thumbnail)
        return embed

    def update_queue_info(self, _=None):
        output_friendly_queue = list(self.queue)
        output_friendly_queue.reverse()

        content = "**__Queue List__:**\nJoin a voice channel and queue songs by name or url in here.\n"
        for i in range(len(output_friendly_queue)):
            entry = output_friendly_queue[i][0]

            duration = entry.data.get('duration', 0)
            duration = time.strftime('%H:%M:%S', time.gmtime(duration)) if duration != "00:00:00" else duration
            duration = str(duration).replace("00:", "", 1) if str(duration).find("00") >= 0 else str(duration)
            new_string = f"{len(output_friendly_queue)-i}. {entry.data.get('title', 'N/A')} [{duration}]\n"
            if len(new_string+content) > 2000: break
            content += new_string
            content.replace("\n", "", -1)
            i += 1

        self.client.loop.create_task(self.persistent_message.edit(content=content))


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5, others=None, filename=None):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

        self.others = others
        self.filename = filename

    @classmethod
    async def from_query(cls, url, *, loop=None, stream=True, volume=0.5):
        loop = loop or asyncio.get_event_loop()
        ytdl.cache.remove()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        other_data = None
        if 'entries' in data:
            # take first item from a playlist
            subdata = data['entries'].pop(0)
            other_data = data['entries']
        else:
            subdata = data
        filename = subdata['formats'][0]['url'] if stream else ytdl.prepare_filename(subdata)
        return cls(discord.FFmpegPCMAudio(filename, before_options=beforeArgs, **ffmpeg_options), data=subdata,
                   volume=volume, others=other_data, filename=filename)

    @classmethod
    async def from_subdata(cls, data, stream=True, volume=0.5):
        filename = data['formats'][0]['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, before_options=beforeArgs, **ffmpeg_options), data=data,
                   volume=volume, filename=filename)

    def copy(self):
        return YTDLSource(discord.FFmpegPCMAudio(self.filename, before_options=beforeArgs, **ffmpeg_options), data=self.data, volume=self.volume, filename=self.filename)
