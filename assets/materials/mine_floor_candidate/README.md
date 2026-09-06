# Mine floor candidate

Generated on the authorized 5080 ComfyUI host with FLUX.2 Dev FP8, 12 steps, seed 906031. Full raw image, generation log, preparation script and Godot scene previews: `E:/3d/mine-floor-staging-20260906/`.

Material: cool grey worn slate, 4 m repeat, 1024² albedo/normal/roughness. Uses the original mine wall pipeline's periodic-plus-smooth seam correction, with darker [87,92,94] base color and restrained fissures. Normal and roughness are artist-directed derivatives, not measured PBR scans. No displacement or collision modification.

User approved integration on 2026-09-06. `scripts/main.gd` now assigns `mine_floor.tres` to the default ground mesh. The existing ground geometry, height and collision are unchanged. The original candidate directory is retained to preserve texture import settings. Actual D3D12 Forward+ scene render and headless material load passed.
