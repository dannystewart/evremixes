# Evanescence Remix Downloader

Simply run the following to download all my latest Evanescence remixes:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This runs [`evdownloader.sh`](evdownloader.sh) in case you want to check it before you run random code off the internet.

### Windows User?

I'm sorry. But fret not—I wrote [`evdownloader.ps1`](evdownloader.ps1) just for you. Run this and feel like an adult with a Unix-based OS for one brief but shining moment:

```ps1
iex (iwr -useb https://dnst.me/evps).Content
```

All you probably care about is downloading the remixes, but if you're interested in understanding how these work, by all means read on.

## More Info

The full version of this script is written in Python and it's very cool (if I do say so myself). The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. But how does it know what's currently available?

Glad you asked! That's where [`evtracks.json`](evtracks.json) comes in. It holds the current list of all the remixes I have available, their URLs, and any necessary metadata, including the URL to the album art. It even accounts for two different ways to do track numbers, which it will ask you to choose when it runs:

- The "intended" track numbers, according to my playlist order
- Their start dates, so they can be sorted chronologically in the order I did them

The ones hosted on my site are in FLAC for compatibility reasons[^alac], but if you're running this script on a Mac, it assumes you want them in Apple Lossless (ALAC) so you can more easily play them or import them into Apple Music, and it will convert them accordingly. If you're some kind of savage who is using Windows or Linux, it will skip the conversion by default and leave them in FLAC.[^flac]

After the files are saved in the intended format, it will go through and apply the metadata. It will also download the cover art from the URL specified in the JSON and apply that too. This is very cool because it doesn't matter what's on the files themselves, it only matters what's in the JSON, and the files don't need to be updated server-side to account for changing metadata or track numbering.

The script will download the remixes to `~/Downloads` on macOS (so you can move them to wherever you want, or simply import and then delete), and to `~/Music` on Windows and Linux.

As the files are downloaded and the metadata is applied, they will also be renamed automatically to match your selected track numbering scheme. When finished, they'll be ready for listening and/or import.

[^alac]: Most browsers will only download ALAC files, not play them. Even Apple doesn't support playback in Safari. It's bizarre.

[^flac]: While not supported via URL, you can also run the script with `--flac` if you're running it locally.

### Basic Version

The main script relies on precompiled binaries[^binaries] as this avoids the need for Python and most dependencies (except `ffmpeg` to convert from FLAC to ALAC). If you don't have `ffmpeg`, it will fall back to a more basic script that downloads pre-converted ALAC files from my site. This is not as cool and relies on me remembering to manually convert and upload new mixes, so I can't guarantee they're always current.

The Python script will skip conversion to ALAC if `ffmpeg` is not found, but it will still tag and rename the FLAC files. **However for Mac users it is assumed that ALAC is always preferable to FLAC, so it will not attempt to run the Python script and will fall back to the basic ALAC downloader.**

[^binaries]: These are in the `dist` folder and are architecture-dependent: `arm` for Apple Silicon Macs, `x86` for Intel Macs, `win` for Windows, and `linux` for Linux. If you're having trouble running them, make sure they're executable with `chmod +x ./evremixes`

## FAQ

### I want to run the cool Python version! What do I need for that?

Just install [Homebrew](https://brew.sh) and then `brew install ffmpeg`. That's it!

### What's all the other stuff in here?

The `tools` folder contains stuff that's only useful for me:

- [`evazure.py`](tools/evazure.py): Uploads files to Azure blob storage where I keep my remixes.
- [`evconverter.py`](tools/evconverter.py): Converts FLAC versions to ALAC and uploads them for the basic downloader.
- [`evtelegram.py`](tools/evtelegram.py): Posts remixes to a Telegram channel. It tracks upload IDs in [`upload_cache.json`](tools/upload_cache.json) and tries to delete them when replacing a song, but unfortunately due to Telegram limitations it can't delete things older than 48 hours, so most will need to be deleted manually. (I thought I was so cool.)
- [`pycompiler.sh`](tools/pycompiler.sh) / [`pycompiler.bat`](tools/pycompiler.bat): One-liners to make it easier to compile the binaries.

Feel free to look, but there's no reason for you to touch, and most of it won't work without environment variables that aren't included here (for obvious reasons).

### How do I replace albums/songs in the Music app?

1. Open Music and wait for **Updating Cloud Music Library** in the bottom left to finish and disappear.
2. Right-click the albums/songs and click **Delete from Library**.
3. Go to **File > Library > Update Cloud Library** and wait for it to finish.
4. Go to **File > Import…** and select the file(s) or entire album folder and click **Open**.
5. Wait for it to import, then verify that everything looks correct.
6. One last time, go to **File > Library > Update Cloud Library** and wait for it to finish.

It's important to wait for each step in the process to finish. If you re-import before it's flushed out, you can end up with duplicates or have your new copies overwritten by old ones. It never hurts to sync twice, and it can be helpful to have another device nearby to watch and make sure you see the changes.
