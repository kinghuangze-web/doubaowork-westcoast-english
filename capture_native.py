"""Capture the Doubao Work window without activating it or capturing overlays."""
from __future__ import annotations

import ctypes

from PIL import Image
import win32gui
import win32ui


def enable_dpi_awareness():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (OSError, AttributeError):
        pass


def find_window():
    matches = []
    def visit(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if title == '豆包工作' and win32gui.IsWindowVisible(hwnd):
            matches.append(hwnd)
    win32gui.EnumWindows(visit, None)
    return matches[0] if matches else None


def capture(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right-left, bottom-top
    if width <= 0 or height <= 0:
        return None, None
    window_dc = win32gui.GetWindowDC(hwnd)
    source_dc = win32ui.CreateDCFromHandle(window_dc)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source_dc, width, height)
    memory_dc.SelectObject(bitmap)
    try:
        ok = ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 2)
        if not ok:
            return None, None
        info = bitmap.GetInfo()
        pixels = bitmap.GetBitmapBits(True)
        image = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), pixels,
                                 'raw', 'BGRX', 0, 1).copy()
        return image, (left, top, width, height)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        memory_dc.DeleteDC()
        source_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)


if __name__ == '__main__':
    enable_dpi_awareness()
    handle = find_window()
    if not handle:
        raise SystemExit('Doubao Work window not found')
    image, rect = capture(handle)
    if image is None:
        raise SystemExit('PrintWindow failed')
    image.save('native-capture.png')
    print(rect, image.size)
