# Spotify Downloader

An advanced desktop application for downloading tracks, albums, and playlists from Spotify. The application fetches track data from Spotify, finds the corresponding audio on YouTube, downloads it in the best available quality, and embeds all necessary metadata, including cover art, artist, album, release year, and track number.

Built with Python using the CustomTkinter library for the graphical user interface and `yt-dlp` for the download engine.

## Core Features

-   **Universal Downloader**: Handles Spotify links for individual tracks, albums, and playlists.
-   **Parallel Downloads**: High-speed downloading with up to 4 parallel workers to process large queues quickly.
-   **Full Download Control**: Pause, Resume, and Stop functionality for the active download queue.
-   **High-Quality Metadata**: Automatically embeds ID3 tags, including:
    -   High-resolution cover art
    -   Track title
    -   Artist
    -   Album name
    -   Release year
    -   Track and disc numbers for correct album ordering
-   **Modern UI**: A clean, tabbed user interface with selectable light and dark modes and a visual progress bar.
-   **Flexible Settings**: All settings are configurable via the UI, including API keys, download path, audio quality (kbps), and duplicate file handling (Skip/Overwrite).
-   **Results Reporting**: A dedicated "Results" tab provides a summary of successful and failed downloads with detailed error reasons.
-   **Built-in Library**: An integrated "Library" tab to browse, search, play, and locate your downloaded tracks directly within the application.

## Screenshots

![Downloader Tab](![image](https://github.com/user-attachments/assets/da5ea8cb-c0f9-4eef-8ae2-0d5840e064a7))
*The main downloader interface showing the progress bar and controls.*

![Library Tab](![image](https://github.com/user-attachments/assets/8e0a09c4-6632-4207-aa3b-6d67e914b866))
*The built-in library for managing downloaded files.*

![Settings Tab](![image](https://github.com/user-attachments/assets/a6b3e59f-7b83-45e1-b7ae-03429837421e))
*The flexible settings panel.*

## Requirements

Before you begin, ensure you have the following installed:

1.  **Python 3.8+**: Download from [python.org](https://www.python.org/).
2.  **FFmpeg**: **(Required)** A command-line tool for audio/video operations.
    -   Download FFmpeg from the [official website](https://ffmpeg.org/download.html).
    -   Unzip the archive and add the path to the `bin` folder to your system's `PATH` environment variable. The application will not be able to process and save audio files without it.

## Installation Guide

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/shehatesogk/Spotify-Downloader
    cd "Your Spotify-Downloader location"
    ```

2.  **(Recommended) Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    ```
    -   On Windows: `venv\Scripts\activate`
    -   On macOS/Linux: `source venv/bin/activate`

3.  **Install the required dependencies:**
    ```bash
    pip install customtkinter spotipy yt-dlp mutagen requests Pillow
    ```

4.  **Get your Spotify API Credentials:**
    -   Go to the [Spotify Developer Dashboard](http.googleusercontent.com/spotify.com/0) and log in.
    -   Click "Create app", give it a name and description.
    -   Once created, you will see your `Client ID` and can view the `Client Secret`.

5.  **Run the application:**
    ```bash
    python app.py
    ```

## Usage

1.  On the first launch, go to the **Settings** tab.
2.  Enter your `Client ID` and `Client Secret` into the respective fields.
3.  Choose your desired download directory using the "Browse..." button.
4.  Adjust any other settings and click **"Save All Settings"**.
5.  Navigate to the **Downloader** tab and paste a Spotify URL (track, album, or playlist).
6.  Click **"Download"**.
7.  Monitor the progress in the log and view the final summary in the **Results** tab.
8.  Browse your downloaded music in the **Library** tab.
