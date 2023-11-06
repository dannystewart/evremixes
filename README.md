# Evanescence Remix Downloader

Just run this one simple command to download all my latest Evanescence remixes:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This runs [`evdownloader.sh`](evdownloader.sh) in case you want to check it before you run random code off the internet.

### Windows User?

My condolences. But fret not; I wrote [`evdownloader.ps1`](evdownloader.ps1) *just for you*. Run this and feel like an adult with a Unix-based OS for one brief but shining moment:

```ps1
iex (iwr -useb https://dnst.me/evps).Content
```

You're probably only here to get the remixes, but if you're interested in how these work, by all means read on! I didn't write this for people to not read it!

## How do these work?

### Fancy Python Version

The full version of this script is written in Python and it's very cool (if I do say so myself). The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. But how does it know what's currently available?

Glad you asked! That's where [`evtracks.json`](evtracks.json) comes in. It holds the current list of all the remixes I have available, their URLs, and any necessary metadata, including the URL to the album art. It even accounts for two different ways to do track numbers, which it will ask you to choose when it runs:

- The "intended" track numbers, according to my playlist order
- Their start dates, so they can be sorted chronologically in the order I did them

The ones hosted on my site are in FLAC for compatibility reasons[^alac], but if you're running this script on a Mac, it assumes you want them in Apple Lossless (ALAC) so you can more easily play them or import them into Apple Music, and it will convert them accordingly. If you're some kind of savage who is using Windows or Linux, it will skip the conversion by default and leave them in FLAC.[^flac]

After the files are saved in the intended format, it will go through and apply the metadata. It will also download the cover art from the URL specified in the JSON and apply that too. This is very cool because it doesn't matter what's on the files themselves, it only matters what's in the JSON, and the files don't need to be updated server-side to account for changing metadata or track numbering.

The script will download the remixes to `~/Downloads` on macOS (so you can move them to wherever you want, or simply import and then delete), and to `~/Music` on Windows and Linux. As the files are downloaded and the metadata is applied, they will also be renamed automatically to match your selected track numbering scheme. When finished, they'll be ready for listening and/or import.

[^alac]: Safari will play them, but it's dependent on MIME type, which my script does take into account. An ALAC-encoded M4A file needs to have `content-disposition` set to `inline` for it to play correctly. Most other browsers will only download them either way.

[^flac]: While not supported via URL, you can also run the script with `--flac` if you're running it locally.

### Basic Bash Version

The main script relies on precompiled binaries as this avoids the need for Python and most dependencies (except `ffmpeg` to convert from FLAC to ALAC). If you don't have `ffmpeg`, it will fall back to a more basic script that downloads pre-converted ALAC files from my site. This is not as cool and relies on me remembering to manually convert and upload new mixes, so I can't guarantee they're always current.

The Python script will skip conversion to ALAC if `ffmpeg` is not found, but it will still tag and rename the FLAC files. **However, for Mac users, it is assumed that ALAC is preferred over FLAC, so it will not attempt to run the Python script at all and will always fall back to the basic ALAC downloader.**

## FAQ (Foreseeably Askable Questions)

### I want to run the cool Python version! What do I need for that?

Just install [Homebrew](https://brew.sh) and then `brew install ffmpeg`. That's it!

### I don't trust downloading and executing random arbitrary code from the internet!

That's not a question, but good! This was a test and you passed. That's why all the code is published here for you to check before you run it. You could also just [listen to my remixes online](https://music.dannystewart.com/evanescence/) if you prefer. Up to you, you do you! But because I do the whole security thing, here's what those commands download and run:

1. The main `evdl` URL goes to [`evdownloader.sh`](evdownloader.sh) and the `evps` URL (for Windows) goes to [`evdownloader.ps1`](evdownloader.ps1).
2. If you meet the requirements, those scripts will then download and run a binary of the Python version.

Binaries are scary, I know—they could be anything! But they're all compiled from [`evremixes.py`](evremixes.py). You can even see the compilation scripts I use under `tools`. If you're ultra paranoid, I encourage you to just run the original Python script—but you'll need Python and all the dependencies, and for that you're on your own.

### Why is it prompting me to install the macOS Developer Tools?

The need to parse JSON left me with two choices: `jq`, which would require Homebrew, or Python, which Apple provides a version of directly. A lot of Macs already have it, and those that don't can install it safely and easily using a feature that's built into the OS and doesn't even require admin rights. The latter seemed like an easier sell. The Developer Tools contain useful stuff that won't negatively affect your system and I'm honestly shocked when I encounter a Mac that's been around for a while and doesn't have them. Lots of things need them. It's why Apple made them so easy to install.[^deps]

### What's all the other stuff in here?

The `tools` folder contains stuff that's only useful for me:

- [`evazure`](tools/evazure.py): A recently-overhauled script that takes WAV or AIFF Logic bounces, converts them to FLAC and ALAC, adds metadata, and uploads them to Azure blob storage where I keep my remixes. This has largely negated the need for [`evconverter`](tools/evconverter.py), which just copied existing FLAC versions to ALAC.
- [`evtelegram`](tools/evtelegram.py): Converts, tags, and uploads remixes to a [Telegram channel](https://t.me/+ihiJnfkMIVYzN2Ex).
- [`pycompiler.sh`](tools/pycompiler.sh) / [`.bat`](tools/pycompiler.bat): One-liners to make it easier to compile the binaries.

Feel free to look, but there's no reason for you to touch, and most of it won't work without environment variables that aren't included here (for obvious reasons).

### How do I replace albums/songs in the Music app?

1. Open Music and wait for **Updating Cloud Music Library** in the bottom left to finish and disappear.
2. Right-click the albums/songs and click **Delete from Library**.
3. Go to **File > Library > Update Cloud Library** and wait for it to finish.
4. Go to **File > Import…** and select the file(s) or entire album folder and click **Open**.
5. Wait for it to import, then verify that everything looks correct.
6. One last time, go to **File > Library > Update Cloud Library** and wait for it to finish.

It's important to wait for each step in the process to finish. If you re-import before it's flushed out, you can end up with duplicates or have your new copies overwritten by old ones. It never hurts to sync twice, and it can be helpful to have another device nearby to watch and make sure you see the changes.

[^deps]: There may still be additional dependencies I didn't account for. I did a stupid amount of testing on these considering no one will ever use them, but at a certain point it's easier for me to tell you to download one thing than it is to try and incorporate it all into the script and take over your system. I did start down that road, but once I hit the need for `sudo`, I reconsidered my life choices. (Some of them.)
