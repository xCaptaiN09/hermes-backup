# Thunar navigation notes

## When `click_element` can misfire

In Thunar, accessible names can sometimes resolve to the wrong control if the UI has:
- a search toggle with a generic/similar name,
- a details/status row that contains the folder name,
- or a folder item that is not actually visible in the current pane.

Observed failure mode:
- trying to click `LocalSend` or `bootimg-tools` resolved to the `Search for Files...` toggle or a status row instead of the folder item.

## Reliable recovery

1. Call `list_elements thunar` and confirm the current frame title.
2. If the desired folder is visible in the main pane, click it by its exact folder item name.
3. If `click_element` resolves the wrong thing, use `Ctrl+L` and type the exact path instead of hunting by name.
4. Verify with `capture` or `list_elements` after navigation.
5. After `Alt+Left`, confirm the window title/path changed; if not, use the visible `Back` button.

## Notes from this session

- `click_element` on `LocalSend` sometimes resolved to the search toggle or status bar instead of the folder item.
- `click_element` on `bootimg-tools` did the same.
- Exact path entry worked reliably for `~/Downloads/LocalSend/bootimg-tools`.
- Folder names can be easier to trust in `list_elements` than in a screenshot, because the same name may appear in the status bar.
- `Alt+Left` did not provide a reliable back-navigation result in this session; `Back` button and exact path entry were more reliable.

## Good pattern

- `focus thunar`
- `list_elements thunar`
- `click_element thunar <exact visible folder name>`
- `capture thunar` or `list_elements thunar`
- If ambiguous, use `Ctrl+L` and the full path

## Image-opening note

For opening a file already known by path, the simplest verification path was:
1. locate the file with `find`
2. open it via the desktop/browser/file URI path if native app launch is not yet covered by the skill
3. verify the opened content with `vision_analyze` or the browser image viewer
