Function Test-Dependencies {
    # Check if ffmpeg is installed
    if (-Not (Get-Command 'ffmpeg' -ErrorAction SilentlyContinue)) {
        Write-Host "Warning: ffmpeg is not installed."
        return $false
    }
    return $true
}

if (Test-Dependencies) {
    # Create a temporary directory
    $tempDir = [System.IO.Path]::GetTempFileName()
    Remove-Item $tempDir
    New-Item -ItemType Directory -Path $tempDir

    # The URL of the file to download
    $url = "https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/win/evremixes.exe"

    # Download the file
    Write-Host "Downloading evremixes..."
    try {
        Invoke-WebRequest -Uri $url -OutFile "$tempDir\evremixes.exe"
    }
    catch {
        Write-Host "Download failed."
        Remove-Item -Recurse -Force $tempDir
        exit 1
    }

    # Run the program
    Write-Host "Running evremixes..."
    Start-Process -FilePath "$tempDir\evremixes.exe"

    # Clean up by removing the temporary directory
    Remove-Item -Recurse -Force $tempDir
}
else {
    # Define potential folders where aria2c might be located
    $potential_folders = @("C:\Users\danny\Downloads")

    # Search for aria2c
    $aria2c_path = $null
    foreach ($folder in $potential_folders) {
        $aria2c_candidate = Get-ChildItem -Path $folder -Recurse -File -Filter "aria2c.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($aria2c_candidate) {
            $aria2c_path = $aria2c_candidate.FullName
            break
        }
    }

    if (-not $aria2c_path) {
        Write-Host "aria2c.exe not found. Fallback methods will be used." -ForegroundColor Yellow
    }

    # Define output folder and other parameters
    $output_folder = "$env:USERPROFILE\Music\Evanescence Remixes"

    # Fetch JSON data and sort it by track_number
    $json_data = Invoke-RestMethod -Uri "https://git.dannystewart.com/danny/evremixes/raw/branch/main/evtracks.json"
    $json_data.tracks = $json_data.tracks | Sort-Object track_number

    # Create output folder if it doesn't exist; remove older files if it does
    if (Test-Path $output_folder) {
        Remove-Item "$output_folder\*.flac" -Force
        Write-Host "Folder already exists; older files removed." -ForegroundColor Yellow
    }
    else {
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

        # Try downloading the file using aria2c first
        if (Test-Path $aria2c_path) {
            & $aria2c_path --dir="$output_folder" --out="$final_filename" $file_url --disable-ipv6=true --quiet=true --show-console-readout=true
            continue
        }

        # If aria2c isn't available, fall back to WebClient
        try {
            $webclient = New-Object System.Net.WebClient
            $webclient.DownloadFile($file_url, "$output_folder\$final_filename")
            continue
        }
        catch {
            # Write-Host "WebClient failed; falling back to Invoke-WebRequest..." -ForegroundColor Yellow
        }

        # If WebClient fails, fall back to Invoke-WebRequest
        try {
            Invoke-WebRequest -Uri $file_url -OutFile "$output_folder\$final_filename"
        }
        catch {
            # Write-Host "Invoke-WebRequest also failed. Skipping this file." -ForegroundColor Red
            continue
        }
    }

    Start-Process "explorer.exe" -ArgumentList $output_folder
    Write-Host "All tracks downloaded! Enjoy!" -ForegroundColor Green
}
