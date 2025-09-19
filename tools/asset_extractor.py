#!/usr/bin/env python3
"""
Asset Extractor for Pokemon Python Platinum
Extracts compressed asset bundles on first run or when bundles are updated.
"""

import os
import json
import zipfile
import tarfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any
import time

class AssetExtractor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.bundles_dir = self.base_path / "bundles"
        self.manifest_file = self.bundles_dir / "asset_manifest.json"
        self.extraction_state_file = self.base_path / ".asset_extraction_state.json"
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load the asset manifest."""
        if not self.manifest_file.exists():
            return {}
        
        with open(self.manifest_file, 'r') as f:
            return json.load(f)
    
    def load_extraction_state(self) -> Dict[str, Any]:
        """Load the previous extraction state."""
        if not self.extraction_state_file.exists():
            return {}
        
        with open(self.extraction_state_file, 'r') as f:
            return json.load(f)
    
    def save_extraction_state(self, state: Dict[str, Any]):
        """Save the current extraction state."""
        with open(self.extraction_state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def needs_extraction(self, bundle: Dict[str, Any]) -> bool:
        """Check if a bundle needs to be extracted."""
        bundle_name = bundle["name"]
        bundle_file = self.bundles_dir / bundle["file"]
        target_dir = self.base_path / bundle["source_directory"]
        
        # Check if bundle file exists
        if not bundle_file.exists():
            print(f"⚠️  Bundle file missing: {bundle_file}")
            return False
        
        # Check if target directory exists
        if not target_dir.exists():
            print(f"📁 Target directory missing: {target_dir}")
            return True
        
        # Check extraction state
        state = self.load_extraction_state()
        if bundle_name not in state:
            print(f"🆕 Bundle never extracted: {bundle_name}")
            return True
        
        # Check if bundle hash has changed
        current_hash = self._calculate_hash(bundle_file)
        if state[bundle_name].get("hash") != current_hash:
            print(f"🔄 Bundle updated: {bundle_name}")
            return True
        
        # Check if all files exist
        missing_files = []
        for file_path in bundle["files"]:
            full_path = target_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing {len(missing_files)} files from {bundle_name}")
            return True
        
        return False
    
    def extract_bundle(self, bundle: Dict[str, Any]) -> bool:
        """Extract a single bundle."""
        bundle_name = bundle["name"]
        bundle_file = self.bundles_dir / bundle["file"]
        target_dir = self.base_path / bundle["source_directory"]
        
        if not bundle_file.exists():
            print(f"Error: Bundle file not found: {bundle_file}")
            return False
        
        print(f"📦 Extracting {bundle_name}...")
        print(f"   From: {bundle_file}")
        print(f"   To: {target_dir}")
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            if bundle["compression"] == "zip":
                with zipfile.ZipFile(bundle_file, 'r') as archive:
                    archive.extractall(target_dir)
            
            elif bundle["compression"] == "tar.gz":
                with tarfile.open(bundle_file, 'r:gz') as archive:
                    archive.extractall(target_dir)
            
            else:
                print(f"Error: Unsupported compression: {bundle['compression']}")
                return False
            
            extraction_time = time.time() - start_time
            
            # Verify extraction
            extracted_files = 0
            for file_path in bundle["files"]:
                full_path = target_dir / file_path
                if full_path.exists():
                    extracted_files += 1
            
            print(f"   ✅ Extracted {extracted_files}/{bundle['file_count']} files in {extraction_time:.2f}s")
            
            # Update extraction state
            state = self.load_extraction_state()
            state[bundle_name] = {
                "hash": bundle["hash"],
                "extracted_at": time.time(),
                "file_count": extracted_files
            }
            self.save_extraction_state(state)
            
            return extracted_files == bundle["file_count"]
            
        except Exception as e:
            print(f"Error extracting {bundle_name}: {e}")
            return False
    
    def extract_all_bundles(self) -> bool:
        """Extract all bundles that need extraction."""
        manifest = self.load_manifest()
        
        if not manifest or "bundles" not in manifest:
            print("No asset manifest found. Run asset_bundler.py first.")
            return False
        
        bundles_to_extract = []
        for bundle in manifest["bundles"]:
            if self.needs_extraction(bundle):
                bundles_to_extract.append(bundle)
        
        if not bundles_to_extract:
            print("✅ All assets are up to date!")
            return True
        
        print(f"🚀 Extracting {len(bundles_to_extract)} asset bundles...")
        print()
        
        success_count = 0
        total_files = 0
        start_time = time.time()
        
        for bundle in bundles_to_extract:
            if self.extract_bundle(bundle):
                success_count += 1
                total_files += bundle["file_count"]
            print()
        
        total_time = time.time() - start_time
        
        print(f"🎉 Asset extraction complete!")
        print(f"   Bundles processed: {success_count}/{len(bundles_to_extract)}")
        print(f"   Files extracted: {total_files:,}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average speed: {total_files/total_time:.0f} files/second")
        
        return success_count == len(bundles_to_extract)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract asset bundles for Pokemon Python Platinum")
    parser.add_argument("--base-path", default=".", help="Base path of the project")
    parser.add_argument("--force", action="store_true", help="Force re-extraction of all bundles")
    
    args = parser.parse_args()
    
    extractor = AssetExtractor(args.base_path)
    
    if args.force:
        # Clear extraction state to force re-extraction
        if extractor.extraction_state_file.exists():
            extractor.extraction_state_file.unlink()
        print("🔄 Forcing re-extraction of all bundles...")
    
    success = extractor.extract_all_bundles()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()