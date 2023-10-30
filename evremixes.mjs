import axios from 'axios';
import chalk from 'chalk';
import fs from 'fs';
import ora from 'ora';
import path from 'path';

const outputFolder = path.join(process.env.HOME, 'Downloads', 'Evanescence Remixes');

async function fetchJSON() {
    const response = await axios.get('https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json');
    const sortedTracks = response.data.tracks.sort((a, b) => a.track_number - b.track_number);
    return {
        ...response.data,
        tracks: sortedTracks
    };
}

async function downloadFile(url, dest, trackTitle) {
    const spinner = ora(`Downloading ${chalk.blue(trackTitle)}...`).start();
    const writer = fs.createWriteStream(dest);

    const response = await axios({
        url,
        method: 'GET',
        responseType: 'stream'
    });

    response.data.pipe(writer);

    return new Promise((resolve, reject) => {
        writer.on('finish', () => {
            spinner.text = `Downloaded ${chalk.blue(trackTitle)}`;
            spinner.succeed();
            resolve();
        });
        writer.on('error', err => {
            spinner.fail(`Download failed for ${trackTitle}}`);
            reject(err);
        });
    });
}

async function main() {
    console.log(chalk.green('Saving Evanescence Remixes to ~/Downloads...'));

    if (!fs.existsSync(outputFolder)) {
        fs.mkdirSync(outputFolder, { recursive: true });
    } else {
        const files = fs.readdirSync(outputFolder).filter(f => f.endsWith('.m4a') || f.endsWith('.m4a.temp'));
        files.forEach(file => fs.unlinkSync(path.join(outputFolder, file)));
        console.log(chalk.yellow('Folder already exists; older files removed.'));
    }

    const jsonData = await fetchJSON();
    const tracks = jsonData.tracks;

    for (let i = 0; i < tracks.length; i++) {
        const track = tracks[i];
        const trackName = track.track_name;
        const fileUrl = track.file_url.replace(/\.flac$/, '.m4a');
        const formattedTrackNumber = String(track.track_number).padStart(2, '0');

        const tempFilename = path.join(outputFolder, `${formattedTrackNumber} - ${trackName}.m4a.temp`);
        const finalFilename = path.join(outputFolder, `${formattedTrackNumber} - ${trackName}.m4a`);

        await downloadFile(fileUrl, tempFilename, trackName).catch(err => console.error(chalk.red(err)));
        fs.renameSync(tempFilename, finalFilename);
    }

    console.log(chalk.green('All tracks downloaded! Enjoy!'));
}

main().catch(err => console.error(err));
