import os
import threading
import json
import re
import glob
import subprocess
import sys
import tkinter.messagebox
import customtkinter as ctk
from customtkinter import filedialog
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TPOS
from concurrent.futures import ThreadPoolExecutor, as_completed

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.CONFIG_FILE = "config.json"
        self.download_path = ctk.StringVar(value="downloads")
        self.quality_var = ctk.StringVar(value="320")
        self.theme_var = ctk.StringVar(value="dark")
        self.client_id_var = ctk.StringVar()
        self.client_secret_var = ctk.StringVar()
        self.duplicate_handling_var = ctk.StringVar(value="skip")
        
        self.sp = None
        self.successful_downloads = []
        self.failed_downloads = []

        self.is_paused = threading.Event()
        self.is_stopped = threading.Event()
        self.download_thread = None

        self.load_settings()
        
        self.title("Spotify Downloader")
        self.iconbitmap("icon.ico")
        self.geometry("800x650")
        ctk.set_appearance_mode(self.theme_var.get())

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.refresh_library)

    def get_button_style(self):
        return {"corner_radius": 0, "border_width": 2, "border_color": "#E0E0E0"}

    def create_widgets(self):
        self.tab_view = ctk.CTkTabview(self, corner_radius=0)
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)
        self.downloader_tab = self.tab_view.add("Downloader")
        self.library_tab = self.tab_view.add("Library")
        self.results_tab = self.tab_view.add("Results")
        self.settings_tab = self.tab_view.add("Settings")
        
        self.create_downloader_tab()
        self.create_library_tab()
        self.create_results_tab()
        self.create_settings_tab()
    
    def create_downloader_tab(self):
        self.url_frame = ctk.CTkFrame(self.downloader_tab)
        self.url_frame.pack(pady=10, padx=10, fill="x")
        self.url_label = ctk.CTkLabel(self.url_frame, text="Spotify URL (Track, Album, Playlist):")
        self.url_label.pack(side="left", padx=(10, 5))
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="https://open.spotify.com/playlist/...")
        self.url_entry.pack(side="left", expand=True, fill="x", padx=5)

        self.main_actions_frame = ctk.CTkFrame(self.downloader_tab)
        self.main_actions_frame.pack(pady=10, padx=10, fill="x")
        self.download_button = ctk.CTkButton(self.main_actions_frame, text="Download", command=self.start_download_thread, **self.get_button_style())
        self.download_button.pack(side="left", expand=True, padx=5, pady=5)
        self.pause_button = ctk.CTkButton(self.main_actions_frame, text="Pause", command=self.toggle_pause, state="disabled", **self.get_button_style())
        self.pause_button.pack(side="left", expand=True, padx=5, pady=5)
        self.stop_button = ctk.CTkButton(self.main_actions_frame, text="Stop", command=self.stop_download, state="disabled", **self.get_button_style())
        self.stop_button.pack(side="left", expand=True, padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.downloader_tab)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5, padx=10, fill="x")

        self.status_textbox = ctk.CTkTextbox(self.downloader_tab, state="disabled")
        self.status_textbox.pack(pady=10, padx=10, expand=True, fill="both")

    def create_library_tab(self):
        self.library_controls_frame = ctk.CTkFrame(self.library_tab)
        self.library_controls_frame.pack(pady=10, padx=10, fill="x")
        self.search_library_entry = ctk.CTkEntry(self.library_controls_frame, placeholder_text="Search Library...")
        self.search_library_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.search_library_entry.bind("<KeyRelease>", self.filter_library)
        self.refresh_library_button = ctk.CTkButton(self.library_controls_frame, text="Refresh", command=self.refresh_library, **self.get_button_style())
        self.refresh_library_button.pack(side="left")
        self.library_scrollable_frame = ctk.CTkScrollableFrame(self.library_tab)
        self.library_scrollable_frame.pack(pady=10, padx=10, expand=True, fill="both")
        
    def create_results_tab(self):
        self.summary_frame = ctk.CTkFrame(self.results_tab)
        self.summary_frame.pack(pady=10, padx=10, fill="x")
        self.summary_total_label = ctk.CTkLabel(self.summary_frame, text="Total: 0")
        self.summary_total_label.pack(side="left", expand=True)
        self.summary_success_label = ctk.CTkLabel(self.summary_frame, text="Successful: 0")
        self.summary_success_label.pack(side="left", expand=True)
        self.summary_failed_label = ctk.CTkLabel(self.summary_frame, text="Failed: 0")
        self.summary_failed_label.pack(side="left", expand=True)
        self.failed_list_label = ctk.CTkLabel(self.results_tab, text="Failed Downloads:")
        self.failed_list_label.pack(pady=(10,0), padx=10, anchor="w")
        self.failed_scrollable_frame = ctk.CTkScrollableFrame(self.results_tab)
        self.failed_scrollable_frame.pack(pady=10, padx=10, expand=True, fill="both")

    def create_settings_tab(self):
        self.settings_scrollable_frame = ctk.CTkScrollableFrame(self.settings_tab)
        self.settings_scrollable_frame.pack(expand=True, fill="both", padx=5, pady=5)

        self.credentials_frame = ctk.CTkFrame(self.settings_scrollable_frame)
        self.credentials_frame.pack(pady=10, padx=10, fill="x")
        self.client_id_label = ctk.CTkLabel(self.credentials_frame, text="Spotify Client ID:")
        self.client_id_label.pack(padx=10, pady=(10, 2), anchor="w")
        self.client_id_entry = ctk.CTkEntry(self.credentials_frame, textvariable=self.client_id_var, width=300)
        self.client_id_entry.pack(padx=10, pady=2, fill="x", expand=True)
        self.client_secret_label = ctk.CTkLabel(self.credentials_frame, text="Spotify Client Secret:")
        self.client_secret_label.pack(padx=10, pady=(10, 2), anchor="w")
        self.client_secret_entry = ctk.CTkEntry(self.credentials_frame, textvariable=self.client_secret_var, show="*", width=300)
        self.client_secret_entry.pack(padx=10, pady=2, fill="x", expand=True)
        
        self.path_frame = ctk.CTkFrame(self.settings_scrollable_frame)
        self.path_frame.pack(pady=10, padx=10, fill="x")
        self.path_label = ctk.CTkLabel(self.path_frame, text="Save to:")
        self.path_label.pack(side="left", padx=(10, 5))
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.download_path, state="readonly")
        self.path_entry.pack(side="left", expand=True, fill="x", padx=5)
        self.browse_button = ctk.CTkButton(self.path_frame, text="Browse...", command=self.select_folder, **self.get_button_style())
        self.browse_button.pack(side="left", padx=(5, 10))

        self.duplicate_frame = ctk.CTkFrame(self.settings_scrollable_frame)
        self.duplicate_frame.pack(pady=10, padx=10, fill="x")
        self.duplicate_label = ctk.CTkLabel(self.duplicate_frame, text="If file already exists:")
        self.duplicate_label.pack(side="left", padx=(10, 5))
        self.skip_radio = ctk.CTkRadioButton(self.duplicate_frame, text="Skip", variable=self.duplicate_handling_var, value="skip")
        self.skip_radio.pack(side="left", padx=10)
        self.overwrite_radio = ctk.CTkRadioButton(self.duplicate_frame, text="Overwrite", variable=self.duplicate_handling_var, value="overwrite")
        self.overwrite_radio.pack(side="left", padx=10)

        self.appearance_frame = ctk.CTkFrame(self.settings_scrollable_frame)
        self.appearance_frame.pack(pady=10, padx=10, fill="x")
        self.quality_label = ctk.CTkLabel(self.appearance_frame, text="Quality (kbps):")
        self.quality_label.pack(side="left", padx=(10, 5), pady=10)
        self.quality_menu = ctk.CTkOptionMenu(self.appearance_frame, values=["128", "192", "256", "320"], variable=self.quality_var, corner_radius=0)
        self.quality_menu.pack(side="left", padx=5, pady=10)
        self.theme_label = ctk.CTkLabel(self.appearance_frame, text="Theme:")
        self.theme_label.pack(side="left", padx=(20, 5), pady=10)
        self.theme_switch = ctk.CTkSwitch(self.appearance_frame, text="Light Mode", command=self.toggle_theme)
        if self.theme_var.get() == "light":
            self.theme_switch.select()
        self.theme_switch.pack(side="left", padx=5, pady=10)
        
        self.save_settings_button = ctk.CTkButton(self.settings_scrollable_frame, text="Save All Settings", command=self.save_settings, **self.get_button_style())
        self.save_settings_button.pack(pady=20, padx=10)

    def sanitize_filename(self, filename):
        return "".join(c for c in filename if c not in r'\/:*?"<>|')

    def load_settings(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.download_path.set(config.get("download_path", "downloads"))
                self.quality_var.set(config.get("quality", "320"))
                self.theme_var.set(config.get("theme", "dark"))
                self.client_id_var.set(config.get("client_id", ""))
                self.client_secret_var.set(config.get("client_secret", ""))
                self.duplicate_handling_var.set(config.get("duplicate_handling", "skip"))
        except (FileNotFoundError, json.JSONDecodeError):
            if not os.path.exists("downloads"):
                os.makedirs("downloads")

    def save_settings(self):
        config = {
            "download_path": self.download_path.get(),
            "quality": self.quality_var.get(),
            "theme": self.theme_var.get(),
            "client_id": self.client_id_var.get(),
            "client_secret": self.client_secret_var.get(),
            "duplicate_handling": self.duplicate_handling_var.get()
        }
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        self.log_status("Settings saved.")
            
    def on_closing(self):
        if self.download_thread and self.download_thread.is_alive():
            if tkinter.messagebox.askyesno("Confirm Exit", "A download is in progress. Are you sure you want to exit?"):
                self.stop_download()
                self.download_thread.join()
                self.destroy()
        else:
            self.save_settings()
            self.destroy()
        
    def initialize_spotify(self):
        client_id, client_secret = self.client_id_var.get(), self.client_secret_var.get()
        if not client_id or not client_secret:
            tkinter.messagebox.showerror("Missing Credentials", "Spotify Client ID and Secret are not set. Please set them in the Settings tab.")
            self.tab_view.set("Settings")
            return False
        try:
            auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            self.sp.search(q='test', type='track', limit=1)
            return True
        except Exception as e:
            tkinter.messagebox.showerror("Spotify Error", f"Could not connect to Spotify. Check your credentials.\n\nError: {e}")
            self.tab_view.set("Settings")
            self.sp = None
            return False

    def select_folder(self):
        path = filedialog.askdirectory(initialdir=self.download_path.get())
        if path:
            self.download_path.set(path)

    def toggle_theme(self):
        mode = "light" if self.theme_switch.get() == 1 else "dark"
        ctk.set_appearance_mode(mode)
        self.theme_var.set(mode)
            
    def log_status(self, message):
        self.status_textbox.configure(state="normal")
        self.status_textbox.insert("end", str(message) + "\n")
        self.status_textbox.configure(state="disabled")
        self.status_textbox.see("end")

    def parse_spotify_url(self, url):
        match = re.search(r"spotify\.com/(playlist|album|track)/([a-zA-Z0-9]+)", url)
        if match:
            return match.groups()
        return None, None
        
    def start_download_thread(self):
        if self.download_thread and self.download_thread.is_alive():
            self.log_status("A download is already in progress.")
            return

        self.is_paused.clear()
        self.is_stopped.clear()
        
        self.download_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        
        self.download_thread = threading.Thread(target=self.run_download_job)
        self.download_thread.start()

    def toggle_pause(self):
        if self.is_paused.is_set():
            self.is_paused.clear()
            self.log_status("...Resuming download.")
            self.pause_button.configure(text="Pause")
        else:
            self.is_paused.set()
            self.log_status("Download paused.")
            self.pause_button.configure(text="Resume")
            
    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.log_status("Stopping download...")
            self.is_stopped.set()
            if self.is_paused.is_set():
                self.is_paused.clear()

    def run_download_job(self):
        if not self.initialize_spotify():
            self.reset_ui_state()
            return
        
        url = self.url_entry.get()
        if not url:
            self.log_status("Error: Please paste a Spotify URL.")
            self.reset_ui_state()
            return

        url_type, url_id = self.parse_spotify_url(url)
        if not url_type:
            tkinter.messagebox.showwarning("Invalid URL", "The provided URL does not appear to be a valid Spotify Track, Album, or Playlist link.")
            self.reset_ui_state()
            return

        self.successful_downloads.clear()
        self.failed_downloads.clear()
        os.makedirs(self.download_path.get(), exist_ok=True)
        
        try:
            self.log_status(f"Fetching {url_type} information...")
            tracks_to_process = []
            if url_type == 'playlist':
                results = self.sp.playlist_tracks(url_id)
                items = results['items']
                while results['next']:
                    results = self.sp.next(results)
                    items.extend(results['items'])
                tracks_to_process = [item['track'] for item in items if item and item.get('track')]
            elif url_type == 'album':
                album_tracks = self.sp.album_tracks(url_id)['items']
                album_details = self.sp.album(url_id)
                for track_stub in album_tracks:
                    full_track = self.sp.track(track_stub['id'])
                    full_track['album'] = album_details
                    tracks_to_process.append(full_track)
            elif url_type == 'track':
                track_data = self.sp.track(url_id)
                tracks_to_process.append(track_data)

            total_tracks = len(tracks_to_process)
            self.log_status(f"Found {total_tracks} track(s). Starting parallel download...")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(self.download_single_track, track) for track in tracks_to_process]
                
                for i, future in enumerate(as_completed(futures)):
                    if self.is_stopped.is_set():
                        break
                    try:
                        result = future.result()
                        if result['status'] == 'success':
                            self.successful_downloads.append(result['name'])
                        else:
                            self.failed_downloads.append(result['data'])
                    except Exception as exc:
                        self.log_status(f"A task generated an exception: {exc}")
                    
                    self.progress_bar.set((i + 1) / total_tracks)
        
        except Exception as e:
            self.log_status(f"An error occurred: {e}")

        self.update_results_tab(total_tracks)
        self.reset_ui_state()
        self.refresh_library()

    def download_single_track(self, track_info):
        import yt_dlp
        
        if self.is_stopped.is_set(): return {'status': 'stopped'}
        if self.is_paused.is_set(): self.is_paused.wait()
        if self.is_stopped.is_set(): return {'status': 'stopped'}

        original_track_name, original_artist_name = "N/A", "N/A"
        try:
            if not track_info:
                return {'status': 'failure', 'data': {'track': 'Unavailable', 'artist': '', 'reason': 'Track data is null.'}}

            original_track_name = track_info['name']
            original_artist_name = track_info['artists'][0]['name']
            sanitized_track_name = self.sanitize_filename(original_track_name)
            sanitized_artist_name = self.sanitize_filename(original_artist_name)
            
            final_filepath = os.path.join(self.download_path.get(), f"{sanitized_artist_name} - {sanitized_track_name}.mp3")
            
            if os.path.exists(final_filepath):
                handling_mode = self.duplicate_handling_var.get()
                if handling_mode == "skip":
                    self.log_status(f"-> Skipping duplicate: {original_track_name}")
                    return {'status': 'success', 'name': original_track_name}
                elif handling_mode == "overwrite":
                    self.log_status(f"-> Overwriting: {original_track_name}")

            search_query = f"{original_artist_name} - {original_track_name} audio"
            output_template = os.path.join(self.download_path.get(), f"{sanitized_artist_name} - {sanitized_track_name}")
            self.log_status(f"-> Searching: {original_track_name}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': self.quality_var.get()}],
                'outtmpl': output_template, 'quiet': True, 'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{search_query}"])
            
            self.embed_metadata(final_filepath, track_info)
            self.log_status(f"-> Downloaded & tagged: {original_track_name}")
            return {'status': 'success', 'name': original_track_name}

        except Exception as e:
            self.log_status(f"-> Failed: {original_track_name}")
            return {'status': 'failure', 'data': {'track': original_track_name, 'artist': original_artist_name, 'reason': e}}

    def embed_metadata(self, file_path, track_info):
        title, artist = track_info['name'], track_info['artists'][0]['name']
        album = track_info['album']['name']
        release_date = track_info['album']['release_date']
        track_num, disc_num = track_info.get('track_number'), track_info.get('disc_number')
        image_url = track_info['album']['images'][0]['url'] if track_info['album']['images'] else None

        audio = MP3(file_path, ID3=ID3)
        if image_url:
            try:
                image_data = requests.get(image_url).content
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=image_data))
            except Exception:
                pass

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=album))
        audio.tags.add(TDRC(encoding=3, text=release_date.split('-')[0]))
        if track_num:
            audio.tags.add(TRCK(encoding=3, text=str(track_num)))
        if disc_num:
            audio.tags.add(TPOS(encoding=3, text=str(disc_num)))
        audio.save()

    def reset_ui_state(self):
        self.download_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pause")
        self.stop_button.configure(state="disabled")

    def update_results_tab(self, total_tracks):
        for widget in self.failed_scrollable_frame.winfo_children():
            widget.destroy()
        success_count, failed_count = len(self.successful_downloads), len(self.failed_downloads)
        self.summary_total_label.configure(text=f"Total: {total_tracks}")
        self.summary_success_label.configure(text=f"Successful: {success_count}")
        self.summary_failed_label.configure(text=f"Failed: {failed_count}")
        for item in self.failed_downloads:
            reason = str(item['reason']).splitlines()[0]
            fail_text = f"{item['artist']} - {item['track']}\nReason: {reason}"
            ctk.CTkLabel(self.failed_scrollable_frame, text=fail_text, justify="left", anchor="w").pack(pady=2, padx=5, fill="x")
        self.tab_view.set("Results")
    
    def refresh_library(self):
        for widget in self.library_scrollable_frame.winfo_children():
            widget.destroy()
        download_dir = self.download_path.get()
        if not os.path.isdir(download_dir): return
        mp3_files = glob.glob(os.path.join(download_dir, "*.mp3"))
        for file_path in sorted(mp3_files, key=os.path.getmtime, reverse=True):
            filename = os.path.basename(file_path)
            item_frame = ctk.CTkFrame(self.library_scrollable_frame)
            item_frame.pack(fill="x", padx=5, pady=2)
            label = ctk.CTkLabel(item_frame, text=filename, anchor="w")
            label.pack(side="left", expand=True, fill="x", padx=5)
            show_button = ctk.CTkButton(item_frame, text="Folder", width=60, command=lambda p=file_path: self.show_in_folder(p), **self.get_button_style())
            show_button.pack(side="right", padx=2)
            play_button = ctk.CTkButton(item_frame, text="Play", width=50, command=lambda p=file_path: self.play_track(p), **self.get_button_style())
            play_button.pack(side="right", padx=2)
            
    def filter_library(self, event=None):
        query = self.search_library_entry.get().lower()
        for item_frame in self.library_scrollable_frame.winfo_children():
            label = item_frame.winfo_children()[0]
            if query in label.cget("text").lower():
                item_frame.pack(fill="x", padx=5, pady=2)
            else:
                item_frame.pack_forget()

    def play_track(self, file_path):
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            self.log_status(f"Could not play file: {e}")
            
    def show_in_folder(self, file_path):
        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        except Exception as e:
            self.log_status(f"Could not open folder: {e}")

if __name__ == "__main__":
    try:
        from subprocess import run, DEVNULL
        run(['ffmpeg', '-version'], stdout=DEVNULL, stderr=DEVNULL)
    except FileNotFoundError:
        print("\n" + "="*70)
        print("WARNING: FFmpeg not found!")
        print("Please download it from https://ffmpeg.org/download.html")
        print("and add its 'bin' folder to your system's PATH environment variable.")
        print("="*70 + "\n")
    app = App()
    app.mainloop()