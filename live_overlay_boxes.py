"""Small click-through text patches over the Doubao Work client."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import queue
import threading
import tkinter as tk

from PIL import Image, ImageTk
from rapidocr import RapidOCR
import win32con
import win32gui

from capture_native import capture, enable_dpi_awareness, find_window
from overlay_preview import translate_screenshot


def is_app_front(hwnd):
    front = win32gui.GetForegroundWindow()
    return front == hwnd or win32gui.GetAncestor(front, win32con.GA_ROOT) == hwnd


def worker(target, terms, output, stop):
    engine = RapidOCR()
    last_hash = None
    last_thumbnail = None
    while not stop.is_set():
        try:
            if win32gui.IsWindow(target) and not win32gui.IsIconic(target):
                image, rect = capture(target)
                if image is not None:
                    digest = hashlib.blake2b(image.tobytes(), digest_size=16).digest()
                    if digest != last_hash:
                        thumbnail = image.resize((64, 40)).convert('RGB').tobytes()
                        if last_thumbnail is not None:
                            pixels_changed = sum(
                                abs(thumbnail[i]-last_thumbnail[i]) > 35 or
                                abs(thumbnail[i+1]-last_thumbnail[i+1]) > 35 or
                                abs(thumbnail[i+2]-last_thumbnail[i+2]) > 35
                                for i in range(0, len(thumbnail), 3)
                            )
                            if pixels_changed > 64*40*.13:
                                if output.full():
                                    output.get_nowait()
                                output.put((rect, []))
                        overlay, matched = translate_screenshot(image, terms, engine)
                        composite = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
                        patches = []
                        for item in matched:
                            x1, y1, x2, y2 = item['patch_rect']
                            patch = composite.crop((x1, y1, x2+1, y2+1))
                            key = (item['source'], round(x1/20), round(y1/20))
                            patches.append((key, (x1, y1), patch))
                        last_hash = digest
                        last_thumbnail = thumbnail
                        if output.full():
                            output.get_nowait()
                        output.put((rect, patches))
        except Exception as error:
            print(f'Layer error: {error}', flush=True)
        stop.wait(1.2)


def set_click_through(toplevel):
    toplevel.update_idletasks()
    hwnd = win32gui.GetAncestor(toplevel.winfo_id(), win32con.GA_ROOT)
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT |
                           win32con.WS_EX_NOACTIVATE | win32con.WS_EX_TOOLWINDOW)
    return hwnd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terms', type=pathlib.Path, default=pathlib.Path(__file__).with_name('overlay_terms.json'))
    parser.add_argument('--always-visible', action='store_true', help='Development only')
    args = parser.parse_args()
    enable_dpi_awareness()
    terms = json.loads(args.terms.read_text(encoding='utf-8'))
    target = find_window()
    if target is None:
        raise SystemExit('Open Doubao Work before starting the English layer.')
    root = tk.Tk()
    root.withdraw()
    updates = queue.Queue(maxsize=1)
    stop = threading.Event()
    threading.Thread(target=worker, args=(target, terms, updates, stop), daemon=True).start()
    windows = {}
    patches = {}

    def tick():
        nonlocal patches
        try:
            while True:
                rect, next_patches = updates.get_nowait()
                patches = {key: (offset, image) for key, offset, image in next_patches}
                for key in list(windows):
                    if key not in patches:
                        windows.pop(key)[0].destroy()
                for key, (offset, image) in patches.items():
                    if key not in windows:
                        top = tk.Toplevel(root)
                        top.overrideredirect(True)
                        top.attributes('-topmost', True)
                        label = tk.Label(top, borderwidth=0, highlightthickness=0)
                        label.pack(fill='both', expand=True)
                        set_click_through(top)
                        windows[key] = (top, label, None)
                    top, label, _ = windows[key]
                    photo = ImageTk.PhotoImage(image)
                    label.configure(image=photo)
                    windows[key] = (top, label, photo)
                print(f'UI phrases translated: {len(patches)}', flush=True)
        except queue.Empty:
            pass
        if not win32gui.IsWindow(target):
            root.destroy()
            return
        show = args.always_visible or (not win32gui.IsIconic(target) and is_app_front(target))
        if show:
            left, top_y, _, _ = win32gui.GetWindowRect(target)
            for key, (offset, image) in patches.items():
                top, _, _ = windows[key]
                x, y = offset
                top.geometry(f'{image.width}x{image.height}+{left+x}+{top_y+y}')
                top.deiconify()
                top.lift()
        else:
            for top, _, _ in windows.values():
                top.withdraw()
        root.after(200, tick)

    try:
        tick()
        root.mainloop()
    finally:
        stop.set()


if __name__ == '__main__':
    main()
