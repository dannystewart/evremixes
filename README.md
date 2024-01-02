# Evanescence Remix Downloader

Just run this one simple command to download all my latest Evanescence remixes:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This runs [`evdownloader.sh`](evdownloader.sh) in case you want to check it before you run random code off the internet.

### Windows User?

My condolences. But fret not; I wrote [`evdownloader.ps1`](evdownloader.ps1) *just for you*:

```ps1
iex (iwr -useb https://dnst.me/evps).Content
```

You're probably only here to get the remixes, but if you're interested in how these work, by all means read on!

## How do these work?

The full version of this script is written in Python. The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. [`evtracks.json`](evtracks.json) holds the current list of remixes I have available, their URLs, and any necessary metadata, including album art. It even accounts for two different ways to do track numbers, which it will ask you to choose when it runs:

- The "intended" track numbers, according to my playlist order
- Their start dates, so they can be sorted chronologically in the order I did them

You can download them in FLAC or ALAC (Apple Lossless) format, and the script will ask you where you want to save them (default options are your Downloads and Music folders, but you can also input a custom path). After the files are saved, it will apply the metadata, download and apply the cover art from the URL specified in the JSON, and automatically rename them to match your selected track numbering scheme.

The Python version is a precompiled binary for maximum compatibility (avoiding the need for dependencies as much as possible), but if for some reason you can't run the Python version, there is also a basic Bash version available as a fallback. The Bash version is what runs first and tests to see if you're able to run the Python version. If so, it launches that, but if not, it just runs by itself.

## FAQ (Foreseeably Askable Questions)

### I don't trust downloading and executing random arbitrary code from the internet!

That's not a question, but good! This was a test and you passed. That's why all the code is published here for you to check before you run it. You could also just [listen to my remixes online](https://music.dannystewart.com/evanescence/) if you prefer. Up to you, you do you! But because I do the whole security thing, here's what those commands download and run:

1. The main `evdl` URL goes to [`evdownloader.sh`](evdownloader.sh) and the `evps` URL (for Windows) goes to [`evdownloader.ps1`](evdownloader.ps1).
2. If you meet the requirements, those scripts will then download and run a binary of the Python version.

Binaries are scary, I know—they could be anything! But they're all compiled from [`evremixes.py`](evremixes.py). You can even see the compilation scripts I use (`pycompiler`). If you're ultra paranoid, I encourage you to just run the original Python script—but you'll need Python and all the dependencies, and for that you're on your own.

### Why is it prompting me to install the macOS Developer Tools?

The need to parse JSON left me with two choices: `jq`, which would require Homebrew, or Python, which Apple provides a version of directly. A lot of Macs already have it, and those that don't can install it safely and easily using a feature that's built into the OS and doesn't even require admin rights. The latter seemed like an easier sell. The Developer Tools contain useful stuff that won't negatively affect your system and I'm honestly shocked when I encounter a Mac that's been around for a while and doesn't have them. Lots of things need them. It's why Apple made them so easy to install.

### How do I replace albums/songs in the Music app?

1. Open Music and wait for **Updating Cloud Music Library** in the bottom left to finish and disappear.
2. Right-click the albums/songs and click **Delete from Library**.
3. Go to **File > Library > Update Cloud Library** and wait for it to finish.
4. Go to **File > Import…** and select the file(s) or entire album folder and click **Open**.
5. Wait for it to import, then verify that everything looks correct.
6. One last time, go to **File > Library > Update Cloud Library** and wait for it to finish.

It's important to wait for each step in the process to finish. If you re-import before it's flushed out, you can end up with duplicates or have your new copies overwritten by old ones. It never hurts to sync twice, and it can be helpful to have another device nearby to watch and make sure you see the changes.
