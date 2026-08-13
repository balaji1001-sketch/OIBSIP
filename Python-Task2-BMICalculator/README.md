# BMI Calculator

A desktop BMI (Body Mass Index) calculator built with Python and Tkinter. It
calculates BMI, classifies the result, and stores each user's history locally.

## Contents

```
bmi_calculator/
├── bmi_cli.py          # Beginner tier - command-line tool
├── bmi_gui.py           # Advanced tier - full GUI application
├── requirements.txt      # Dependencies for the advanced tier
└── README.md             # This file
```

Running `bmi_gui.py` will automatically create a `bmi_records.db` SQLite
file in the same folder the first time it's launched. This file is not
included in the zip since it's generated at runtime.
## Advanced Tier - `bmi_gui.py`

A full desktop application built with **tkinter**, **sqlite3**, and
**matplotlib**.

**Install dependencies:**
```bash
pip install -r requirements.txt
```
(`tkinter` and `sqlite3` ship with the standard Python installation on most
platforms — on some Linux distros you may need `sudo apt install python3-tk`.)

**Run it:**
```bash
python bmi_gui.py
```

### Feature checklist (all implemented)

- [x] GUI window built with tkinter — no command line
- [x] Input fields with labels for name, weight, and height; a "Calculate & Save" button
- [x] Result displayed in the GUI with colour-coded feedback
      (blue = underweight, green = normal, orange = overweight, red = obese)
- [x] Multi-user support — every record is tagged with a user name, and a
      dropdown lets you switch between users
- [x] Historical records stored in an SQLite database (`bmi_records.db`)
- [x] Graph view — a matplotlib line chart shows a selected user's BMI
      trend over time, with the healthy range shaded in green
- [x] Error handling for invalid input and database read/write failures
      (all DB calls are wrapped in try/except and surfaced via message boxes)

### How to use it

1. Enter a name, weight (kg), and height (cm), then click **Calculate & Save**.
   The result box changes colour based on the BMI category and the record
   is saved to the database automatically.
2. Use the **Select User** dropdown to pick any user who has saved records.
3. Click **View History** to see a table of that user's past records.
4. Click **Show Trend Graph** to see a line chart of that user's BMI over
   time.
5. Click **Refresh Users** any time to reload the dropdown list (useful if
   you've just added a new user).

### Notes on design choices

- **SQLite over CSV**: chosen for reliable concurrent read/write, easy
  querying by user, and to demonstrate `sqlite3` CRUD operations as
  suggested in the task brief.
- **BMI thresholds** follow the standard WHO classification:
  - `< 18.5` → Underweight
  - `18.5 – 24.9` → Normal
  - `25 – 29.9` → Overweight
  - `≥ 30` → Obese
- All database operations live in a single `BMIDatabase` class so the GUI
  code never touches SQL directly, which keeps error handling centralised
  and consistent.
