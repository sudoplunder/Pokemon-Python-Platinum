#!/usr/bin/env python3
"""
Enhanced setup script that handles both dependencies and asset extraction.
"""

import os
import sys
import warnings
from pathlib import Path

# Suppress the pygame pkg_resources deprecation warning
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Add tools directory to path
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

def main():
    print("🎮 Pokemon Python Platinum - Enhanced Setup")
    print("=" * 50)
    
    # Step 1: Install dependencies
    print("\n📦 Step 1: Installing Dependencies")
    try:
        from setup_requirements import RequirementsSetup
        setup = RequirementsSetup()
        setup.run()
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    
    # Step 2: Extract asset bundles
    print("\n🎵 Step 2: Extracting Audio Assets")
    try:
        from asset_extractor import AssetExtractor
        extractor = AssetExtractor(".")
        success = extractor.extract_all_bundles()
        if not success:
            print("⚠️  Some assets failed to extract, but the game may still work")
    except Exception as e:
        print(f"⚠️  Asset extraction error: {e}")
        print("   The game will try to use individual audio files if available")
    
    # Step 3: Verify everything is ready
    print("\n✅ Step 3: Final Verification")
    try:
        from verify_dependencies import main as verify_deps
        verify_deps()
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    
    print("\n🎉 Setup Complete! You can now run the game.")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        input("\nPress Enter to exit...")
        sys.exit(1)