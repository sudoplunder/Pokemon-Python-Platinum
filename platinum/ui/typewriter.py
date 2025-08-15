import sys, time

SPEED_MAP = {1: 0.0, 2: 0.01, 3: 0.03}

def type_out(text: str, speed_setting: int = 2):
    delay = SPEED_MAP.get(speed_setting, 0.01)
    if delay <= 0:
        print(text)
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()