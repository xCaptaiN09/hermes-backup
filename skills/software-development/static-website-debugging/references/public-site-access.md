# Public site access and verification fallback

Session-learned workflow for public pages that do not load cleanly in the browser.

## Symptoms
- `browser_navigate` times out while opening a public page.
- The page returns an interstitial or challenge page instead of the expected content.
- A site is reachable via HTTP, but browser interaction stalls before the desired UI appears.

## Preferred fallback order
1. Retry the target page once with a direct, canonical URL.
2. Check whether the service exposes a public JSON/API endpoint for the data.
3. Fetch the underlying data with a normal HTTP client when the browser cannot reach the content cleanly.
4. If the user only needs the value, report the extracted data instead of forcing a fragile browser path.
5. If the user explicitly wants a screenshot, only provide a browser screenshot when the page content is actually visible; otherwise say the page was gated and show the best available fallback artifact clearly labeled.

## Practical notes
- Use a normal browser screenshot for real page state when the page loads.
- For protected pages, the useful verification target is often the API response, not the rendered page.
- Keep the fallback clearly described so it is not mistaken for a native browser capture.
