# NOAA GLERL VIIRS Wallpaper Updater (Windows)

Automatically downloads the most recent **NOAA GLERL VIIRS True Color** imagery and sets it as your Windows desktop (and lock screen) wallpaper, updating every 15 minutes.

## Features
- Pulls latest PNGs from NOAA GLERL ERDDAP
- Selects the largest (best coverage) recent image
- Fixes DPI metadata for Windows
- Sets wallpaper across all monitors
- Runs continuously on a 15-minute interval

## Requirements
- Windows 10 / 11  
- Python 3.8+

## Install dependencies:
```bash
pip install requests beautifulsoup4 pillow
```

## Data Source
Imagery is retrieved from NOAA GLERL ERDDAP:
https://coastwatch.glerl.noaa.gov/satellite-data-products/viirs/ 
