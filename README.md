# Evanescence Remix Scripts

Various download and conversion scripts for my Evanescence remixes.

## Easy Downloader (Bash)

This is the one meant to be used by anybody. Just run this:
```bash
bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

This leads to `evdownloader.sh` here in the repo. It grabs a JSON of all my current remixes and metadata and uses that to download them to your `~/Downloads` folder. Files come pre-tagged and are ready to import into something like Apple Music.

There is one dependency, which is `jq` to parse JSON. If you have [Homebrew](https://brew.sh) the script should install it automatically, but if not, you'll need to install it.

## Other Scripts (Python)

### Setup and dependencies

1. Install [Homebrew](https://brew.sh) if you don't already have it: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install Python 3: `brew install python`
3. Clone this repository somewhere: `git clone https://git.dannystewart.com/danny/evremixes.git`
4. Install dependencies: `pip install -r requirements.txt`

To run the script, just `cd` to the directory and run `python scriptname.py` (replacing the script name, obviously).

Note that there are better/cleaner ways to run Python using virtual environments, but that's beyond the scope of this readme.

### evremixes

This is a fancier Python version of the main downloader script. This one handles the conversion from FLAC to ALAC (as well as all the metadata tagging) locally on your machine.

I wanted to use this by default because it's way cooler, but I abandoned it because it had too many Python dependencies, and precompiled binaries were architecture-specific. It converts to FLAC to ALAC on your local machine, which also means it requires `ffmpeg` and I couldn't guarantee that would be available.

### evconverter

This is what I use to convert the FLAC files to ALAC, tag them with the correct metadata and album art, and re-upload them to Azure so they can be downloaded by the main Bash script. (I do the heavy lifting so you don't have to!)

### evtelegram

This is a cool script I wrote to convert, tag, and upload selected remixes to a Telegram channel where I'm keeping all of them.

### Binary Versions

There are precompiled binaries that avoid the need to have Python or its depenedencies, but as noted above, they are dependent on platform architecture, so you'll need to run the x86 one on Intel and the ARM one on Apple Silicon.

The scripts are in the `dist` directory. Just `cd` from there to either `x86` or `arm` depending on your platform, then run `chmod +x ./evremixes` to make the script executable and `./evremixes` to run it.

### Other Notes

#### How to update/replace albums/songs in Apple Music

It's always easiest if you have metadata on the files before importing. [Meta](https://www.nightbirdsevolve.com/meta/) is a great app for this, but you don't need to worry about it here as that's the point of all this, obviously.

##### Remove the old albums/songs

1. Open Apple Music.
2. Look in the bottom left corner for "Updating Cloud Music Library." Wait for this to finish and disappear.
3. Right-click the albums/songs and click Delete from Library.
4. Go to File > Library > Update Cloud Library, and again look in the bottom left for "Updating Cloud Music Library" and wait for it to finish.

You need to wait for it to completely sync the removal of the album. If you re-import before it's fully flushed out, you can end up with duplicates or have your new copies overwritten by the old versions.

##### Re-import the albums/songs

6. Go to File > Import….
7. Select the song file(s) or the entire folder containing the album and click Open.
8. Wait for it to import everything and verify that the album and metadata all look correct.
9. One more time, go to File > Library > Update Cloud Library and wait for it to finish.

If in doubt, it never hurts to run a sync twice. It can also help to have another device nearby to watch and make sure the changes are syncing correctly.
