import os
import requests
from bs4 import BeautifulSoup
import ctypes
from PIL import Image
import winreg
from datetime import datetime
import time
import subprocess

# Function to find the top 3 most recent PNGs
def find_top_3_recent_pngs(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [link.get("href") for link in soup.find_all("a") if link.get("href")]
    png_links = [link for link in links if link.endswith(".png")]
    subdirs = [link for link in links if link.endswith("/")]

    if png_links:
        # Sort PNG links based on filename timestamps in descending order
        png_links.sort(reverse=True)
        # Keep the top 3 most recent
        return [base_url + png for png in png_links[:3]]

    for subdir in subdirs:  # If no PNGs found, search subdirectories recursively
        subdir_url = base_url + subdir
        result = find_top_3_recent_pngs(subdir_url)
        if result:
            return result

    return []

# Function to determine the largest PNG by size
def find_largest_png(png_urls):
    largest_url = None
    largest_size = 0
    for url in png_urls:
        response = requests.head(url)  # Get the headers only to check size
        size = int(response.headers.get("Content-Length", 0))
        if size > largest_size:
            largest_size = size
            largest_url = url
    return largest_url

# Function to download the PNG
def download_png(url, save_path):
    response = requests.get(url)
    with open(save_path, "wb") as file:
        file.write(response.content)

# Function to fix DPI and save the image
def fix_image_dpi(image_path):
    with Image.open(image_path) as img:
        img.save(image_path, dpi=(96, 96))  # Fix DPI to avoid invalid resolution warnings

# Function to set the wallpaper on each monitor
def set_wallpaper_for_all_monitors(image_path):
    absolute_path = os.path.abspath(image_path)

    # Wallpaper styles:
    # 0: Centered
    # 2: Stretched
    # 6: Fit
    # 10: Fill
    style = 2  # Choose 'Stretched' style
    tile_wallpaper = 0  # 0 = No tiling, 1 = Tile

    # Apply the wallpaper globally
    ctypes.windll.user32.SystemParametersInfoW(20, 0, absolute_path, 3)

    # Modify registry for individual monitor settings
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, str(style))
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, str(tile_wallpaper))

# Function to set the lock screen wallpaper using PowerShell
def set_lockscreen_wallpaper_powershell(image_path):
    powershell_script = f"""
    $lockscreenWallpaper = "{image_path}"
    $key = "HKCU:\\Control Panel\\Desktop"
    Set-ItemProperty -Path $key -Name "LockScreen" -Value $lockscreenWallpaper
    """
    subprocess.run(["powershell", "-Command", powershell_script], check=True)

# Main script
def main():
    # Get the current year and month
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month

    # Format the base URL to reflect the current year and month
    base_url = f"https://apps.glerl.noaa.gov/erddap/files/GL_VIIRS_True_Color/{year}/{month:02d}/"
    
    print(f"Searching for the top 3 most recent PNGs in: {base_url}")

    top_3_png_urls = find_top_3_recent_pngs(base_url)

    if top_3_png_urls:
        print(f"Top 3 recent PNGs found: {top_3_png_urls}")
        largest_png_url = find_largest_png(top_3_png_urls)
        print(f"Largest PNG selected: {largest_png_url}")

        save_path = os.path.join(os.getcwd(), "wallpaper.png")
        download_png(largest_png_url, save_path)
        fix_image_dpi(save_path)  # Fix DPI
        print(f"Downloaded and processed to: {save_path}")
        set_wallpaper_for_all_monitors(save_path)
        print("Wallpaper set successfully!")

        # Set the lockscreen wallpaper using PowerShell
        set_lockscreen_wallpaper_powershell(save_path)
        print("Lockscreen wallpaper set successfully!")
    else:
        print("No PNG files found.")

# Run the main script with a timer
if __name__ == "__main__":
    while True:
        main()  # Run the wallpaper update
        print("Checking for new image in 15 mins \n")
        time.sleep(900)  # Wait for 15 mins before checking again
