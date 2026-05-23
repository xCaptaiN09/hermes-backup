---
name: static-website-debugging
description: Diagnose and update local static sites built with HTML/CSS/JS, including asset wiring, loading issues, and browser verification.
version: 1.0.0
author: Hermes Agent + Captained by session learning
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [static-site, html, css, javascript, assets, browser, local-server, debugging]
---

# Static Website Debugging

Use this skill when the task is to edit or debug a local static website or front-end prototype made of HTML/CSS/JS files and asset folders.

## Typical triggers
- Update `index.html`, CSS modules, or JS modules in a local site directory
- Fix missing images, favicon issues, broken paths, or asset folder mismatches
- Diagnose loading screens, preloader hangs, or scripts that wait on page load
- Verify changes in a browser using a local HTTP server

## Workflow
1. Inspect the file tree and confirm the paths referenced in HTML/CSS/JS.
2. Read the relevant file blocks before editing; avoid patching from memory.
3. Make the smallest possible content change first.
4. If assets are referenced by relative paths, verify the file names and folder locations exactly.
5. When a page depends on `window.load`, add a fallback or cached-state check if the page can hang before the event fires.
6. Run a local server and verify in a browser, not by double-clicking the HTML file.
7. Check browser console for 404s and JS errors when images or sections fail to appear.

## Common pitfalls
- Asset path mismatches between HTML and the actual filesystem layout
- Using `file://` instead of a local server during verification
- Preloaders that only hide on `window.load` and never recover if something hangs
- CSS overlays or pseudo-elements that block content if `z-index` is wrong
- Model/image cards that still rely on placeholder divs after images are introduced

## Verification checklist
- Page title loads
- Preloader disappears
- Hero sections render in order
- Image URLs resolve without 404s
- Browser shows the expected layout at normal and hover states
- Console is free of red network errors

## Related support files
- `references/static-site-debugging.md` — session-tested fixes, path mismatch notes, and verification commands
- `references/public-site-access.md` — fallback order for public pages that time out or gate behind challenges

## Notes
Prefer browser verification for visual work and use the console for asset/error diagnosis. If the page is stuck, treat the load lifecycle as suspect before assuming the content itself is broken.