"""
BMI Calculator - Advanced (GUI) Tier
------------------------------------------------
A full desktop application built with tkinter that:
  * Calculates BMI from weight (kg) and height (cm) input fields
  * Shows colour-coded results (green = normal, red = obese, etc.)
  * Supports multiple named users
  * Persists every calculation to a local SQLite database
  * Displays historical records in a table
  * Plots a user's BMI trend over time with matplotlib
  * Handles database read/write errors gracefully

Run:
    python bmi_gui.py

Requirements:
    pip install -r requirements.txt
"""

import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmi_records.db")


# ----------------------------------------------------------------------
# BMI calculation helpers
# ----------------------------------------------------------------------
def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI given weight in kilograms and height in centimetres."""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def classify_bmi(bmi: float):
    """Return (category, colour_hex) for a given BMI value."""
    if bmi < 18.5:
        return "Underweight", "#3498db"   # blue
    elif bmi < 25:
        return "Normal", "#2ecc71"        # green
    elif bmi < 30:
        return "Overweight", "#f39c12"    # orange
    else:
        return "Obese", "#e74c3c"         # red


# ----------------------------------------------------------------------
# Database layer
# ----------------------------------------------------------------------
class BMIDatabase:
    """Handles all SQLite persistence for BMI records."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    height_cm REAL NOT NULL,
                    bmi REAL NOT NULL,
                    category TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialise database: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def add_record(self, user_name, weight_kg, height_cm, bmi, category):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO records "
                "(user_name, weight_kg, height_cm, bmi, category, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_name,
                    weight_kg,
                    height_cm,
                    bmi,
                    category,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to save record: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_users(self):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT DISTINCT user_name FROM records ORDER BY user_name COLLATE NOCASE"
            )
            return [row[0] for row in cur.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to load users: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_records_for_user(self, user_name):
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT weight_kg, height_cm, bmi, category, recorded_at "
                "FROM records WHERE user_name = ? ORDER BY recorded_at ASC",
                (user_name,),
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to load records: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass


# ----------------------------------------------------------------------
# GUI application
# ----------------------------------------------------------------------
class BMIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BMI Calculator")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(bg="#f5f6fa")

        try:
            self.db = BMIDatabase()
        except RuntimeError as e:
            messagebox.showerror("Database Error", str(e))
            self.destroy()
            return

        self._build_widgets()
        self._refresh_user_dropdown()

    # ---------------- UI construction ----------------
    def _build_widgets(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        tk.Label(
            self, text="BMI Calculator", font=("Segoe UI", 18, "bold"), bg="#f5f6fa"
        ).pack(pady=(15, 5))

        form = tk.Frame(self, bg="#f5f6fa")
        form.pack(pady=10)

        tk.Label(form, text="Name:", bg="#f5f6fa", font=("Segoe UI", 11)).grid(
            row=0, column=0, sticky="e", padx=5, pady=8
        )
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, width=25).grid(
            row=0, column=1, padx=5, pady=8
        )

        tk.Label(form, text="Weight (kg):", bg="#f5f6fa", font=("Segoe UI", 11)).grid(
            row=1, column=0, sticky="e", padx=5, pady=8
        )
        self.weight_var = tk.StringVar()
        tk.Entry(form, textvariable=self.weight_var, width=25).grid(
            row=1, column=1, padx=5, pady=8
        )

        tk.Label(form, text="Height (cm):", bg="#f5f6fa", font=("Segoe UI", 11)).grid(
            row=2, column=0, sticky="e", padx=5, pady=8
        )
        self.height_var = tk.StringVar()
        tk.Entry(form, textvariable=self.height_var, width=25).grid(
            row=2, column=1, padx=5, pady=8
        )

        tk.Button(
            self,
            text="Calculate & Save",
            font=("Segoe UI", 11, "bold"),
            bg="#4a69bd",
            fg="white",
            activebackground="#3c58a8",
            command=self.on_calculate,
        ).pack(pady=10, ipadx=10, ipady=4)

        self.result_frame = tk.Frame(self, bg="#dcdde1", width=400, height=90)
        self.result_frame.pack(pady=10)
        self.result_frame.pack_propagate(False)

        self.result_label = tk.Label(
            self.result_frame,
            text="Enter details and press Calculate",
            font=("Segoe UI", 13, "bold"),
            bg="#dcdde1",
            wraplength=380,
            justify="center",
        )
        self.result_label.pack(expand=True)

        # Legend
        legend = tk.Frame(self, bg="#f5f6fa")
        legend.pack(pady=(0, 10))
        legend_items = [
            ("Underweight", "#3498db"),
            ("Normal", "#2ecc71"),
            ("Overweight", "#f39c12"),
            ("Obese", "#e74c3c"),
        ]
        for text, color in legend_items:
            box = tk.Frame(legend, bg="#f5f6fa")
            box.pack(side="left", padx=6)
            tk.Label(box, text="  ", bg=color).pack(side="left")
            tk.Label(box, text=text, bg="#f5f6fa", font=("Segoe UI", 8)).pack(
                side="left", padx=(3, 0)
            )

        history_frame = tk.Frame(self, bg="#f5f6fa")
        history_frame.pack(pady=10)

        tk.Label(
            history_frame, text="Select User:", bg="#f5f6fa", font=("Segoe UI", 11)
        ).grid(row=0, column=0, padx=5)
        self.user_dropdown_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(
            history_frame,
            textvariable=self.user_dropdown_var,
            width=20,
            state="readonly",
        )
        self.user_dropdown.grid(row=0, column=1, padx=5)

        btn_frame = tk.Frame(self, bg="#f5f6fa")
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="View History",
            command=self.on_view_history,
            bg="#7f8fa6",
            fg="white",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            btn_frame,
            text="Show Trend Graph",
            command=self.on_show_graph,
            bg="#8e44ad",
            fg="white",
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, padx=8)

        tk.Button(
            btn_frame,
            text="Refresh Users",
            command=self._refresh_user_dropdown,
            bg="#535c68",
            fg="white",
            font=("Segoe UI", 10),
        ).grid(row=0, column=2, padx=8)

    # ---------------- Data helpers ----------------
    def _refresh_user_dropdown(self):
        try:
            users = self.db.get_users()
        except RuntimeError as e:
            messagebox.showerror("Database Error", str(e))
            users = []

        self.user_dropdown["values"] = users
        if users and not self.user_dropdown_var.get():
            self.user_dropdown_var.set(users[0])

    def _validate_inputs(self):
        name = self.name_var.get().strip()
        weight_str = self.weight_var.get().strip()
        height_str = self.height_var.get().strip()

        if not name:
            raise ValueError("Please enter a name.")

        try:
            weight = float(weight_str)
            height = float(height_str)
        except ValueError:
            raise ValueError("Weight and height must be numeric values.")

        if weight <= 0 or weight > 500:
            raise ValueError("Please enter a realistic weight in kg (1-500).")
        if height <= 0 or height > 300:
            raise ValueError("Please enter a realistic height in cm (1-300).")

        return name, weight, height

    # ---------------- Event handlers ----------------
    def on_calculate(self):
        try:
            name, weight, height = self._validate_inputs()
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        bmi = calculate_bmi(weight, height)
        category, color = classify_bmi(bmi)

        self.result_frame.configure(bg=color)
        self.result_label.configure(
            bg=color,
            fg="white",
            text=f"{name}'s BMI: {bmi}\nCategory: {category}",
        )

        try:
            self.db.add_record(name, weight, height, bmi, category)
        except RuntimeError as e:
            messagebox.showerror(
                "Database Error", f"BMI was calculated but could not be saved:\n{e}"
            )
            return

        self._refresh_user_dropdown()
        self.user_dropdown_var.set(name)

    def on_view_history(self):
        user = self.user_dropdown_var.get()
        if not user:
            messagebox.showinfo("No User Selected", "Please select a user first.")
            return

        try:
            records = self.db.get_records_for_user(user)
        except RuntimeError as e:
            messagebox.showerror("Database Error", str(e))
            return

        if not records:
            messagebox.showinfo("No Records", f"No history found for {user}.")
            return

        win = tk.Toplevel(self)
        win.title(f"History - {user}")
        win.geometry("520x320")

        columns = ("weight", "height", "bmi", "category", "date")
        tree = ttk.Treeview(win, columns=columns, show="headings")
        headings = {
            "weight": "Weight (kg)",
            "height": "Height (cm)",
            "bmi": "BMI",
            "category": "Category",
            "date": "Date",
        }
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=95, anchor="center")

        for row in records:
            tree.insert("", "end", values=row)

        tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_show_graph(self):
        user = self.user_dropdown_var.get()
        if not user:
            messagebox.showinfo("No User Selected", "Please select a user first.")
            return

        try:
            records = self.db.get_records_for_user(user)
        except RuntimeError as e:
            messagebox.showerror("Database Error", str(e))
            return

        if not records:
            messagebox.showinfo("No Data", f"No BMI records found for {user}.")
            return

        dates = [r[4] for r in records]
        bmis = [r[2] for r in records]

        win = tk.Toplevel(self)
        win.title(f"BMI Trend - {user}")
        win.geometry("680x460")

        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        ax.plot(range(len(bmis)), bmis, marker="o", color="#4a69bd", linewidth=2)
        ax.axhspan(18.5, 25, color="#2ecc71", alpha=0.12, label="Normal range")
        ax.set_title(f"{user}'s BMI Trend")
        ax.set_xlabel("Record #")
        ax.set_ylabel("BMI")
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels([d.split(" ")[0] for d in dates], rotation=45, ha="right")
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        def on_close():
            plt.close(fig)
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)


if __name__ == "__main__":
    app = BMIApp()
    app.mainloop()
