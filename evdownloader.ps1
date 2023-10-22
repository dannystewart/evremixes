# Evanescence remix downloader, now in PowerShell for you Windows users

# The URL of the file to download
$url = "https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/win/evremixes.exe"

# Define potential folders where aria2c might be located
$potential_folders = @("$env:USERPROFILE\Downloads")

# Search for aria2c
$aria2c_path = $null
foreach ($folder in $potential_folders) {
    $aria2c_candidate = Get-ChildItem -Path $folder -Recurse -File -Filter "aria2c.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($aria2c_candidate) {
        $aria2c_path = $aria2c_candidate.FullName
        break
    }
}

# Function to gracefully fall back to less preferred downloaders
Function Get-RemoteFile {
    param(
        [string]$url,
        [string]$outputPath,
        [string]$outputFolder = ''
    )
    if ($aria2c_path) {
        & $aria2c_path --dir="$outputFolder" --out="$outputPath" $url --disable-ipv6=true --quiet=true --show-console-readout=true
    }
    else {
        try {
            $webclient = New-Object System.Net.WebClient
            $webclient.DownloadFile($url, "$outputFolder\$outputPath")
        }
        catch {
            Write-Host "WebClient failed; falling back to Invoke-WebRequest..." -ForegroundColor Yellow
            Invoke-WebRequest -Uri $url -OutFile "$outputFolder\$outputPath"
        }
    }
}

# Trap function to clean up on interrupt
trap {
    Write-Host "Interrupt detected. Cleaning up..."
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    exit 1
}

# Create a temporary directory
$tempDir = [System.IO.Path]::GetTempFileName()
Remove-Item $tempDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Download the file
Write-Host "Downloading evremixes..."
Get-RemoteFile -url "https://git.dannystewart.com/danny/evremixes/raw/branch/main/dist/win/evremixes.exe" -outputPath "evremixes.exe" -outputFolder $tempDir

# Run the program in the current context
Write-Host "Running evremixes..."
$proc = Start-Process "$tempDir\evremixes.exe" -NoNewWindow -PassThru
$proc | Wait-Process
$exitCode = $proc.ExitCode

# Check if the process ran successfully
if ($exitCode -ne 0) {
    Write-Host "evremixes execution failed. Falling back to basic PowerShell downloader..." -ForegroundColor Yellow

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
        Get-RemoteFile -url $file_url -outputPath $final_filename -outputFolder $output_folder
    }

    Start-Process "explorer.exe" -ArgumentList $output_folder
    Write-Host "All tracks downloaded! Enjoy!" -ForegroundColor Green
}

# Clean up by removing the temporary directory
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
