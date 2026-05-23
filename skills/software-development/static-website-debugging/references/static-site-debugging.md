# Static Website Debugging Notes

## Session-tested patterns

### 1) Bulletproof preloader pattern
A preloader that waits only for `window.load` can get stuck if the event is missed or an asset load behaves unexpectedly. A safe pattern is:
- animate progress toward ~95%
- keep an `isHidden` guard to prevent double execution
- listen for `window.load`
- also check `document.readyState === 'complete'`
- add a hard timeout fallback, e.g. 3000ms
- on hide, set progress to 100%, then remove the loading class and trigger hero animations

### 2) Asset path mismatch fix
When HTML points to `assets/models/*.png` but files are actually in `assets/*.png`, the page will render as if images are missing. Fix by making the filesystem match the HTML paths exactly, or update the references consistently.

### 3) Browser verification sequence
- Serve the folder over HTTP with a local server
- Open the page in the browser
- Inspect the rendered DOM and image elements
- Check console for 404s or JS errors
- Confirm image elements exist and their URLs resolve

### 4) Good debugging questions
- Is the page stuck before first paint or only during image loading?
- Do the referenced files exist at the exact paths used in HTML?
- Is a CSS overlay hidden behind or in front of content correctly?
- Did the code rely on a load event that might never fire in the current situation?

## Practical commands
- Local server: `python3 -m http.server 8000 --directory /path/to/site`
- Console inspection: look for failed network requests and uncaught JS errors
- If models are missing, compare the HTML `src` with the asset tree exactly

## Session note
This skill was created after a Lamborghini static-site task where a preloader hang was fixed by adding a load/cached-state/failsafe timeout path and the model images were restored by syncing the HTML paths with the actual `assets/models/` directory.