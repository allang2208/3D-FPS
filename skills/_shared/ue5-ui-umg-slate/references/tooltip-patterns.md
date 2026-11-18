# Tooltip Patterns

## Placement
- Anchor near cursor or target widget.
- Apply fixed offset. 原因：提示框需要与指针留出稳定间距，具体偏移仍服从视口边界与实际锚点。
- Flip horizontally/vertically when near viewport edges.
- Clamp final position to viewport bounds.

## Content
- First line: item display name and quantity.
- Second line: short description or fallback text.

## Lifecycle
- Show on hover enter.
- Update position while active. 原因：活动提示需跟随有效锚点变化，同时保留视口限制以防窗口变化后越界。
- Hide immediately on hover leave or invalid target.
