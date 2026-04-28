import json
from lib.json import extract_strings

test_data = {
    "title": "Welcome",
    "icon": "home-icon",
    "icons": ["heart", "star"],
    "settings": {
        "label": "Language",
        "icon": "globe"
    },
    "items": [
        {"name": "Item 1", "icon": "check"},
        {"name": "Item 2"}
    ]
}

strings = extract_strings(test_data)
print("Extracted strings:")
for path, val in strings:
    print(f"  {path}: {val}")

# Expected:
# title: Welcome
# settings.label: Language
# items[0].name: Item 1
# items[1].name: Item 2
# (No icons should be present)
