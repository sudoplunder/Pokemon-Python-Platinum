import sys, time, os

__all__ = ["type_out", "clear_screen", "wait_for_continue"]

# Non-zero delays so even fastest speed animates left-to-right
# 1 = fast, 2 = normal, 3 = slow
SPEED_MAP = {1: 0.004, 2: 0.012, 3: 0.02}

def type_out(text: str, speed_setting: int = 2):
    delay = SPEED_MAP.get(speed_setting, 0.01)
    # Guarantee a tiny delay for animation unless explicitly overridden by env
    if delay <= 0:
        delay = 0.004
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def clear_screen():
    # Avoid clearing during automated tests
    if os.getenv('PYTEST_CURRENT_TEST'):
        return
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def wait_for_continue(prompt: str = "Press Enter to continue...", debug: bool = False):
    if os.getenv('PYTEST_CURRENT_TEST'):
        return
    try:
        input(prompt)
    except EOFError:
        if debug:
            print("[skip wait]")