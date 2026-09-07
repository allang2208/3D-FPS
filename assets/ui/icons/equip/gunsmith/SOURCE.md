# Gunsmith backpack renders

These transparent PNGs are generated from the current runtime models, materials,
camera framing, and lighting used by `res://ui/gunsmith_preview.gd`.

- Generator: `res://tests/render_gunsmith_backpack_icons.gd`
- Output size: 1024 x 260, transparent background
- Models: the five entries in `GunsmithPreview.MODELS`
- Purpose: horizontal backpack art only; equipment slots continue to use the
  upward-diagonal `res://assets/ui/icons/equip/fps_*.png` set.

Regenerate with a visible rendering backend so skinned meshes and materials are
captured from the same path as the in-game modification panel.
