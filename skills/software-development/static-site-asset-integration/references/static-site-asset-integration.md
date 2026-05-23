# Static Site Asset Integration Reference

## When to use

- Replacing hero gradients with real image backgrounds.
- Replacing placeholder product/model blocks with real `<img>` tags.
- Adding overlays so white/gold text stays readable on cinematic images.

## Search patterns that help

- `hero-bg`
- `model-placeholder`
- `model-image`
- `background: linear-gradient`
- `favicon.png`

## Safe edit pattern

- Read the exact HTML/CSS sections first.
- Patch only the repeated blocks that need changing.
- Keep wrappers, IDs, and data attributes intact.
- Add overlay and z-index rules at the bottom of the CSS file if the site already has a large component stylesheet.

## Useful CSS rules

- Hero backgrounds:
  - `background-size: cover;`
  - `background-position: center;`
  - `background-repeat: no-repeat;`
- Transparent product images:
  - `object-fit: contain;`
  - explicit padding inside the card
  - hover transform on the image element

## Verification

- Confirm all repeated hero slides were updated.
- Confirm all model cards were updated.
- Confirm asset folders exist for every referenced path.
- Confirm no old placeholder gradients remain in the targeted blocks.
