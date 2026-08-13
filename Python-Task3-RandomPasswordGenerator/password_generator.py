"""
Random Password Generator - Advanced Tier
GUI password generator with complexity controls, strength meter,
clipboard integration, and session history.
"""

import secrets
import string
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

AMBIGUOUS_CHARS = "0Ol1I|"
MIN_LENGTH = 8
MAX_LENGTH = 64
HISTORY_LIMIT = 5

COLORS = {
    "bg": "#12131a",
    "card": "#1b1d29",
    "card_alt": "#242637",
    "border": "#2f3142",
    "text": "#e9e9f2",
    "muted": "#8d8fa3",
    "accent": "#6c63ff",
    "accent_hover": "#7d75ff",
    "accent_pressed": "#5a52e0",
    "danger": "#ef4444",
    "warning": "#f5a623",
    "success": "#22c55e",
}


class PasswordGenerator:
    """Handles secure password generation logic (no UI concerns)."""

    def __init__(self):
        self.uppercase = string.ascii_uppercase
        self.lowercase = string.ascii_lowercase
        self.digits = string.digits
        self.symbols = "!@#$%^&*()-_=+[]{};:,.<>?/"

    def _pool_for(self, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous):
        pools = []
        if use_upper:
            pools.append(self._strip_ambiguous(self.uppercase, exclude_ambiguous))
        if use_lower:
            pools.append(self._strip_ambiguous(self.lowercase, exclude_ambiguous))
        if use_digits:
            pools.append(self._strip_ambiguous(self.digits, exclude_ambiguous))
        if use_symbols:
            pools.append(self._strip_ambiguous(self.symbols, exclude_ambiguous))
        return pools

    @staticmethod
    def _strip_ambiguous(charset, exclude_ambiguous):
        if not exclude_ambiguous:
            return charset
        return "".join(c for c in charset if c not in AMBIGUOUS_CHARS)

    def generate(self, length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous):
        """Generate a cryptographically secure password matching the given criteria.

        Raises ValueError on invalid input (short length, too few character types,
        or a character type selected that becomes empty after ambiguous exclusion).
        """
        if length < MIN_LENGTH:
            raise ValueError(f"Password length must be at least {MIN_LENGTH} characters.")

        selected_count = sum([use_upper, use_lower, use_digits, use_symbols])
        if selected_count < 2:
            raise ValueError("Select at least 2 character types.")

        pools = self._pool_for(use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous)
        if any(len(pool) == 0 for pool in pools):
            raise ValueError("A selected character type has no usable characters left "
                              "(try disabling 'exclude ambiguous').")

        # Guarantee at least one character from each selected pool.
        required_chars = [secrets.choice(pool) for pool in pools]

        combined_pool = "".join(pools)
        remaining = length - len(required_chars)
        password_chars = required_chars + [secrets.choice(combined_pool) for _ in range(remaining)]

        # Shuffle securely so the guaranteed characters aren't always at the front.
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

        return "".join(password_chars)

    @staticmethod
    def strength_of(password, use_upper, use_lower, use_digits, use_symbols):
        """Return (label, score 0-100) based on length and character diversity."""
        diversity = sum([use_upper, use_lower, use_digits, use_symbols])
        length = len(password)

        score = 0
        score += min(length, 20) * 2       # up to 40 points for length
        score += (length - 20) if length > 20 else 0  # bonus for longer passwords
        score += diversity * 15            # up to 60 points for diversity
        score = max(0, min(100, score))

        if length < MIN_LENGTH or diversity < 2:
            return "Weak", min(score, 33)
        if score < 60:
            return "Weak", score
        if score < 85:
            return "Medium", score
        return "Strong", score


class PasswordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.generator = PasswordGenerator()
        self.history = []

        root.title("Password Generator")
        root.resizable(False, False)

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self):
        self.root.configure(bg=COLORS["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=COLORS["bg"])

        style.configure("TLabelframe", background=COLORS["card"], bordercolor=COLORS["border"],
                         relief="flat", borderwidth=1)
        style.configure("TLabelframe.Label", background=COLORS["card"], foreground=COLORS["accent"],
                         font=("Segoe UI", 9, "bold"))

        style.configure("TLabel", background=COLORS["card"], foreground=COLORS["text"],
                         font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"],
                         font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"],
                         font=("Segoe UI", 10))
        style.configure("Badge.TLabel", background=COLORS["card_alt"], foreground=COLORS["accent"],
                         font=("Segoe UI", 11, "bold"), padding=(10, 4), anchor="center")

        style.configure("TCheckbutton", background=COLORS["card"], foreground=COLORS["text"],
                         font=("Segoe UI", 10), focuscolor=COLORS["card"])
        style.map("TCheckbutton",
                  background=[("active", COLORS["card"])],
                  indicatorcolor=[("selected", COLORS["accent"]), ("!selected", COLORS["card_alt"])])

        style.configure("Horizontal.TScale", background=COLORS["card"], troughcolor=COLORS["card_alt"],
                         bordercolor=COLORS["card"], lightcolor=COLORS["accent"], darkcolor=COLORS["accent"])

        style.configure("TSpinbox", fieldbackground=COLORS["card_alt"], background=COLORS["card_alt"],
                         foreground=COLORS["text"], arrowcolor=COLORS["text"],
                         bordercolor=COLORS["border"], insertcolor=COLORS["text"], padding=4)

        style.configure("TEntry", fieldbackground=COLORS["card_alt"], foreground=COLORS["accent"],
                         bordercolor=COLORS["border"], insertcolor=COLORS["text"], padding=8)
        style.map("TEntry", fieldbackground=[("readonly", COLORS["card_alt"])],
                  foreground=[("readonly", COLORS["text"])])

        style.configure("Accent.TButton", background=COLORS["accent"], foreground="white",
                         font=("Segoe UI", 11, "bold"), padding=12, borderwidth=0, relief="flat")
        style.map("Accent.TButton",
                  background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent_pressed"]),
                              ("disabled", COLORS["card_alt"])],
                  foreground=[("disabled", COLORS["muted"])])

        style.configure("Secondary.TButton", background=COLORS["card_alt"], foreground=COLORS["text"],
                         font=("Segoe UI", 10), padding=9, borderwidth=1, relief="flat")
        style.map("Secondary.TButton",
                  background=[("active", COLORS["border"]), ("disabled", COLORS["card"])],
                  foreground=[("disabled", COLORS["muted"])])

        style.configure("TSeparator", background=COLORS["border"])

        style.configure("TProgressbar", troughcolor=COLORS["card_alt"], borderwidth=0, thickness=14)
        for name, color in (("Weak", COLORS["danger"]), ("Medium", COLORS["warning"]),
                             ("Strong", COLORS["success"])):
            style.configure(f"{name}.Horizontal.TProgressbar", troughcolor=COLORS["card_alt"],
                             background=color, bordercolor=COLORS["card_alt"],
                             lightcolor=color, darkcolor=color)
            style.configure(f"{name}Badge.TLabel", background=COLORS["card_alt"], foreground=color,
                             font=("Segoe UI", 11, "bold"), padding=(10, 4), anchor="center")

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=24)
        outer.grid(row=0, column=0, sticky="nsew")

        ttk.Label(outer, text="🔐 Password Generator", style="Title.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(outer, text="Generate strong, cryptographically secure passwords instantly.",
                  style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 18))

        # --- Length control ---
        length_frame = ttk.LabelFrame(outer, text="PASSWORD LENGTH", padding=14)
        length_frame.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        length_frame.columnconfigure(0, weight=1)

        self.length_var = tk.IntVar(value=12)
        self.length_badge = ttk.Label(length_frame, text="12", style="Badge.TLabel", width=4)
        self.length_badge.grid(row=0, column=1, padx=(14, 0))

        self.length_slider = ttk.Scale(
            length_frame, from_=MIN_LENGTH, to=MAX_LENGTH, orient="horizontal",
            variable=self.length_var, command=self._on_slider_change
        )
        self.length_slider.grid(row=0, column=0, sticky="ew")

        self.length_spin = ttk.Spinbox(
            length_frame, from_=MIN_LENGTH, to=MAX_LENGTH, width=5,
            textvariable=self.length_var, command=self._on_spin_change
        )
        self.length_spin.grid(row=1, column=0, sticky="w", pady=(12, 0))

        # --- Character type options ---
        options_frame = ttk.LabelFrame(outer, text="CHARACTER TYPES · SELECT AT LEAST 2", padding=14)
        options_frame.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        options_frame.columnconfigure((0, 1), weight=1)

        self.use_upper = tk.BooleanVar(value=True)
        self.use_lower = tk.BooleanVar(value=True)
        self.use_digits = tk.BooleanVar(value=True)
        self.use_symbols = tk.BooleanVar(value=True)
        self.exclude_ambiguous = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Uppercase (A-Z)", variable=self.use_upper).grid(
            row=0, column=0, sticky="w", pady=4)
        ttk.Checkbutton(options_frame, text="Lowercase (a-z)", variable=self.use_lower).grid(
            row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(options_frame, text="Numbers (0-9)", variable=self.use_digits).grid(
            row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(options_frame, text="Symbols (!@#$...)", variable=self.use_symbols).grid(
            row=1, column=1, sticky="w", pady=4)
        ttk.Separator(options_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Checkbutton(options_frame, text="Exclude ambiguous characters (0, O, l, 1, I, |)",
                         variable=self.exclude_ambiguous).grid(
            row=3, column=0, columnspan=2, sticky="w")

        # --- Generate button ---
        self.generate_btn = ttk.Button(outer, text="⚡  Generate Password", style="Accent.TButton",
                                        command=self.on_generate)
        self.generate_btn.grid(row=4, column=0, sticky="ew", pady=(0, 14))

        # --- Result display ---
        result_frame = ttk.LabelFrame(outer, text="GENERATED PASSWORD", padding=14)
        result_frame.grid(row=5, column=0, sticky="ew", pady=(0, 14))
        result_frame.columnconfigure(0, weight=1)

        self.password_var = tk.StringVar(value="")
        self.password_entry = ttk.Entry(
            result_frame, textvariable=self.password_var, font=("Consolas", 14),
            justify="center", state="readonly"
        )
        self.password_entry.grid(row=0, column=0, sticky="ew", ipady=6)

        self.copy_btn = ttk.Button(result_frame, text="📋  Copy to Clipboard", style="Secondary.TButton",
                                    command=self.on_copy, state="disabled")
        self.copy_btn.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        # --- Strength indicator ---
        strength_frame = ttk.LabelFrame(outer, text="PASSWORD STRENGTH", padding=14)
        strength_frame.grid(row=6, column=0, sticky="ew", pady=(0, 14))
        strength_frame.columnconfigure(0, weight=1)

        self.strength_bar = ttk.Progressbar(strength_frame, orient="horizontal",
                                             mode="determinate", maximum=100)
        self.strength_bar.grid(row=0, column=0, sticky="ew", ipady=2)

        self.strength_label = ttk.Label(strength_frame, text="—", style="Badge.TLabel", width=8)
        self.strength_label.grid(row=0, column=1, padx=(14, 0))

        # --- History ---
        history_frame = ttk.LabelFrame(
            outer, text="HISTORY · LAST 5 THIS SESSION (NOT SAVED TO DISK)", padding=14)
        history_frame.grid(row=7, column=0, sticky="ew")
        history_frame.columnconfigure(0, weight=1)

        self.history_list = tk.Listbox(
            history_frame, height=5, font=("Consolas", 10), activestyle="none",
            bg=COLORS["card_alt"], fg=COLORS["text"], selectbackground=COLORS["accent"],
            selectforeground="white", highlightthickness=0, borderwidth=0, relief="flat"
        )
        self.history_list.grid(row=0, column=0, sticky="ew")
        self.history_list.bind("<<ListboxSelect>>", self._on_history_select)

        if not CLIPBOARD_AVAILABLE:
            self.copy_btn.state(["disabled"])

    # --- Event handlers ---

    def _on_slider_change(self, _value):
        self.length_var.set(int(float(_value)))
        self.length_badge.config(text=str(self.length_var.get()))

    def _on_spin_change(self):
        self.length_badge.config(text=str(self.length_var.get()))

    def _on_history_select(self, _event):
        selection = self.history_list.curselection()
        if not selection:
            return
        entry = self.history_list.get(selection[0])
        password = entry.split(") ", 1)[-1] if ") " in entry else entry
        self.password_var.set(password)
        self.copy_btn.state(["!disabled"] if CLIPBOARD_AVAILABLE else ["disabled"])

    def on_generate(self):
        try:
            length = int(self.length_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid Length", "Please enter a valid numeric length.")
            return

        try:
            password = self.generator.generate(
                length=length,
                use_upper=self.use_upper.get(),
                use_lower=self.use_lower.get(),
                use_digits=self.use_digits.get(),
                use_symbols=self.use_symbols.get(),
                exclude_ambiguous=self.exclude_ambiguous.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Cannot Generate Password", str(exc))
            return

        self.password_var.set(password)
        self._update_strength(password)
        self._add_to_history(password)

        if CLIPBOARD_AVAILABLE:
            pyperclip.copy(password)
            self.copy_btn.state(["!disabled"])
        else:
            self.copy_btn.state(["disabled"])

    def on_copy(self):
        password = self.password_var.get()
        if not password:
            return
        if CLIPBOARD_AVAILABLE:
            pyperclip.copy(password)
            messagebox.showinfo("Copied", "Password copied to clipboard.")
        else:
            messagebox.showwarning("Clipboard Unavailable",
                                    "pyperclip is not installed. Run: pip install pyperclip")

    def _update_strength(self, password):
        label, score = self.generator.strength_of(
            password, self.use_upper.get(), self.use_lower.get(),
            self.use_digits.get(), self.use_symbols.get()
        )
        self.strength_bar["value"] = score
        self.strength_bar.configure(style=f"{label}.Horizontal.TProgressbar")
        self.strength_label.config(text=label, style=f"{label}Badge.TLabel")

    def _add_to_history(self, password):
        self.history.insert(0, password)
        self.history = self.history[:HISTORY_LIMIT]
        self.history_list.delete(0, tk.END)
        for i, pw in enumerate(self.history, start=1):
            self.history_list.insert(tk.END, f"{i}) {pw}")


def main():
    root = tk.Tk()
    app = PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
