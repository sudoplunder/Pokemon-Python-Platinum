#!/usr/bin/env python3
"""
Game - Requirements Setup
High-polish requirement checker with progress bars and detailed error handling.
"""

import sys
import subprocess
import importlib
import platform
from pathlib import Path
import time
import warnings

# Suppress the pygame pkg_resources deprecation warning
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Try to import rich, if not available, install it first
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.align import Align
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class RequirementsSetup:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.failed_packages = []
        self.installed_packages = []
        
    def print(self, text, style=None):
        """Print with or without Rich styling."""
        if RICH_AVAILABLE and self.console:
            self.console.print(text, style=style)
        else:
            print(text)
    
    def show_title(self):
        """Display the setup title."""
        if RICH_AVAILABLE:
            title_panel = Panel(
                Text("Requirements Setup", justify="center", style="bold bright_yellow"),
                border_style="bright_white",
                padding=(1, 2)
            )
            self.console.print(Align.center(title_panel))
            self.console.print()
        else:
            print("=" * 60)
            print("    Requirements Setup")
            print("=" * 60)
            print()
    
    def check_python_version(self):
        """Check if Python version is compatible."""
        version = sys.version_info
        self.print(f"Checking Python version...", style="bright_blue")
        
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.print(f"❌ Python {version.major}.{version.minor} detected", style="red")
            self.print(f"Python 3.8 or higher is required.", style="red")
            self.print(f"Download from: https://python.org/downloads/", style="bright_cyan")
            return False
        
        self.print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible", style="green")
        return True
    
    def check_pip(self):
        """Check if pip is available."""
        self.print(f"Checking pip availability...", style="bright_blue")
        
        try:
            import pip
            self.print(f"✅ pip is available", style="green")
            return True
        except ImportError:
            try:
                subprocess.run([sys.executable, "-m", "pip", "--version"], 
                             capture_output=True, check=True)
                self.print(f"✅ pip is available via module", style="green")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.print(f"❌ pip is not installed", style="red")
                self.print(f"Install pip: https://pip.pypa.io/en/stable/installation/", style="bright_cyan")
                return False
    
    def install_rich_first(self):
        """Install Rich first if not available."""
        global RICH_AVAILABLE
        if RICH_AVAILABLE:
            return True
            
        print("Installing Rich for better UI...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "rich"], 
                         check=True, capture_output=True)
            print("✅ Rich installed successfully")
            # Re-import Rich
            try:
                from rich.console import Console
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
                from rich.panel import Panel
                from rich.text import Text
                from rich.prompt import Confirm
                from rich.table import Table
                from rich.align import Align
                from rich import print as rprint
                RICH_AVAILABLE = True
                self.console = Console()
                return True
            except ImportError:
                print("⚠️ Rich installed but couldn't import")
                return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Rich: {e}")
            return False
    
    def get_requirements(self):
        """Get list of required packages."""
        # Complete list of requirements based on actual imports in the codebase
        requirements = [
            "pygame>=2.0.0",        # Audio system (game sounds/music)
            "requests>=2.25.0",     # HTTP requests (downloading Pokemon cries)
            "rich>=10.0.0",         # Beautiful terminal UI (menus, battle interface)
            "colorama>=0.4.0",      # Cross-platform colored terminal text
            "pydub>=0.25.0",        # Audio file conversion (optional for audio tools)
            "typing-extensions>=4.0.0",  # Enhanced typing support for Python <3.10
        ]
        
        return requirements
    
    def install_package(self, package, progress_task=None):
        """Install a single package with error handling."""
        try:
            if progress_task and RICH_AVAILABLE:
                self.console.print(f"Installing {package}...", style="bright_blue")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.installed_packages.append(package)
            
            if progress_task and RICH_AVAILABLE:
                self.console.print(f"✅ {package} installed successfully", style="green")
            
            return True, None
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            
            # Provide helpful error messages for specific packages
            help_msg = self._get_package_help(package)
            if help_msg:
                error_msg += f"\n{help_msg}"
            
            self.failed_packages.append((package, error_msg))
            
            if progress_task and RICH_AVAILABLE:
                self.console.print(f"❌ Failed to install {package}", style="red")
                self.console.print(f"   Error: {error_msg}", style="dim red")
            
            return False, error_msg
    
    def _get_package_help(self, package):
        """Get helpful installation tips for specific packages."""
        package_name = package.split(">=")[0].split("==")[0]
        
        help_messages = {
            "pygame": "pygame requires additional system libraries. Try: pip install pygame --upgrade",
            "pydub": "pydub requires FFmpeg for audio conversion. Install FFmpeg or skip audio tools.",
            "colorama": "colorama provides cross-platform colored text support.",
            "typing-extensions": "typing-extensions provides enhanced typing for older Python versions."
        }
        
        return help_messages.get(package_name, "")
    
    def install_requirements(self, requirements):
        """Install all requirements with progress tracking."""
        if not requirements:
            self.print("No requirements to install.", style="green")
            return True
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                task = progress.add_task("Installing packages...", total=len(requirements))
                
                for package in requirements:
                    progress.update(task, description=f"Installing {package}")
                    success, error = self.install_package(package)
                    progress.advance(task)
                    time.sleep(0.1)  # Small delay for visual effect
                
                progress.update(task, description="Installation complete!")
        else:
            print(f"Installing {len(requirements)} packages...")
            for i, package in enumerate(requirements, 1):
                print(f"[{i}/{len(requirements)}] Installing {package}...")
                self.install_package(package)
        
        return len(self.failed_packages) == 0
    
    def show_results(self):
        """Display installation results."""
        if RICH_AVAILABLE:
            from rich.box import ROUNDED
            # Create results table
            table = Table(title="Installation Results", box=ROUNDED)
            table.add_column("Package", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Details", style="dim")
            
            # Add successful installations
            for package in self.installed_packages:
                table.add_row(package, "✅ Success", "Installed successfully")
            
            # Add failed installations
            for package, error in self.failed_packages:
                table.add_row(package, "❌ Failed", error[:50] + "..." if len(error) > 50 else error)
            
            self.console.print(table)
            self.console.print()
            
            if self.failed_packages:
                error_panel = Panel(
                    f"[red]{len(self.failed_packages)} package(s) failed to install.[/red]\n"
                    f"Please check the errors above and install manually:\n"
                    f"[cyan]pip install {' '.join([pkg for pkg, _ in self.failed_packages])}[/cyan]",
                    title="Installation Issues",
                    border_style="red"
                )
                self.console.print(error_panel)
            else:
                success_panel = Panel(
                    "[green]All requirements installed successfully![/green]\n"
                    "You can now run: [cyan]python main.py[/cyan]",
                    title="Setup Complete",
                    border_style="green"
                )
                self.console.print(success_panel)
        else:
            print("\nInstallation Results:")
            print("-" * 40)
            for package in self.installed_packages:
                print(f"✅ {package} - Success")
            for package, error in self.failed_packages:
                print(f"❌ {package} - Failed: {error}")
            
            if self.failed_packages:
                print(f"\nSome package(s) failed.")
                print("Install manually with:")
                print(f"pip install {' '.join([pkg for pkg, _ in self.failed_packages])}")
            else:
                print("\nAll requirements installed successfully!")
                print("Run the game with: python main.py")
    
    def run_setup(self):
        """Run the complete setup process."""
        self.show_title()
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        # Check pip
        if not self.check_pip():
            return False
        
        # Install Rich first if needed
        if not self.install_rich_first():
            self.print("⚠️ Continuing without Rich UI enhancements", style="yellow")
        
        # Get requirements
        requirements = self.get_requirements()
        self.print(f"Found {len(requirements)} requirements to install", style="bright_blue")
        
        # Install requirements
        success = self.install_requirements(requirements)
        
        # Show results
        self.show_results()
        
        return success and len(self.failed_packages) == 0


def main():
    """Main entry point."""
    setup = RequirementsSetup()
    
    try:
        success = setup.run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        setup.print("\nSetup cancelled by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        import traceback
        setup.print(f"\nUnexpected error: {e}", style="red")
        setup.print(f"Full traceback: {traceback.format_exc()}", style="dim red")
        sys.exit(1)


if __name__ == "__main__":
    main()