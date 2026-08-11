import atexit
import ctypes
from ctypes import wintypes

import customtkinter as ctk
import psutil
import win32con
import win32gui
import win32process

DWMWA_CLOAKED = 14

dwmapi = ctypes.WinDLL("dwmapi")
dwm_get_window_attribute = dwmapi.DwmGetWindowAttribute
dwm_get_window_attribute.argtypes = (
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
)
dwm_get_window_attribute.restype = ctypes.c_long


class WindowLocker(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Window Locker")
        self.geometry("300x400")
        self.locked_windows = set()
        atexit.register(self.unlock_all_windows)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True)
        self.reload_button = ctk.CTkButton(self, text="reload", command=self.get_windows)
        self.reload_button.pack(pady=5, padx=10)
        self.get_windows()

    def get_windows(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        apps = {}

        def enum_cb(hwnd, _results):
            if not win32gui.IsWindowVisible(hwnd):
                return
            is_cloaked = ctypes.c_int(0)
            result = dwm_get_window_attribute(
                hwnd,
                DWMWA_CLOAKED,
                ctypes.byref(is_cloaked),
                ctypes.sizeof(is_cloaked),
            )
            if result == 0 and is_cloaked.value:
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            hwnd_owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                return
            if hwnd_owner != 0 and not (ex_style & win32con.WS_EX_APPWINDOW):
                return
            class_name = win32gui.GetClassName(hwnd)
            if class_name in ("Progman", "WorkerW"):
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process_name = psutil.Process(pid).name().lower()
                apps.setdefault(process_name, []).append(hwnd)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        win32gui.EnumWindows(enum_cb, None)

        for exe_name, hwnds in apps.items():
            display_name = exe_name.replace(".exe", "").capitalize()
            switch_var = ctk.BooleanVar(value=all(hwnd in self.locked_windows for hwnd in hwnds))
            switch = ctk.CTkSwitch(
                self.main_frame,
                text=display_name,
                variable=switch_var,
                onvalue=True,
                offvalue=False,
                command=lambda h=hwnds, v=switch_var: self.lock_windows(h, v.get()),
            )
            switch.pack(pady=5, padx=10, anchor="w")

    def lock_windows(self, hwnds, state):
        z_order = win32con.HWND_TOPMOST if state else win32con.HWND_NOTOPMOST
        for hwnd in hwnds:
            try:
                win32gui.SetWindowPos(
                    hwnd,
                    z_order,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                )
            except win32gui.error:
                self.locked_windows.discard(hwnd)
            else:
                if state:
                    self.locked_windows.add(hwnd)
                else:
                    self.locked_windows.discard(hwnd)

    def unlock_all_windows(self):
        self.lock_windows(tuple(self.locked_windows), False)

    def on_close(self):
        self.unlock_all_windows()
        self.destroy()


if __name__ == "__main__":
    WindowLocker().mainloop()
