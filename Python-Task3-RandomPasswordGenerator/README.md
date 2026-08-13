# Task 3 · Random Password Generator (Advanced Tier)

A GUI tool built with `tkinter` that generates strong, cryptographically secure
passwords based on user-defined criteria.

## Features

- **GUI controls** — slider + spinbox for password length (8–64), checkboxes
  for character types (uppercase, lowercase, numbers, symbols)
- **Cryptographically secure generation** — uses Python's `secrets` module
  (not `random`) for every random choice, including the shuffle step
- **Guaranteed character coverage** — the generated password always contains
  at least one character from each selected type
- **Strength indicator** — color-coded progress bar and Weak / Medium /
  Strong label based on length and character diversity
- **Exclude ambiguous characters** — optional checkbox to remove
  look-alike characters (`0`, `O`, `l`, `1`, `I`, `|`)
- **Copy to Clipboard** — powered by `pyperclip`; passwords are copied
  automatically on generation, with a manual copy button as backup
- **Session history** — shows the last 5 generated passwords; kept in
  memory only and never written to disk
- **Input validation** — rejects lengths under 8 characters or fewer than
  2 selected character types, with a clear error dialog

## Requirements

- Python 3.8+
- `tkinter` (included with most standard Python installations)
- `pyperclip` (for clipboard support)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python password_generator.py
```

1. Set the desired password length using the slider or spinbox.
2. Select at least 2 character types to include.
3. (Optional) Enable "Exclude ambiguous characters".
4. Click **Generate Password** — the password is generated, displayed,
   scored for strength, copied to your clipboard, and added to history.
5. Click any entry in the history list to reload it into the display field.

## Project Structure

```
Python-Task3-RandomPasswordGenerator/
├── password_generator.py   # Application source (generator logic + GUI)
├── requirements.txt        # Python dependencies
├── details.txt             # Original task requirements
└── README.md                # This file
```

## Notes

- If `pyperclip` is not installed, the app still runs — clipboard-related
  buttons are simply disabled until it's available.
- History is session-only by design (per the task's security requirement)
  and resets each time the app restarts.
