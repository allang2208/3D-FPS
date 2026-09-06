# Qwantani Night pure-sky panorama — 2026-09-06

Source: https://polyhaven.com/a/qwantani_night_puresky

Asset: `qwantani_night_puresky_8k.jpg`, 8192x4096 tonemapped equirectangular panorama, 30,309,210 bytes. Downloaded unchanged from Poly Haven; MD5 `70c24e45fe8db819641c76068675c4a2` matches its asset API.

Authors: Greg Zaal (photography), Jarod Guest (processing). License: CC0. This is the edited sky-only version of Qwantani Night.

Runtime: one inward-facing 64x32 sphere, one mipmapped anisotropic texture sample, no lighting, shadows, fog, screen-space pass, volumetric effect, or per-frame geometry rebuild. The existing instanced star layer remains in front for subtle twinkle. Daylight hides the complete night layer; cloud cover and moon direction attenuate it. The imported texture uses desktop VRAM compression and mipmaps to avoid a roughly 170 MiB RGBA8 allocation with mip levels.
