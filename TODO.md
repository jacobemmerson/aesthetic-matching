# TODO

- **Roast (paused).** `server/roast.py` + Ollama are unwired from the service. When resumed:
  - Read EXIF from uploads (Pillow `getexif`): GPS -> name-drop the city; capture date -> mock
    old photos; camera model -> DSLR vs phone vs film-scan jokes. Never log or return GPS.
  - Handle HEIC uploads (`pillow-heif`) for iPhone users on non-Safari browsers.
