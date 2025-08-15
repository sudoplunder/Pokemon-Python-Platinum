"""
ASCII logo display with coloring.
"""


def get_pokemon_logo():
    """Return ASCII art Pokémon logo."""
    return """
    ██████╗  ██████╗ ██╗  ██╗███████╗███╗   ███╗ ██████╗ ███╗   ██╗
    ██╔══██╗██╔═══██╗██║ ██╔╝██╔════╝████╗ ████║██╔═══██╗████╗  ██║
    ██████╔╝██║   ██║█████╔╝ █████╗  ██╔████╔██║██║   ██║██╔██╗ ██║
    ██╔═══╝ ██║   ██║██╔═██╗ ██╔══╝  ██║╚██╔╝██║██║   ██║██║╚██╗██║
    ██║     ╚██████╔╝██║  ██╗███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
    """


def get_platinum_logo():
    """Return ASCII art Platinum logo."""
    return """
    ██████╗ ██╗      █████╗ ████████╗██╗███╗   ██╗██╗   ██╗███╗   ███╗
    ██╔══██╗██║     ██╔══██╗╚══██╔══╝██║████╗  ██║██║   ██║████╗ ████║
    ██████╔╝██║     ███████║   ██║   ██║██╔██╗ ██║██║   ██║██╔████╔██║
    ██╔═══╝ ██║     ██╔══██║   ██║   ██║██║╚██╗██║██║   ██║██║╚██╔╝██║
    ██║     ███████╗██║  ██║   ██║   ██║██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
    """


def show_colored_logo():
    """Display the full colored Pokémon Platinum logo."""
    try:
        # Try to use colorama for cross-platform color support
        from colorama import Fore, Style, init
        init()
        
        pokemon_logo = get_pokemon_logo()
        platinum_logo = get_platinum_logo()
        
        print(Fore.YELLOW + pokemon_logo + Style.RESET_ALL)
        print(Fore.CYAN + platinum_logo + Style.RESET_ALL)
        print(Fore.WHITE + "                     Python Edition" + Style.RESET_ALL)
        
    except ImportError:
        # Fallback to plain text if colorama not available
        print(get_pokemon_logo())
        print(get_platinum_logo())
        print("                     Python Edition")


def show_simple_title():
    """Display a simple text title for minimal environments."""
    print("=" * 60)
    print("          POKÉMON PLATINUM - PYTHON EDITION")
    print("=" * 60)