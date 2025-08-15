"""
Logo / branding utilities.

Provides:
- POKEMON_ASCII: Multi-line raw ASCII art for the Pokémon banner.
- colored_logo(): Optionally wraps the ASCII art in ANSI yellow.
- print_logo(): Convenience print with auto color disable on unsupported terminals.
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
    """
    Return the ASCII logo, optionally wrapped in ANSI yellow.
    """
    if not yellow:
        return POKEMON_ASCII
    return f"\033[33m{POKEMON_ASCII}\033[0m"

def print_logo(force_color: bool | None = None):
    """
    Print the logo, auto-disabling color if stdout is not a TTY unless forced.

    force_color:
      True  -> always color
      False -> never color
      None  -> auto (color only if terminal likely supports ANSI)
    """
    import sys
    use_color = True
    if force_color is None:
        use_color = sys.stdout.isatty()
    else:
        use_color = force_color
    print(colored_logo(use_color))