---
name: static-site-asset-integration
description: "Integrate real image assets into existing static HTML/CSS sites without breaking layout, layering, or existing interactions."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  tags: [html, css, static-site, asset-integration, frontend, patching]
---

# Static Site Asset Integration

Use this skill when a user asks you to replace placeholder visuals in an existing HTML/CSS site with real images, transparent PNGs, or CDN-backed assets.

## Core workflow

1. **Inspect the existing structure first.**
   - Read the relevant HTML/CSS files.
   - Search for the exact section names, class names, and placeholder markup.
   - Avoid broad replacements until you know how many copies exist.

2. **Patch the smallest possible surface area.**
   - Replace only the targeted hero slide, card image block, or asset path.
   - Preserve existing IDs, data attributes, and JS hooks.
   - Prefer `patch` over rewriting the whole file.

3. **Use semantic image markup.**
   - For hero backgrounds, keep the existing container and swap the inline gradient or image source.
   - For product/model cards, replace placeholder blocks with `<img>` tags when the asset is transparent or needs real layout behavior.
   - Keep alt text specific and meaningful.

4. **Add layering styles carefully.**
   - If the design needs text over images, add an overlay pseudo-element and explicit `z-index` ordering.
   - For transparent car images, use `object-fit: contain`, not `cover`.
   - Verify that hover transforms and filters apply to the image, not to the wrapper only.

5. **Check for conflicts in other CSS files.**
   - Existing animations or positioning rules may live in separate files.
   - If a selector already exists elsewhere, make sure the new rules complement it instead of clobbering it.

6. **Verify the asset paths and folders.**
   - Ensure the referenced directories exist.
   - Confirm favicon and hero/model paths match the HTML exactly.
   - Search for any remaining placeholder gradients or fallback blocks.

## Common pitfalls

- Replacing a placeholder block but accidentally removing the surrounding `.model-image` wrapper.
- Adding a pseudo-element overlay without setting the parent `position: relative`.
- Setting the overlay above the text because `z-index` ordering was not explicit.
- Using `background-size: cover` for product cutouts that should remain fully visible.
- Editing only one of several repeated sections in a slider or card grid.

## Verification checklist

- The intended hero/card blocks are updated.
- No placeholder gradients remain in the targeted sections.
- The CSS overlay still allows text and badges to sit above the image.
- Favicon and referenced asset directories exist.
- The page still preserves its original navigation, slider, and card structure.

## Support files

- `references/static-site-asset-integration.md` — concise checklist and example selector/search patterns for this workflow.
