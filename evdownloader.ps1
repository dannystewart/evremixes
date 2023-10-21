# Define the full path to aria2c
$aria2c_path = "C:\Users\danny\Downloads\aria2-1.36.0-win-64bit-build1\aria2c.exe"

# Define output folder and other parameters
$output_folder = "$env:USERPROFILE\Music\Evanescence Remixes"

# Fetch JSON data and sort it by track_number
$json_data = Invoke-RestMethod -Uri "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
$json_data.tracks = $json_data.tracks | Sort-Object track_number

# Create output folder if it doesn't exist; remove older files if it does
if (Test-Path $output_folder) {
    Remove-Item "$output_folder\*" -Force
    Write-Host "Folder already exists; older files removed." -ForegroundColor Yellow
} else {
    New-Item -Path $output_folder -ItemType Directory -Force > $null
}

# Loop over each track in the JSON array
$length = $json_data.tracks.Count
for ($i = 0; $i -lt $length; $i++) {

    $track = $json_data.tracks[$i]
    $track_name = $track.track_name
    $file_url = $track.file_url
    $track_number = $track.track_number

    # Generate final file names
    $formatted_track_number = "{0:D2}" -f $track_number
    $final_filename = "$formatted_track_number - $track_name.flac"

    Write-Host "[$($i + 1)/$length] Downloading $track_name..."

    # Download the file using aria2c
    & $aria2c_path --dir="$output_folder" --out="$final_filename" $file_url --disable-ipv6=true --quiet=true --show-console-readout=true
}

Start-Process "explorer.exe" -ArgumentList $output_folder
Write-Host "All tracks downloaded! Enjoy!" -ForegroundColor Green
