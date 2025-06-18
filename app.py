import os
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC
import yt_dlp

SPOTIPY_CLIENT_ID = 'YOUR_CLIENT_ID'
SPOTIPY_CLIENT_SECRET = 'YOUR_CLIENT_SECRET'

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify Downloader")
        self.geometry("700x550")
        ctk.set_appearance_mode("dark")

        try:
            auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            print(f"Spotify authentication error: {e}")
            self.sp = None

        self.create_widgets()

    def create_widgets(self):
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.pack(pady=20, padx=20, fill="x")

        self.url_label = ctk.CTkLabel(self.url_frame, text="Spotify Playlist URL:")
        self.url_label.pack(side="left", padx=(10, 5))

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="https://open.spotify.com/playlist/...")
        self.url_entry.pack(side="left", expand=True, fill="x", padx=5)

        self.download_button = ctk.CTkButton(self.url_frame, text="Download", command=self.start_download_thread)
        self.download_button.pack(side="left", padx=(5, 10))

        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.pack(pady=10, padx=20, fill="x")
        
        self.quality_label = ctk.CTkLabel(self.settings_frame, text="Quality (kbps):")
        self.quality_label.pack(side="left", padx=(10, 5))
        self.quality_menu = ctk.CTkOptionMenu(self.settings_frame, values=["128", "192", "256", "320"])
        self.quality_menu.set("320")
        self.quality_menu.pack(side="left", padx=5)

        self.theme_label = ctk.CTkLabel(self.settings_frame, text="Theme:")
        self.theme_label.pack(side="left", padx=(20, 5))
        self.theme_switch = ctk.CTkSwitch(self.settings_frame, text="Light Mode", command=self.toggle_theme)
        self.theme_switch.pack(side="left", padx=5)

        self.status_textbox = ctk.CTkTextbox(self, state="disabled")
        self.status_textbox.pack(pady=10, padx=20, expand=True, fill="both")

    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")
            
    def log_status(self, message):
        self.status_textbox.configure(state="normal")
        self.status_textbox.insert("end", message + "\n")
        self.status_textbox.configure(state="disabled")
        self.status_textbox.see("end")

    def start_download_thread(self):
        self.download_button.configure(state="disabled", text="Downloading...")
        download_thread = threading.Thread(target=self.download_playlist)
        download_thread.start()

    def download_playlist(self):
        playlist_url = self.url_entry.get()
        if not playlist_url:
            self.log_status("Error: Please paste a playlist URL.")
            self.download_button.configure(state="normal", text="Download")
            return

        if not self.sp:
            self.log_status("Error: Could not connect to Spotify API. Check your Client ID/Secret.")
            self.download_button.configure(state="normal", text="Download")
            return

        try:
            self.log_status("Fetching playlist information...")
            results = self.sp.playlist_tracks(playlist_url)
            tracks = results['items']

            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
            
            self.log_status(f"Found {len(tracks)} tracks.")

            for i, item in enumerate(tracks):
                track = item['track']
                if not track:
                    self.log_status(f"Skipping unavailable track ({i+1}/{len(tracks)})")
                    continue

                track_name = track['name']
                artist_name = track['artists'][0]['name']
                album_name = track['album']['name']
                release_date = track['album']['release_date']
                image_url = track['album']['images'][0]['url']
                
                search_query = f"{artist_name} - {track_name} audio"
                self.log_status(f"({i+1}/{len(tracks)}) Searching for: {track_name}...")

                filename = os.path.join(DOWNLOAD_DIR, f"{artist_name} - {track_name}.mp3")
                
                if os.path.exists(filename):
                    self.log_status(f"-> Already downloaded: {track_name}")
                    continue

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': self.quality_menu.get(),
                    }],
                    'outtmpl': os.path.join(DOWNLOAD_DIR, f"{artist_name} - {track_name}"),
                    'quiet': True,
                }

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([f"ytsearch1:{search_query}"])
                    
                    self.log_status(f"-> Downloaded: {track_name}")

                    self.log_status(f"   -> Embedding metadata...")
                    self.embed_metadata(filename, track_name, artist_name, album_name, release_date, image_url)
                    self.log_status(f"   -> Done!")

                except Exception as e:
                    self.log_status(f"-> Failed to download {track_name}: {e}")

        except Exception as e:
            self.log_status(f"Error: Invalid playlist URL or API issue. {e}")
        
        self.log_status("\n--- DOWNLOAD COMPLETE ---")
        self.download_button.configure(state="normal", text="Download")

    def embed_metadata(self, file_path, title, artist, album, release_date, image_url):
        try:
            audio = MP3(file_path, ID3=ID3)
            image_data = requests.get(image_url).content

            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=image_data))
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TALB(encoding=3, text=album))
            audio.tags.add(TDRC(encoding=3, text=release_date.split('-')[0]))

            audio.save()
        except Exception as e:
            self.log_status(f"   -> Failed to embed metadata: {e}")


if __name__ == "__main__":
    try:
        from subprocess import run, DEVNULL
        run(['ffmpeg', '-version'], stdout=DEVNULL, stderr=DEVNULL)
    except FileNotFoundError:
        print("\n" + "="*70)
        print("WARNING: FFmpeg not found!")
        print("FFmpeg is required for converting to MP3 and embedding metadata.")
        print("Please download it from https://ffmpeg.org/download.html")
        print("and add its 'bin' folder to your system's PATH environment variable.")
        print("="*70 + "\n")

    app = App()
    app.mainloop()