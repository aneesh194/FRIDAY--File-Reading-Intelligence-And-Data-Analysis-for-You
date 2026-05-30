"""
FRIDAY AI — Clawd-2 Animated Desktop Companion
================================================
Renders the real pixel-art clawd-2 pet from its spritesheet.webp as a
floating, draggable, borderless Tkinter window.  Listens on TCP 19872
for status JSON payloads from FRIDAY AI and transitions animations live.

Spritesheet spec  (from codex-pet.com/pets/clawd-2):
  Frame cell: 192 × 208 px   |   Grid: 8 cols × 9 rows
  Row 0  Idle        6 frames  1100 ms
  Row 1  Run Right   8 frames  1060 ms
  Row 2  Run Left    8 frames  1060 ms
  Row 3  Waving      4 frames   700 ms
  Row 4  Jumping     5 frames   840 ms
  Row 5  Failed      8 frames  1220 ms
  Row 6  Waiting     6 frames  1010 ms
  Row 7  Running     6 frames   820 ms  (typing on laptop)
  Row 8  Review      6 frames  1030 ms
"""

import tkinter as tk
import os
import sys
import json
import socket
import threading
import time

from PIL import Image, ImageTk

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITESHEET = os.path.join(SCRIPT_DIR, "clawd-2", "spritesheet.webp")

# ── Sprite Grid Constants ────────────────────────────────────────────────────
CELL_W = 192
CELL_H = 208
COLS   = 8

# Scale factor — how much to enlarge the pixel art (nearest-neighbor)
SCALE  = 2

# ── Animation State Definitions ──────────────────────────────────────────────
# Each entry: (row, num_frames, total_duration_ms)
ANIM_STATES = {
    "idle":      (0, 6, 1100),
    "run_right": (1, 8, 1060),
    "run_left":  (2, 8, 1060),
    "waving":    (3, 4,  700),
    "jumping":   (4, 5,  840),
    "failed":    (5, 8, 1220),
    "waiting":   (6, 6, 1010),
    "running":   (7, 6,  820),
    "review":    (8, 6, 1030),
}

# Map FRIDAY AI status keywords → clawd-2 animation state
FRIDAY_STATUS_MAP = {
    "idle":      "idle",
    "thinking":  "review",
    "working_1": "running",
    "confused":  "failed",
    "happy":     "jumping",
    "sleeping":  "waiting",
    "waving":    "waving",
    "greeting":  "waving",
}

TCP_PORT = 19872


class ClawdCompanion:
    """Real pixel-art animated desktop companion powered by clawd-2 spritesheet."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Clawd — FRIDAY Companion")

        # ── Window Chrome ────────────────────────────────────────────────
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="#0e0e14")

        # Try to set window transparency (works on Win10+)
        try:
            self.root.wm_attributes("-transparentcolor", "#0e0e14")
        except Exception:
            pass

        # Position: bottom-right of screen
        disp_w = CELL_W * SCALE + 16
        disp_h = CELL_H * SCALE + 60
        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        x = scr_w - disp_w - 20
        y = scr_h - disp_h - 60
        self.root.geometry(f"{disp_w}x{disp_h}+{x}+{y}")

        # ── UI Layout ────────────────────────────────────────────────────
        self.container = tk.Frame(self.root, bg="#12121c", bd=0)
        self.container.pack(fill="both", expand=True)

        # Title bar / drag handle
        self.hud = tk.Label(
            self.container,
            text="🦀 CLAWD · IDLE",
            font=("Consolas", 9, "bold"),
            bg="#1a1a2e",
            fg="#ff8844",
            bd=0, pady=4,
            cursor="fleur"
        )
        self.hud.pack(fill="x")

        # Canvas for the sprite
        self.canvas = tk.Canvas(
            self.container,
            width=CELL_W * SCALE,
            height=CELL_H * SCALE,
            bg="#0e0e14",
            highlightthickness=0
        )
        self.canvas.pack(padx=4, pady=4)

        # Status bar
        self.status_bar = tk.Label(
            self.container,
            text="FRIDAY AI Companion · Online",
            font=("Consolas", 8),
            bg="#161622",
            fg="#6a6a8a",
            pady=2
        )
        self.status_bar.pack(fill="x")

        # ── Drag Bindings ────────────────────────────────────────────────
        for w in (self.hud, self.canvas, self.container):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

        # ── Right-Click Menu ─────────────────────────────────────────────
        self.menu = tk.Menu(
            self.root, tearoff=0,
            bg="#1e1e30", fg="#ffffff",
            activebackground="#3a3a5a"
        )
        self.menu.add_command(label="Toggle Pin on Top", command=self._toggle_pin)
        self.menu.add_separator()
        # Add animation state sub-menu for manual testing
        anim_menu = tk.Menu(self.menu, tearoff=0, bg="#1e1e30", fg="#ffffff",
                            activebackground="#3a3a5a")
        for state_name in ANIM_STATES:
            anim_menu.add_command(
                label=state_name.replace("_", " ").title(),
                command=lambda s=state_name: self._set_state(s)
            )
        self.menu.add_cascade(label="Set Animation", menu=anim_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Exit Companion", command=self.root.destroy)

        for w in (self.root, self.container, self.canvas, self.hud, self.status_bar):
            w.bind("<Button-3>", self._popup_menu)

        # ── Load Spritesheet ─────────────────────────────────────────────
        self.all_frames = {}   # state_name → list[ImageTk.PhotoImage]
        self._load_spritesheet()

        # ── Animation State ──────────────────────────────────────────────
        self.current_state = "idle"
        self.frame_idx = 0
        self.after_id = None
        self._running = True
        self._tick_interval = 180
        self.canvas_img_id = None

        # Start idle animation
        self._play_state("idle")

        # ── TCP Listener ─────────────────────────────────────────────────
        self._start_tcp()

    # ═══════════════════════════════════════════════════════════════════════
    #  Spritesheet Loader
    # ═══════════════════════════════════════════════════════════════════════
    def _load_spritesheet(self):
        if not os.path.exists(SPRITESHEET):
            self.status_bar.config(text="ERROR: spritesheet.webp not found!")
            return

        sheet = Image.open(SPRITESHEET).convert("RGBA")

        for state_name, (row, num_frames, _dur) in ANIM_STATES.items():
            frames = []
            for col in range(num_frames):
                x0 = col * CELL_W
                y0 = row * CELL_H
                cell = sheet.crop((x0, y0, x0 + CELL_W, y0 + CELL_H))

                # Scale up with nearest-neighbor to preserve pixel art crispness
                scaled = cell.resize(
                    (CELL_W * SCALE, CELL_H * SCALE),
                    Image.Resampling.NEAREST
                )
                frames.append(ImageTk.PhotoImage(scaled))

            self.all_frames[state_name] = frames

    # ═══════════════════════════════════════════════════════════════════════
    #  Animation Player
    # ═══════════════════════════════════════════════════════════════════════
    def _play_state(self, state_name: str):
        if state_name not in ANIM_STATES or state_name not in self.all_frames:
            state_name = "idle"

        self.current_state = state_name
        self.frame_idx = 0

        _row, num_frames, total_dur = ANIM_STATES[state_name]
        self._tick_interval = max(total_dur // num_frames, 30)

        # Update HUD text
        display_name = state_name.replace("_", " ").upper()
        self.hud.config(text=f"🦀 CLAWD · {display_name}")

        # Cancel any previous animation loop
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except (tk.TclError, ValueError):
                pass
            self.after_id = None

        self._tick()

    def _tick(self):
        if not self._running:
            return
        try:
            frames = self.all_frames.get(self.current_state, [])
            if not frames:
                return

            photo = frames[self.frame_idx % len(frames)]

            if self.canvas_img_id is None:
                self.canvas_img_id = self.canvas.create_image(
                    CELL_W * SCALE // 2,
                    CELL_H * SCALE // 2,
                    image=photo,
                    anchor="center"
                )
            else:
                self.canvas.itemconfig(self.canvas_img_id, image=photo)

            # Keep a reference so Tk doesn't garbage-collect the image
            self.canvas._current_photo = photo

            self.frame_idx = (self.frame_idx + 1) % len(frames)
            self.after_id = self.root.after(self._tick_interval, self._tick)
        except tk.TclError:
            # Window was destroyed
            pass

    def _set_state(self, state_name: str):
        """Switch animation state (from menu or TCP)."""
        if state_name == self.current_state:
            return
        self._play_state(state_name)

    # ═══════════════════════════════════════════════════════════════════════
    #  Drag Logic
    # ═══════════════════════════════════════════════════════════════════════
    def _drag_start(self, event):
        self._dx = event.x
        self._dy = event.y

    def _drag_move(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    # ═══════════════════════════════════════════════════════════════════════
    #  Context Menu
    # ═══════════════════════════════════════════════════════════════════════
    def _popup_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def _toggle_pin(self):
        current = self.root.wm_attributes("-topmost")
        self.root.wm_attributes("-topmost", not current)

    # ═══════════════════════════════════════════════════════════════════════
    #  TCP Listener (receives status from FRIDAY AI main.py)
    # ═══════════════════════════════════════════════════════════════════════
    def _start_tcp(self):
        def _listen():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                srv.bind(("127.0.0.1", TCP_PORT))
                srv.listen(5)
            except Exception as e:
                print(f"[Clawd Companion] TCP bind failed on port {TCP_PORT}: {e}")
                return

            while True:
                try:
                    conn, _ = srv.accept()
                    raw = conn.recv(4096).decode("utf-8", errors="replace")
                    conn.close()
                    if not raw:
                        continue

                    for line in raw.strip().split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                            action = payload.get("action")
                            if action == "set_status":
                                friday_status = payload.get("status", "idle")
                                # Map FRIDAY status → clawd-2 animation state
                                anim_state = FRIDAY_STATUS_MAP.get(
                                    friday_status, "idle"
                                )
                                # Schedule state change on main thread
                                def _apply(s=anim_state, fs=friday_status):
                                    try:
                                        self._set_state(s)
                                        self.status_bar.config(
                                            text=f"FRIDAY status: {fs.upper()}"
                                        )
                                    except tk.TclError:
                                        pass
                                self.root.after(0, _apply)
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass

        t = threading.Thread(target=_listen, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    app = ClawdCompanion(root)
    root.mainloop()


if __name__ == "__main__":
    main()
