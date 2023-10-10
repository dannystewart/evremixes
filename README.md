# Evanescence Remix Downloader

Download script for my Evanescence remixes. Grabs a JSON file containing a list of remixes and metadata, then downloads, converts to ALAC, adds metadata and cover art, and renames files. Ready for import into Apple Music!

## Setup

1. Install [Homebrew](https://brew.sh) if you don't already have it: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install Python 3: `brew install python`
3. Clone this repository somewhere: `git clone https://git.dannystewart.com/danny/evremixes.git`
4. Install dependencies: `pip install -r requirements.txt`

## Usage

Just run the script: `python evremixes.py`

It'll ask for a directory to download to. It defaults to `~/Downloads`, so just hit Enter if that's what you want*. It'll proceed to download into a subfolder by album name, adding metadata and cover artwork. They'll be named by track number and name, and can be imported directly into Apple Music.

*\*(you know, like the song)*

### Lazy Method

If you're lazy and can't or don't want to install Python and its dependencies, you can just run the executable in the `dist` directory:

```bash
cd dist
chmod +x evremixes
./evremixes
```

### Unbelievably Lazy But Extremely Cool Method

Just run this one command and watch the magic happen:
```bash
/bin/bash -c "$(curl -fsSL https://dnst.me/evdl)"
```

### How to update/replace albums/songs in Apple Music

It's always easiest if you have metadata on the files before importing. [Meta](https://www.nightbirdsevolve.com/meta/) is a great app for this, but you don't need to worry about it here as that's the point of this script, obviously.

#### Remove the old albums/songs

1. Open Apple Music.
2. Look in the bottom left corner for "Updating Cloud Music Library." Wait for this to finish and disappear.
3. Right-click the albums/songs and click Delete from Library.
4. Go to File > Library > Update Cloud Library, and again look in the bottom left for "Updating Cloud Music Library" and wait for it to finish.

You need to wait for it to completely sync the removal of the album. If you re-import before it's fully flushed out, you can end up with duplicates or have your new copies overwritten by the old versions.

#### Re-import the albums/songs

6. Go to File > Import….
7. Select the song file(s) or the entire folder containing the album and click Open.
8. Wait for it to import everything and verify that the album and metadata all look correct.
9. One more time, go to File > Library > Update Cloud Library and wait for it to finish.

If in doubt, it never hurts to run a sync twice. It can also help to have another device nearby to watch and make sure the changes are syncing correctly.
