# Evanescence Remix Downloader

Simply run the following to download all my latest Evanescence remixes:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This runs [`evdownloader.sh`](evdownloader.sh) in case you want to check it before you run random code off the internet.

### Windows User?

I'm sorry. But don't feel left out—I wrote [`evdownloader.ps1`](evdownloader.ps1) just for you. Run this and you'll feel like an adult with a Unix-based OS, for one brief but shining moment:

```ps1
iex (iwr -useb https://dnst.me/evps).Content
```

All you probably care about is downloading the remixes, but if you're interested in understanding how these work, by all means read on.

## More Info

The full version of this script is written in Python and it's very cool (if I do say so myself). The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. But how does it know what's currently available?

Glad you asked! That's where [`evtracks.json`](evtracks.json) comes in. It holds the current list of all the remixes I have available, their URLs, and any necessary metadata, including the URL to the album art. It even accounts for two different ways to do track numbers, which it will ask you to choose when it runs:

- The "intended" track numbers, according to my playlist order
- Their start dates, so they can be sorted chronologically in the order I did them

The ones hosted on my site are in FLAC for compatibility reasons[^1], but if you're running this script on a Mac, it assumes you want them in Apple Lossless (ALAC) so you can more easily play them or import them into Apple Music, and it will convert them accordingly. If you're some kind of savage who is using Windows or Linux, it will skip the conversion by default and leave them in FLAC.[^2]

After the files are saved in the intended format, it will go through and apply the metadata. It will also download the cover art from the URL specified in the JSON and apply that too. This is very cool because it doesn't matter what's on the files themselves, it only matters what's in the JSON, and the files don't need to be updated server-side to account for changing metadata or track numbering.

The script will download the remixes to `~/Downloads` on macOS (so you can move them to wherever you want, or simply import and then delete), and to `~/Music` on Windows and Linux.

As the files are downloaded and the metadata is applied, they will also be renamed automatically to match your selected track numbering scheme. When finished, they'll be ready for listening and/or import.

[^1]: Most web browsers won't play ALAC-encoded M4A files; they will only download them. Even Apple doesn't support native playback in Safari. It's bizarre.

[^2]: While not supported by direct URL, you can also run the script with `--flac` to keep them in FLAC if you're running it locally on your machine.

### Basic Bash Version

Unfortunately the full Python version requires a few dependencies, most notably `ffmpeg` to handle the conversion from FLAC to ALAC. There is, however, a basic version of the script, written in Bash, that is nowhere near as cool, but it will download pre-converted ALAC files from my site. This relies on me remembering to manually re-encode and re-upload new files when mixes change, so I can't guarantee with 100% certainty that they will always be current.

The Python script will detect whether `ffmpeg` is installed or not, and if not, it will download the FLAC files, tag, and rename them without attempting to convert to ALAC; **however**, for Mac users, it is always assumed that ALAC is preferable to FLAC, so if `ffmpeg` is not detected on your system, it will not even attempt to run the Python script and will fall back to the basic downloader.

### Binaries for the Python Version

By default, the main script relies on precompiled binaries for the Python part, as this avoids the need for Python and most dependencies (with the unavoidable exception of `ffmpeg`). These are contained within the `dist` folder. They are unavoidably architecture-dependent, so you'll need to run the one in `arm` for Apple Silicon Macs, `x86` for Intel Macs, `win` for Windows, and `linux` for Linux (I know you wouldn't have figured those last two out on your own).

If you're having trouble running them, try `chmod +x ./evremixes` to make sure they're executable.

### Other Stuff

The `old` folder contains earlier versions for historical reference that you can (and should) ignore, and the `tools` folder contains stuff just for me. You can look but there's no reason for you to touch.

- [`evazure.py`](tools/evazure.py): This is an Evanescence-specific Python script to upload to Azure blob storage, where I keep my remixes.
- [`evconverter.py`](tools/evconverter.py): This is what I use to convert the FLAC files to ALAC, tag them, and re-upload them to Azure so they can be downloaded by the Bash script.
- [`evtelegram.py`](tools/evtelegram.py): This is a nifty script that uploads remixes to a Telegram channel. It tracks upload IDs in [`upload_cache.json`](tools/upload_cache.json) and tries to delete them when replacing a song, but unfortunately due to Telegram limitations it can't delete things older than 48 hours, so most will need to be deleted manually. (I thought I was so cool.)
- [`pycompiler.sh`](tools/pycompiler.sh) / [`pycompiler.bat`](tools/pycompiler.bat): These are just one-liners to make it easier to compile the binaries in four different places (for each OS and architecture).

## FAQ

### I want to run the cool Python version! What do I need for that?

Good for you for asking, because it's exactly how you should feel. You're missing out without it, and you don't need much so it's not that bad! All you need to do is install [Homebrew](https://brew.sh) (follow their instructions; trust me, it's better for everyone) and then use it to install `ffmpeg`:

```bash
brew install ffmpeg
```

### I want to be a super cool Python user like you! How can I get that set up?

It's a little beyond the scope of this readme, but you'll need to install Python and its dependencies. You can find guides like [this](https://www.pythoncentral.io/installing-python-on-mac-using-homebrew/) or [this](https://www.freecodecamp.org/news/python-version-on-mac-update/).

Once you have it all set up, clone this repository and install the necessary dependencies:
```bash
git clone https://git.dannystewart.com/danny/evremixes.git
cd evremixes
pip install -r requirements.txt
python evremixes.py
```

### What's the best way to update/replace albums/songs in Apple Music?

Having the metadata in place first makes things much easier, so I'll take this opportunity to plug [Meta](https://www.nightbirdsevolve.com/meta/), which is a great app for managing metadata that you don't need to worry about here because that's the entire point of this script. Once you have everything downloaded and tagged:

1. Open Apple Music and look in the bottom left corner for "**Updating Cloud Music Library**."
2. Wait for that to finish and disappear, then right-click the albums/songs and click **Delete from Library**.
3. Go to **File > Library > Update Cloud Library**.
4. Again look for "**Updating Cloud Music Library**" and wait for it to finish.[^3]
5. Go to **File > Import….**
6. Select the song file(s) or the entire folder containing the album and click **Open**.
7. Wait for it to import everything.
8. Verify that the album and metadata all look correct.
9. One last time, go to **File > Library > Update Cloud Library** and wait for it to finish.[^4]

[^3]: It's important for it to completely sync the removal of the album. If you re-import before it's fully flushed out, you can end up with duplicates or have your new copies overwritten by old versions.

[^4]: It never hurts to run a sync twice, and it helps to have another device nearby to watch and make sure the changes are syncing over.
