import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

PLAYLIST_URL = os.environ['SPOTIFY_PLAYLIST_LINK']
def add_to_playlist(song_url: str):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public", open_browser=False))

    track_urls = get_playlist_track_urls(sp)

    if song_url not in track_urls:
        sp.playlist_add_items(PLAYLIST_URL, [song_url])

def get_playlist_track_urls(sp) -> list[str]:
    results = sp.playlist_tracks(PLAYLIST_URL)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    track_urls = [item['track']['external_urls']['spotify'] for item in tracks]
    return track_urls
