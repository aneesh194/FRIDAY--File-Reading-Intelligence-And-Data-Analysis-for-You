import os
import sys
import time
import threading
from typing import List, Dict

# Force standard output to use UTF-8 encoding for full emoji/unicode support on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Enable virtual terminal processing (ANSI escape codes) natively on Windows Command Prompt
if os.name == 'nt':
    try:
        os.system('')
    except:
        pass

# Standard species sprites ported from claude-code-main
# Each frame is 4-5 lines tall and 12 chars wide
BODIES: Dict[str, List[List[str]]] = {
    "robot": [
        [
            "   .[||].   ",
            "  [  o  o  ]  ",
            "  [  ====  ]  ",
            "  `--------´  "
        ],
        [
            "   .[||].   ",
            "  [  -  -  ]  ",
            "  [  -==-  ]  ",
            "  `--------´  "
        ],
        [
            "     *      ",
            "   .[||].   ",
            "  [  o  o  ]  ",
            "  [  ====  ]  ",
            "  `--------´  "
        ]
    ],
    "cat": [
        [
            "   /\\_/\\    ",
            "  (  o   o  )  ",
            "  (   ω   )   ",
            "  (\")_(\")   "
        ],
        [
            "   /\\_/\\    ",
            "  (  -   -  )  ",
            "  (   ω   )   ",
            "  (\")_(\")~  "
        ],
        [
            "   /\\_/\\    ",
            "  (  o   o  )  ",
            "  (   •   )   ",
            "  (\")_(\")   "
        ]
    ],
    "duck": [
        [
            "    __      ",
            "  <( o )___  ",
            "   (  ._>   ",
            "    `--´    "
        ],
        [
            "    __      ",
            "  <( - )___  ",
            "   (  ._>   ",
            "    `--´~   "
        ],
        [
            "    __      ",
            "  <( o )___  ",
            "   (  .__>  ",
            "    `--´    "
        ]
    ],
    "chonk": [
        [
            "  /\\    /\\  ",
            " (  o    o  ) ",
            " (   ..   ) ",
            "  `------´  "
        ],
        [
            "  /\\    /|  ",
            " (  -    -  ) ",
            " (   ..   ) ",
            "  `------´  "
        ],
        [
            "  /\\    /\\  ",
            " (  o    o  ) ",
            " (   ..   ) ",
            "  `------´~ "
        ]
    ],
    "crab": [
        [
            "   (\\_._/)   ",
            "  / (o o) \\\\  ",
            " (   -=-   ) ",
            "  `-\"---`-\"  "
        ],
        [
            "   (/_._\\\\)   ",
            "  / (- -) \\\\  ",
            " (   -=-   ) ",
            "  `-\"---`-\"  "
        ],
        [
            "   (\\_._/)   ",
            "  \\\\ (o o) /  ",
            " (   -==-  ) ",
            "  `-\"---`-\"  "
        ]
    ]
}

HAS_CLAWD2 = False
CURRENT_MOOD = "idle"

def set_buddy_mood(mood: str):
    """Sets the active mood for clawd-2 terminal companion."""
    global CURRENT_MOOD
    if mood in ("idle", "thinking", "typing", "happy", "sleeping", "confused"):
        CURRENT_MOOD = mood

def load_clawd2_assets():
    global HAS_CLAWD2
    img_path = r"d:\Project FRIDAY\clawd-2\spritesheet.webp"
    if not os.path.exists(img_path):
        return

    try:
        from PIL import Image
        img = Image.open(img_path).convert("RGBA")
        cell_w, cell_h = 192, 208
        target_w, target_h = 20, 22
        
        mood_specs = {
            "idle": (0, 6),
            "thinking": (4, 5),
            "typing": (6, 6),
            "happy": (7, 6),
            "sleeping": (5, 8),
            "confused": (8, 6)
        }
        
        for mood, (row, num_frames) in mood_specs.items():
            mood_frames = []
            for col in range(num_frames):
                x_start = col * cell_w
                y_start = row * cell_h
                frame = img.crop((x_start, y_start, x_start + cell_w, y_start + cell_h))
                resized = frame.resize((target_w, target_h), Image.Resampling.NEAREST)
                
                pixels = resized.load()
                ansi_frame = []
                for y in range(0, target_h, 2):
                    line_parts = []
                    for x in range(target_w):
                        r1, g1, b1, a1 = pixels[x, y]
                        if y + 1 < target_h:
                            r2, g2, b2, a2 = pixels[x, y + 1]
                        else:
                            r2, g2, b2, a2 = 0, 0, 0, 0
                            
                        t_visible = (a1 >= 128)
                        b_visible = (a2 >= 128)
                        
                        if t_visible and b_visible:
                            line_parts.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀\033[0m")
                        elif t_visible:
                            line_parts.append(f"\033[38;2;{r1};{g1};{b1}m▀\033[0m")
                        elif b_visible:
                            line_parts.append(f"\033[38;2;{r2};{g2};{b2}m▄\033[0m")
                        else:
                            line_parts.append(" ")
                    ansi_frame.append("".join(line_parts))
                mood_frames.append(ansi_frame)
            
            BODIES[f"clawd-2_{mood}"] = mood_frames
        
        HAS_CLAWD2 = True
    except Exception as e:
        pass

# Load clawd-2 assets immediately on import
load_clawd2_assets()

HAT_LINES = {
    "none": "",
    "crown": "   \\^^^/    ",
    "tophat": "   [___]    ",
    "wizard": "    /^\\     "
}

def render_buddy_frame(species: str, frame_idx: int, hat: str = "none") -> List[str]:
    """Compiles a single frame lines for the given species buddy."""
    if species == "clawd-2" or (species == "crab" and HAS_CLAWD2):
        mood_key = f"clawd-2_{CURRENT_MOOD}"
        frames = BODIES.get(mood_key, BODIES.get("clawd-2_idle", BODIES["crab"]))
    else:
        frames = BODIES.get(species, BODIES["crab"])
        
    body = list(frames[frame_idx % len(frames)])
    
    # Prepend hat if specified (only for ASCII species as Clawd-2 doesn't need hats)
    if species != "clawd-2" and hat != "none" and hat in HAT_LINES:
        hat_line = HAT_LINES[hat]
        return [hat_line] + body
    return body

class BuddyAnimator:
    """Handles ambient thread-safe terminal ASCII/ANSI buddy animations."""
    def __init__(self, species: str = "crab", hat: str = "none"):
        if species == "crab" and HAS_CLAWD2:
            species = "clawd-2"
        self.species = species
        self.hat = hat
        self.stop_event = threading.Event()
        self.thread = None

    def _animate(self, status_text: str):
        frame_idx = 0
        first_render = True
        # Bounce sequence for "thinking" mood — pet jumps up and down
        bounce_seq = [0, 0, 1, 2, 2, 1, 0, 0]
        max_bounce = 2

        # Pre-calculate fixed block height so cursor movement is always consistent
        sample_lines = render_buddy_frame(self.species, 0, self.hat)
        use_bounce = (CURRENT_MOOD == "thinking")
        if use_bounce:
            block_height = 1 + max_bounce + len(sample_lines) + 1
        else:
            block_height = len(sample_lines) + 2

        while not self.stop_event.is_set():
            lines = render_buddy_frame(self.species, frame_idx, self.hat)
            
            # Build the entire block of text to write
            block = []
            if self.species == "clawd-2":
                block.append(f"[FRIDAY Companion] (State: {CURRENT_MOOD.upper()})")
            else:
                block.append(f"[FRIDAY Companion] (State: ACTIVE)")

            if use_bounce:
                bounce = bounce_seq[frame_idx % len(bounce_seq)]
                # Empty lines above pet (pet jumps UP = fewer lines above)
                for _ in range(max_bounce - bounce):
                    block.append("")
                for line in lines:
                    block.append(f"  {line}")
                # Fill remaining bounce padding at bottom
                for _ in range(bounce):
                    block.append("")
            else:
                for line in lines:
                    block.append(f"  {line}")

            block.append(f"  💡 FRIDAY: {status_text}...")
            
            # Clear lines and write them
            output_str = ""
            if not first_render:
                # Move cursor back to the top of the block
                output_str += f"\033[{block_height}A"
            else:
                first_render = False
                
            for l in block:
                output_str += f"\033[K{l}\n"
                
            sys.stdout.write(output_str)
            sys.stdout.flush()
            
            frame_idx += 1
            # Sleep in small steps to react to stop event quickly
            for _ in range(3):
                if self.stop_event.is_set():
                    break
                time.sleep(0.05)
                
        # On stop, clear the printed block
        clear_str = f"\033[{block_height}A"
        for _ in range(block_height):
            clear_str += "\033[K\n"
        clear_str += f"\033[{block_height}A"
        sys.stdout.write(clear_str)
        sys.stdout.flush()

    def start(self, status_text: str = "Computing answers"):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._animate, args=(status_text,), daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=2.0)
            self.thread = None

def welcome_buddy_animation(species: str = "crab", hat: str = "none"):
    """Plays a quick startup animation for FRIDAY's terminal companion."""
    if species == "crab" and HAS_CLAWD2:
        species = "clawd-2"
        
    if species == "clawd-2":
        set_buddy_mood("happy")
        frames = BODIES.get("clawd-2_happy", BODIES["crab"])
    else:
        frames = BODIES.get(species, BODIES["crab"])
    
    first_render = True
    for f in range(len(frames) * 2):
        lines = render_buddy_frame(species, f, hat)
        
        block = []
        block.append(f"[FRIDAY Companion] (State: STARTING)")
        for line in lines:
            block.append(f"  {line}")
        block.append("  Companion status: ONLINE")
        
        output_str = ""
        if not first_render:
            output_str += f"\033[{len(block)}A"
        else:
            first_render = False
            
        for l in block:
            output_str += f"\033[K{l}\n"
            
        sys.stdout.write(output_str)
        sys.stdout.flush()
        time.sleep(0.15)
        
    set_buddy_mood("idle")

