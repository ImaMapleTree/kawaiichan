import math

import spotipy

OAUTH_TOKEN_URL = 'http://localhost/'

SOA = spotipy.SpotifyClientCredentials(client_id="006b0085921642b2b8c6da7f354f0bf1", client_secret="aeb3e255f4984dedb75c38668bfc3bff")
sp = spotipy.Spotify(auth_manager=SOA)

class Playlist():
    def __init__(self, data):
        self.data = data
        self.collaborative = data["collaborative"]
        self.description = data["description"]
        self.external_url = data["external_urls"]
        self.followers = data["followers"]
        self.href = data["href"]
        self.id = data["id"]
        self.images = data["images"]
        self.name = data["name"]
        self.owner = data["owner"]
        self.public = data["public"]
        self.tracks = data["tracks"]

        remaining = self.tracks.get("total")
        for i in range(math.ceil(remaining/100)):
            #print(sp.playlist_items(self.id, offset=100+(i*100), limit=100))
            self.tracks["items"] += sp.playlist_items(self.id, offset=100+(i*100), limit=100)["items"]

        self.songs = self.get_song_names()

    def get_song_names(self):
        names = []
        for item in self.tracks["items"]:
            item = item["track"]
            name = item["name"] + " " + item["artists"][0]["name"]
            names.append(name)
        return names

    def pop(self, index):
        return self.songs.pop(index)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n < len(self.songs):
            result = self.songs[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

def smart_parse(query):
    if query.find("playlist") != -1:
        return playlist_entries(query)

def playlist_entries(playlist):
    return Playlist(sp.playlist(playlist))

