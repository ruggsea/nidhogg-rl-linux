"""nav3.py — closed-loop menu navigation that KNOWS which row is selected.

Why the earlier attempts failed: the main menu scrolls UNDER A FIXED HIGHLIGHT BAR. The bar is always
at the same screen position (measured: image y 836-886 in a 1920-wide capture, content y ~413), so
the highlighted row cannot be inferred from any coordinate - only from the TEXT under the bar. That is
also why blind key sequences kept landing in OPTIONS and cycling the language to French and Chinese.

Method:
  * capture the game window (screencapture -l <window id>),
  * crop the highlight band,
  * compare it pixel-wise against a reference crop of the item we want,
  * press S to scroll until the wanted item is under the bar, then Enter.

The reference crops were captured from screenshots whose content was verified by eye, so this is a
sequence of stimuli with a checked response, not a guess.
"""
import subprocess
import sys
import time

import train_state as TS

BAND_TOP_FRAC = 836 / 1256.0     # measured on a 1920x1256 capture of a 960x628 window
BAND_BOT_FRAC = 886 / 1256.0
BAND_X0_FRAC = 0.30
BAND_X1_FRAC = 0.70
K_ENTER, K_S, K_ESC, K_UP = 13, 83, 27, 38


def window_id():
    out = subprocess.run(["/tmp/winid"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "960x628":
            return parts[0]
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and "x" in parts[1]:
            w, h = parts[1].split("x")
            if int(w) > 300 and int(h) > 200:
                return parts[0]
    return None


def capture(path):
    wid = window_id()
    if not wid:
        return False
    subprocess.run(["screencapture", "-x", "-o", "-l", wid, path], capture_output=True)
    return True


def find_band_rgb(im):
    """Locate the highlight bar by scanning a column for the menu's grey band (value 20-45).

    Fixed fractions were wrong: the bar only exists while a menu is actually open, and the capture
    size depends on the window. Detecting it dynamically also tells us "no menu is open", which is a
    state the navigation has to act on rather than silently compare against.
    """
    W, H = im.size
    x = int(W * BAND_X0_FRAC)
    start = None
    for y in range(H):
        v = im.getpixel((x, y))[0]
        inside = 20 <= v <= 45
        if inside and start is None:
            start = y
        elif not inside and start is not None:
            if y - start > 20:
                return (start, y - 1)
            start = None
    return None


def band(path="/tmp/_band.png"):
    """Grey-scale crop of the highlight bar, or None when no menu is open."""
    from PIL import Image
    if not capture(path):
        return None
    im = Image.open(path).convert("RGB")
    rng = find_band_rgb(im)
    if rng is None:
        return None
    top, bot = rng
    W, _ = im.size
    return im.convert("L").crop((int(W * BAND_X0_FRAC), top + 4, int(W * BAND_X1_FRAC), bot - 4))


def band_diff(a, b):
    from PIL import ImageChops
    if a.size != b.size:
        b = b.resize(a.size)
    d = ImageChops.difference(a, b)
    px = list(d.get_flattened_data()) if hasattr(d, "get_flattened_data") else list(d.getdata())
    return sum(px) / len(px)


def press(mgr, code, wait=1.2):
    mgr.press(code)
    time.sleep(wait)


def scroll_until(mgr, reference, label, tries=8, threshold=12.0, log=print):
    """Press S until the band matches `reference`; return True when it does."""
    opened = 0
    for i in range(tries):
        cur = band()
        if cur is None:
            # No menu open: this is the title/splash. Open the menu and retry rather than comparing
            # against a bar that does not exist.
            if opened < 3:
                opened += 1
                log(f"   no menu bar visible - pressing Enter to open the menu ({opened})")
                press(mgr, K_ENTER, 2.0)
                continue
            log("   no menu appeared")
            return False
        d = band_diff(cur, reference)
        log(f"   try {i}: diff vs {label} = {d:.1f}")
        if d <= threshold:
            log(f"   {label} is under the highlight bar")
            return True
        cur.save(f"/tmp/_band_try{i}.png")
        press(mgr, K_S, 1.1)
    return False


def main():
    mgr = TS.InstanceManager(iid=0)
    log = print
    from PIL import Image
    ref_sp = Image.open("/tmp/band_singleplayer.png").convert("L")
    log(f"window id: {window_id()}")
    if not scroll_until(mgr, ref_sp, "SINGLE PLAYER", log=log):
        log("FAIL: never scrolled SINGLE PLAYER under the bar")
        return 1
    press(mgr, K_ENTER, 2.4)
    log(f"after Enter: room={mgr.room()} {mgr.room_name(mgr.room())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
