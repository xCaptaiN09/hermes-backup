# Thunar double-click failure cases

## Session findings

Observed during direct folder-opening tests in Thunar:

- `double_click_element thunar LocalSend` succeeded once when the folder was clearly in the current pane and the accessible target resolved correctly.
- `double_click_element thunar bootimg-tools` repeatedly misresolved to unrelated controls such as `dialog-error-symbolic` or the search toggle/status row.
- When falling back to coordinate double-click on the visible `bootimg-tools` folder icon, the click was accepted by the tool, but the Thunar window state was lost immediately afterward (`windows == []`, `focus thunar` reported no windows found).

## Practical guidance

- Prefer `double_click_element` only when the folder name is clearly visible and the current pane is stable.
- If Thunar resolves the wrong node, use `Ctrl+L` with the exact path instead of continuing to hunt by name.
- If using coordinate double-click for a visible icon, verify the window title and current window list immediately after the action.
- Do not treat a successful click return value as proof that the intended folder opened.

## Example reliable path

- `~/Downloads/LocalSend`
- `~/Downloads/LocalSend/bootimg-tools`

## Verification pattern

1. `focus thunar`
2. `list_elements thunar`
3. `capture thunar`
4. `double_click_element thunar <visible folder>` or coordinate double-click if necessary
5. `list_elements thunar` again
6. If the window disappears from tracking, recover with path entry or relaunch Thunar before continuing
