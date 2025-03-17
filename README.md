# Evanescence Remix Downloader

The "canonical" versions of my remixes are the ones officially published [on my website](https://music.dannystewart.com/evanescence/), so the script grabs them from there. [`evtracks.json`](evtracks.json) holds the current list of available remixes, metadata, and URLs.

You're presented with the choice of FLAC or ALAC (Apple Lossless), as well as where you want the files to be saved. The default options are your Downloads and Music folders, but you can also enter a custom path. After downloading, it will apply the correct metadata, album art, and filenames.

## Installation and Usage

To install, make sure you have Python set up, then run the following.[^1]

```bash
pip install git+https://github.com/dannystewart/evremixes.git
```
And then simply run:

```bash
evremixes
```
