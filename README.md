# Doubao Work West Coast English

A small Windows companion that displays English over Doubao Work's Chinese interface. It runs outside the client: no patched executable, resource archive, browser cache, system proxy, or certificate.

The tone is clear first, with a little West Coast energy where it fits: “Yo, what are we tackling today?”, “Give it another shot”, “Hell yeah.” Buttons and permission choices stay direct.

## Install and use

1. Open Doubao Work.
2. Double-click `Start-English.cmd`. The first run installs local Python dependencies; later runs start directly. Python 3.11 or 3.12 (or `uv`) must be available.
3. To turn it off, double-click `Stop-English.cmd`.

The English layer follows the client window, hides when the client is not active, and lets mouse clicks pass to the client. Stopping it immediately shows the original UI. The local glossary is in [`overlay_terms.json`](overlay_terms.json).

## Scope

This is an early public release, tested on Windows with Doubao Work 2.31.10. It covers common navigation, the home prompt, the chat composer, and several task and status labels. It translates visible UI phrases from the glossary, not your chats, files, or generated content. OCR can miss or misread text, and some screens remain Chinese. Add short, reviewed UI phrases to the glossary to extend coverage.

The software uses [RapidOCR](https://github.com/RapidAI/RapidOCR) for local OCR. Screenshots stay on your computer. No translation request is sent to a server. The project does not contain Doubao Work binaries, bundles, cache files, or account data.

## Development

`capture_native.py` captures only the target window. `overlay_preview.py` detects text and creates an image layer. `live_overlay_boxes.py` displays small click-through patches and updates them as the UI changes. Run `python overlay_preview.py screenshot.png overlay_terms.json preview.png` to inspect a proposed translation before adding a term.

Contributions should keep controls and permissions unambiguous. Put slang in greetings and low-stakes status messages rather than destructive actions.
