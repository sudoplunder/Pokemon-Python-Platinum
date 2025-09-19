#!/usr/bin/env python3
"""
Asset Bundler for Pokemon Python Platinum
Packs thousands of small audio files into compressed bundles for faster download/extraction.
"""

import os
import json
import zipfile
import tarfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any
import argparse

class AssetBundler:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.bundles_dir = self.base_path / "bundles"
        self.manifest_file = self.bundles_dir / "asset_manifest.json"
        
        # Create bundles directory
        self.bundles_dir.mkdir(exist_ok=True)
    
    def create_bundle(self, name: str, source_dir: str, compression: str = "zip") -> Dict[str, Any]:
        """Create a compressed bundle from a directory of assets."""
        source_path = self.base_path / source_dir
        bundle_path = self.bundles_dir / f"{name}.{compression}"
        
        if not source_path.exists():
            print(f"Warning: Source directory {source_path} does not exist")
            return {}
        
        files_info = {}
        total_original_size = 0
        file_count = 0
        
        print(f"Creating bundle: {name}")
        print(f"Source: {source_path}")
        print(f"Output: {bundle_path}")
        
        if compression == "zip":
            with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        # Calculate relative path from source directory
                        relative_path = file_path.relative_to(source_path)
                        
                        # Add to bundle
                        bundle.write(file_path, relative_path)
                        
                        # Track file info
                        original_size = file_path.stat().st_size
                        files_info[str(relative_path)] = {
                            "original_size": original_size,
                            "hash": self._calculate_hash(file_path)
                        }
                        total_original_size += original_size
                        file_count += 1
        
        elif compression == "tar.gz":
            with tarfile.open(bundle_path, 'w:gz') as bundle:
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(source_path)
                        bundle.add(file_path, relative_path)
                        
                        original_size = file_path.stat().st_size
                        files_info[str(relative_path)] = {
                            "original_size": original_size,
                            "hash": self._calculate_hash(file_path)
                        }
                        total_original_size += original_size
                        file_count += 1
        
        # Calculate compression stats
        compressed_size = bundle_path.stat().st_size
        compression_ratio = (1 - compressed_size / total_original_size) * 100 if total_original_size > 0 else 0
        
        bundle_info = {
            "name": name,
            "file": f"{name}.{compression}",
            "source_directory": source_dir,
            "compression": compression,
            "file_count": file_count,
            "original_size": total_original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(compression_ratio, 2),
            "files": files_info,
            "hash": self._calculate_hash(bundle_path)
        }
        
        print(f"✅ Bundle created: {file_count} files")
        print(f"   Original size: {self._format_size(total_original_size)}")
        print(f"   Compressed size: {self._format_size(compressed_size)}")
        print(f"   Compression ratio: {compression_ratio:.1f}%")
        print()
        
        return bundle_info
    
    def create_audio_bundles(self):
        """Create optimized bundles for audio assets."""
        manifest = {
            "version": "1.0",
            "created": "2025-09-19",
            "bundles": []
        }
        
        # Bundle Pokemon cries
        pokemon_cries = self.create_bundle(
            "pokemon_cries", 
            "assets/audio/sfx/cries", 
            "zip"
        )
        if pokemon_cries:
            manifest["bundles"].append(pokemon_cries)
        
        # Bundle move sounds
        move_sounds = self.create_bundle(
            "move_sounds", 
            "assets/audio/sfx/moves", 
            "zip"
        )
        if move_sounds:
            manifest["bundles"].append(move_sounds)
        
        # Bundle other audio effects
        other_audio = self.create_bundle(
            "audio_effects", 
            "assets/audio/sfx", 
            "zip"
        )
        if other_audio:
            # Remove the cries and moves from this bundle since they're separate
            manifest["bundles"].append(other_audio)
        
        # Save manifest
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"📄 Manifest saved: {self.manifest_file}")
        
        # Calculate total savings
        total_original = sum(bundle["original_size"] for bundle in manifest["bundles"])
        total_compressed = sum(bundle["compressed_size"] for bundle in manifest["bundles"])
        total_files = sum(bundle["file_count"] for bundle in manifest["bundles"])
        
        print("\n🎉 Asset Bundling Complete!")
        print(f"Total files bundled: {total_files:,}")
        print(f"Total original size: {self._format_size(total_original)}")
        print(f"Total compressed size: {self._format_size(total_compressed)}")
        print(f"Total space saved: {self._format_size(total_original - total_compressed)}")
        print(f"Overall compression: {((total_original - total_compressed) / total_original * 100):.1f}%")
        print(f"File count reduced from {total_files:,} to {len(manifest['bundles'])} bundles")
        
        return manifest
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # First 16 chars for brevity
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

def main():
    parser = argparse.ArgumentParser(description="Create asset bundles for Pokemon Python Platinum")
    parser.add_argument("--base-path", default=".", help="Base path of the project")
    parser.add_argument("--audio-only", action="store_true", help="Only bundle audio assets")
    
    args = parser.parse_args()
    
    bundler = AssetBundler(args.base_path)
    
    if args.audio_only:
        bundler.create_audio_bundles()
    else:
        # Future: Add more bundle types (images, data, etc.)
        bundler.create_audio_bundles()

if __name__ == "__main__":
    main()