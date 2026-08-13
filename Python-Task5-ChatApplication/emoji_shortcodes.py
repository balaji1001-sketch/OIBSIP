"""Renders common emoji shortcodes (:smile:) as Unicode characters."""

import re

SHORTCODES = {
    "smile": "😄", "smiley": "😃", "grin": "😁", "laughing": "😆", "joy": "😂",
    "wink": "😉", "blush": "😊", "sunglasses": "😎", "thinking": "🤔",
    "neutral_face": "😐", "confused": "😕", "cry": "😢", "sob": "😭",
    "angry": "😠", "rage": "😡", "scream": "😱", "sleeping": "😴",
    "wave": "👋", "thumbsup": "👍", "+1": "👍", "thumbsdown": "👎", "-1": "👎",
    "clap": "👏", "pray": "🙏", "ok_hand": "👌", "muscle": "💪",
    "heart": "❤️", "heart_eyes": "😍", "broken_heart": "💔",
    "fire": "🔥", "star": "⭐", "sparkles": "✨", "100": "💯",
    "tada": "🎉", "rocket": "🚀", "eyes": "👀", "check_mark": "✅",
    "x": "❌", "warning": "⚠️", "question": "❓", "exclamation": "❗",
    "coffee": "☕", "pizza": "🍕", "beer": "🍺", "dog": "🐶", "cat": "🐱",
}

_SHORTCODE_RE = re.compile(r":([a-zA-Z0-9_+\-]+):")


def render(text):
    return _SHORTCODE_RE.sub(lambda m: SHORTCODES.get(m.group(1), m.group(0)), text)
