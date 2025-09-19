#!/usr/bin/env python3
"""
Verify all game dependencies are properly installed and working.
"""

import sys
import warnings

# Suppress the pygame pkg_resources deprecation warning
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

def test_imports():
    """Test that all required packages can be imported."""
    tests = [
        ("pygame", "Game audio and graphics engine"),
        ("requests", "HTTP requests for downloading assets"),
        ("rich", "Beautiful terminal UI and formatting"),
        ("colorama", "Cross-platform colored terminal text"),
        ("pydub", "Audio file processing (optional)"),
        ("typing_extensions", "Enhanced typing support"),
    ]
    
    results = []
    
    for package, description in tests:
        try:
            __import__(package)
            results.append((package, True, description))
            print(f"✅ {package:<20} - {description}")
        except ImportError as e:
            results.append((package, False, f"Error: {e}"))
            print(f"❌ {package:<20} - Error: {e}")
    
    # Summary
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    print(f"\nImport Test Results: {success_count}/{total_count} packages working")
    
    if success_count == total_count:
        print("All dependencies are properly installed!")
        return True
    else:
        print("Some packages are missing. Run: python setup_requirements.py")
        return False

def test_core_functionality():
    """Test basic functionality of core packages."""
    print("\nTesting core functionality...")
    
    try:
        # Test pygame mixer (audio system)
        import pygame
        pygame.mixer.init()
        print("✅ pygame.mixer initialized successfully")
        pygame.mixer.quit()
    except Exception as e:
        print(f"pygame audio test failed: {e}")
    
    try:
        # Test rich console
        from rich.console import Console
        console = Console()
        print("✅ Rich console created successfully")
    except Exception as e:
        print(f"Rich console test failed: {e}")
    
    try:
        # Test colorama
        from colorama import Fore, Style, init
        init()
        print("✅ Colorama initialized successfully")
    except Exception as e:
        print(f"Colorama test failed: {e}")

if __name__ == "__main__":
    print("Game - Dependency Verification")
    print("=" * 50)
    
    # Test imports
    all_imports_work = test_imports()
    
    # Test functionality if imports work
    if all_imports_work:
        test_core_functionality()
        print("\nReady to play!")
        sys.exit(0)
    else:
        print("\nPlease install missing dependencies before playing.")
        sys.exit(1)