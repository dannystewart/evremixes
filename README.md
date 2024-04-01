# Evanescence Remix Downloader

Just run this one simple command to download all my latest Evanescence remixes:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This runs [`evdownloader.sh`](evdownloader.sh) in case you want to check it before you run random code off the internet.

### Windows User?

My condolences. But fret not; I wrote [`evdownloader.ps1`](evdownloader.ps1) *just for you*:

```ps1
iex (iwr -useb https://dnst.me/evdl).Content
```

You're probably only here to get the remixes, but if you're interested in how these work, read on!

## How do these work?

The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. [`evtracks.json`](evtracks.json) holds the current list of available remixes, metadata, and URLs.

You're presented with the choice of FLAC or ALAC (Apple Lossless), as well as where you want the files to be saved. The default options are your Downloads and Music folders, but you can also enter a custom path. After downloading, it will apply the correct metadata, album art, and filenames.

## FAQ (Foreseeably Askable Questions)

### I don't trust downloading and executing random arbitrary code from the internet!

That's not a question, but good! This was a test and you passed. That's why all the code is published here for you to check before you run it. You could also just [listen to my remixes online](https://music.dannystewart.com/evanescence/) if you prefer. Up to you, you do you! But because I do the whole security thing, here's what those commands download and run:

1. The main `evdl` URL goes to [`evdownloader.sh`](evdownloader.sh) and the `evps` URL (for Windows) goes to [`evdownloader.ps1`](evdownloader.ps1).
2. If you meet the requirements, those scripts will then download and run a binary of the Python version.

Binaries are scary, I know—they could be anything! But they're all compiled from [`evremixes.py`](evremixes.py). You can even see the compilation scripts I use (`pycompiler`). If you're ultra paranoid, I encourage you to just run the original Python script—but you'll need Python and all the dependencies, and for that you're on your own.

### Hey, how'd you get the same URL to download a different script per OS?

Glad you asked! In a neat bit of synergy with my [bot program](https://gitlab.dannystewart.com/danny/telegram-bots), that `/evdl` URL actually goes to a [special endpoint](https://gitlab.dannystewart.com/danny/telegram-bots/-/blob/main/app/startup/bots.py?ref_type=heads#L94) on my bot server that determines your user agent and serves up the correct script accordingly!

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
