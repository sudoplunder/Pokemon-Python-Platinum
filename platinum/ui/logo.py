"""
Logo / branding utilities (with backward compatibility shim).

Provides:
- POKEMON_ASCII: Multi-line raw ASCII art for the Pokémon banner.
- colored_logo(): Return logo optionally colored.
- print_logo(): Print logo (auto color if TTY).
- show_logo(): Backwards-compatible alias for earlier code expecting this name.
"""

POKEMON_ASCII = r"""
                                  ,'
    _.----.        ____         ,'  _\   ___    ___     ____
_,-'       `.     |    |  /`.   \,-'    |   \  /   |   |    \  |`.
\      __    \    '-.  | /   `.  ___    |    \/    |   '-.   \ |  |
 \.    \ \   |  __  |  |/    ,','_  `.  |          | __  |    \|  |
   \    \/   /,' _`.|      ,' / / / /   |          ,' _`.|     |  |
    \     ,-'/  /   \    ,'   | \/ / ,`.|         /  /   \  |     |
     \    \ |   \_/  |   `-.  \    `'  /|  |    ||   \_/  | |\    |
      \    \ \      /       `-.`.___,-' |  |\  /| \      /  | |   |
       \    \ `.__,'|  |`-._    `|      |__| \/ |  `.__,'|  | |   |
        \_.-'       |__|    `-._ |              '-.|     '-.| |   |
                                `'                            '-._|
"""

def colored_logo(yellow: bool = True) -> str:
    """Return the ASCII logo, optionally wrapped in ANSI yellow."""
    if not yellow:
        return POKEMON_ASCII
    return f"\033[33m{POKEMON_ASCII}\033[0m"

def print_logo(force_color: bool | None = None):
    """
    Print the logo, disabling color if stdout not a TTY unless forced.
    force_color: True always color, False never color, None auto-detect.
    """
    import sys
    use_color = sys.stdout.isatty() if force_color is None else force_color
    print(colored_logo(use_color))

# Backwards compatibility for older code expecting show_logo()
def show_logo():
    print_logo()