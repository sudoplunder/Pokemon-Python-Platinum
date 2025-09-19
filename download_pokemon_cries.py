#!/usr/bin/env python3
"""
Download Pokemon cries from Pokemon Showdown audio directory.
Downloads all .ogg files to assets/audio/sfx/cries/
"""

import os
import requests
from urllib.parse import urljoin, urlparse
from pathlib import Path
import time
import re

# Base URL for Pokemon Showdown cries
BASE_URL = "https://play.pokemonshowdown.com/audio/cries/"

# Output directory
OUTPUT_DIR = Path("assets/audio/sfx/cries")

def get_file_list():
    """Scrape the directory listing to get all .ogg files."""
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
        
        # Look for .ogg file links in the HTML
        ogg_pattern = r'href="([^"]*\.ogg)"'
        ogg_files = re.findall(ogg_pattern, response.text)
        
        return ogg_files
    except Exception as e:
        print(f"Error getting file list: {e}")
        return []

def download_file(filename, retries=3):
    """Download a single .ogg file with retry logic."""
    url = urljoin(BASE_URL, filename)
    output_path = OUTPUT_DIR / filename
    
    # Skip if file already exists
    if output_path.exists():
        print(f"⏭️  Skipping {filename} (already exists)")
        return True
    
    for attempt in range(retries):
        try:
            print(f"📥 Downloading {filename}... (attempt {attempt + 1})")
            
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Write file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"✅ Downloaded {filename} ({output_path.stat().st_size} bytes)")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading {filename} (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                print(f"⏳ Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"💥 Failed to download {filename} after {retries} attempts")
                return False
    
    return False

def main():
    """Main download function."""
    print("🎵 Pokemon Cry Downloader")
    print("=" * 50)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR.absolute()}")
    
    # Get list of .ogg files
    print("\n🔍 Getting file list from Pokemon Showdown...")
    ogg_files = get_file_list()
    
    if not ogg_files:
        print("❌ No .ogg files found or unable to access directory")
        return
    
    print(f"✅ Found {len(ogg_files)} .ogg files")
    
    # Download each file
    print("\n📥 Starting downloads...")
    successful = 0
    failed = 0
    
    for i, filename in enumerate(ogg_files, 1):
        print(f"\n[{i}/{len(ogg_files)}] Processing: {filename}")
        
        if download_file(filename):
            successful += 1
        else:
            failed += 1
        
        # Small delay between downloads to be respectful
        if i < len(ogg_files):
            time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Download Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Files saved to: {OUTPUT_DIR.absolute()}")
    
    if successful > 0:
        print(f"\n🎉 Downloaded {successful} Pokemon cries successfully!")
    
    if failed > 0:
        print(f"\n⚠️  {failed} files failed to download. You can re-run the script to retry.")

if __name__ == "__main__":
    main()