# Static site asset + preloader fixes

Use this when a local HTML/CSS/JS site appears stuck loading or images do not render.

## Asset path checks
- Compare the paths used in HTML/CSS against the real on-disk paths.
- If HTML expects `assets/models/model-x.png`, make sure the file exists at that exact path, not just `assets/model-x.png`.
- If you move assets, mirror the folder structure in the repository instead of changing one path in isolation.

## Preloader hardening
A preloader that waits only on `window.load` can get stuck if the event is missed or cached state behaves oddly.

Recommended pattern:
- start a progress animation with a guard so it cannot run twice
- add a standard `window.load` listener
- add a `document.readyState === 'complete'` cache check
- add a short failsafe timeout to hide the preloader even if an asset is broken

## Browser verification
- Serve the site over HTTP for testing (`python3 -m http.server ...`) rather than opening `file://` directly.
- Use browser devtools / console to inspect `document.images` and check for broken URLs.
- Confirm the page state after the preloader hides, not just whether the HTML loads.

## Useful failure patterns
- blank/black screenshot from a browser tool does not always mean the page is broken; re-open the page and verify via snapshot/console first
- if only some images are missing, check for path mismatches between generated HTML and copied assets
