
import os
import re
import requests
from bs4 import BeautifulSoup
import ctypes
from PIL import Image, ImageDraw, ImageFont
import winreg
from datetime import datetime, timedelta
import time

# ---------- NEW: remember last applied PNG URL ----------
STATE_FILE = os.path.join(os.getcwd(), "last_url.txt")

def load_last_url():
    """Return the last applied PNG URL, or None if not present."""
    try:
        if os.path.isfile(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                url = f.read().strip()
                return url or None
    except Exception:
        pass
    return None

def save_last_url(url: str):
    """Persist the last applied PNG URL."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(url.strip())
    except Exception as e:
        print(f"Warning: could not save last_url.txt: {e}")

# Function to find the top 3 most recent PNGs
def find_top_3_recent_pngs(base_url):
    resp = requests.get(base_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    png_links = [lnk for lnk in links if lnk.endswith(".png")]
    subdirs = [lnk for lnk in links if lnk.endswith("/")]
    if png_links:
        # Assumes lexicographic sorting puts newest first given the filename includes date/time
        png_links.sort(reverse=True)
        return [base_url + p for p in png_links[:3]]
    # If no PNGs here, try child directories (recursive)
    for sub in subdirs:
        sub_url = base_url + sub
        result = find_top_3_recent_pngs(sub_url)
        if result:
            return result
    return []

# Function to determine the largest PNG by size (fallback if HEAD lacks Content-Length)
def find_largest_png(png_urls):
    largest_url = None
    largest_size = 0
    for url in png_urls:
        size = 0
        try:
            r = requests.head(url, timeout=20)
            size = int(r.headers.get("Content-Length", 0))
            if size == 0:
                r = requests.get(url, stream=True, timeout=20)
                size = int(r.headers.get("Content-Length", 0))
        except Exception:
            size = 0
        if size > largest_size:
            largest_size = size
            largest_url = url
    return largest_url

# Download PNG to disk
def download_png(url, save_path_png):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with open(save_path_png, "wb") as f:
        f.write(r.content)

# Convert PNG → JPEG (handles alpha by compositing over white)
def convert_png_to_jpeg(png_path, jpeg_path, quality=95):
    with Image.open(png_path) as img:
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.getchannel("A") if "A" in img.getbands() else None
            if alpha is not None:
                background.paste(img.convert("RGB"), mask=alpha)
            else:
                background.paste(img.convert("RGB"))
            rgb_img = background
        else:
            rgb_img = img.convert("RGB")
        rgb_img.save(jpeg_path, "JPEG", quality=95, optimize=True)

# --- Parse UTC datetime from filename: npp_viirs_true_color_YYYYMMDD_HHMMSS_GreatLakes.png ---
def parse_datetime_utc_from_filename(url_or_path):
    """
    Returns a naive datetime assumed to be UTC for pattern YYYYMMDD_HHMMSS found in filename.
    If parsing fails, returns None.
    """
    filename = os.path.basename(url_or_path)
    m = re.search(r'(\d{8})_(\d{6})', filename)
    if not m:
        return None
    yyyymmdd = m.group(1)
    hhmmss = m.group(2)
    try:
        dt_utc = datetime.strptime(f"{yyyymmdd}{hhmmss}", "%Y%m%d%H%M%S")
        return dt_utc
    except ValueError:
        return None


# --- Build caption using fixed Eastern Time (EST = UTC-5, no DST switching) ---
def build_caption_from_url_est_fixed(png_url):
    """
    Produces a caption like:
    'VIIRS NPP • 2025-12-15 14:05:12 EST • Great Lakes'
    Using fixed EST (UTC-5) year-round.
    """
    fname = os.path.basename(png_url)
    lower = fname.lower()
    # Platform inference (simple)
    if "npp_" in lower:
        platform = "NPP"
    elif "j1_" in lower or "jpss1" in lower:
        platform = "JPSS-1"
    elif "j2_" in lower or "jpss2" in lower:
        platform = "JPSS-2"
    else:
        platform = "VIIRS"

    # Region (e.g., GreatLakes)
    region_match = re.search(r'_(GreatLakes)\.png$', fname, re.IGNORECASE)
    region = (region_match.group(1) if region_match else "").replace("_", " ")
    if region.lower() == "greatlakes":
        region = "NOAA CoastWatch | Great Lakes Regional Node"

    # Parse UTC datetime and convert to fixed EST (UTC-5)
    dt_utc = parse_datetime_utc_from_filename(png_url)
    if dt_utc is not None:
        dt_est = dt_utc - timedelta(hours=5)
        dt_str = dt_est.strftime("%Y-%m-%d %H:%M:%S EST |")
    else:
        dt_str = "Date/Time Unknown |"

    parts = [f"VIIRS {platform} |", dt_str]
    if region:
        parts.append(region)
    return " ".join(parts)


# --- Draw smaller black rectangle with white text exactly in the top-left corner ---
def add_caption_top_left_exact(jpeg_path, caption_text, font_scale=0.02, pad_x_factor=0.4, pad_y_factor=0.4):
    """
    Places a black rectangle with white text at the exact top (no margins).
    - font_scale: fraction of image height used for font size.
    - pad_x_factor/pad_y_factor: padding relative to font size to keep the box compact.
    """
    if not caption_text:
        return
    with Image.open(jpeg_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        # Smaller font than before to reduce box size
        font_size = max(13, int(h * font_scale))
        # Try common fonts; fallback to default
        font = None
        for fpath in [
            "arial.ttf",
            "Segoe UI.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            try:
                font = ImageFont.truetype(fpath, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(img)
        # Measure text
        text_bbox = draw.textbbox((0, 0), caption_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        # Smaller padding
        pad_x = int(font_size * pad_x_factor)
        pad_y = int(font_size * pad_y_factor)
        rect_left = ((w - (text_w + 2 * pad_x))//2)
        rect_top = 0.5
        rect_right = rect_left + (text_w + 2 * pad_x)
        rect_bottom = rect_top + (text_h + 2 * pad_y)
        # Black rectangle
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 0))
        # White text
        text_x = rect_left + pad_x
        text_y = rect_top + pad_y
        draw.text((text_x, text_y), caption_text, font=font, fill=(255, 255, 255))
        img.save(jpeg_path, "JPEG", quality=95, optimize=True)

# Set wallpaper (JPEG path)
def set_wallpaper_for_all_monitors(image_path_jpeg):
    absolute_path = os.path.abspath(image_path_jpeg)
    # Style options: 0=Center, 2=Stretch, 6=Fit, 10=Fill
    style = 2
    tile_wallpaper = 0
    # SPI_SETDESKWALLPAPER = 20; flags=3 to update the INI file and broadcast change
    ctypes.windll.user32.SystemParametersInfoW(20, 0, absolute_path, 3)
    # Persist preferences to registry
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Wallpaper", 0, winreg.REG_SZ, absolute_path)
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, str(style))
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, str(tile_wallpaper))

# Safe file delete helper
def safe_delete(path):
    try:
        if path and os.path.isfile(path):
            os.remove(path)
            print(f"Deleted: {path}")
    except Exception as e:
        print(f"Warning: could not delete {path}: {e}")

def main():
    # Current year/month
    now = datetime.now()
    year = now.year
    month = now.month
    base_url = f"https://apps.glerl.noaa.gov/erddap/files/GL_VIIRS_True_Color/{year}/{month:02d}/"
    print(f"Searching for the top 3 most recent PNGs in: {base_url}")

    top3 = find_top_3_recent_pngs(base_url)
    if not top3:
        print("No PNG files found.")
        return

    print(f"Top 3 recent PNGs found: {top3}\n")
    largest_png_url = find_largest_png(top3) or top3[0]
    print(f"Largest PNG selected: {largest_png_url}\n")

    last_url = load_last_url()
    last_url = "google.ca/?"
    if last_url == largest_png_url:
        # Exactly the same URL as last time — do nothing
        print("Same image as last iteration. Skipping download, conversion, and wallpaper update.\n")
        return

    # File paths
    png_path = os.path.join(os.getcwd(), "wallpaper.png")
    jpg_path = os.path.join(os.getcwd(), "wallpaper.jpg")

    # Download PNG
    download_png(largest_png_url, png_path)

    # Convert PNG → JPEG
    convert_png_to_jpeg(png_path, jpg_path, quality=95)
    print(f"Downloaded PNG → converted to JPEG at: {jpg_path}\n")

    # --- Caption from filename in fixed Eastern Time (EST = UTC-5) ---
    caption = build_caption_from_url_est_fixed(largest_png_url)
    add_caption_top_left_exact(jpg_path, caption)
    print(f"Caption added (top-left): '{caption}'\n")

    # Set the wallpaper using JPEG
    set_wallpaper_for_all_monitors(jpg_path)
    print("Wallpaper set successfully (JPEG)!")
    save_last_url(largest_png_url)  # remember the URL we just applied

    # Cleanup: delete PNG and JPEG
    safe_delete(png_path)
    safe_delete(jpg_path)

if __name__ == "__main__":
    while True:
        main()
        print("Checking for new image in 30 mins \n")
        time.sleep(1800)
