# Shared physical gun optics

The 2026-10-30 screenshot review found black screen surrounds, hidden weapon
models and low-contrast generic marks. This revision sends one owner-local
scene capture to the original ocular glass. Scope frames, installation sockets,
weapon meshes and animations are retained. The normal ADS camera supplies the
surrounding scene. Only the current optic captures, only while aiming.

## Reticle families

| Optic | Image and markings |
| --- | --- |
| M24 factory 6x | Fine precision cross, spaced mrad ticks and numbers; auxiliary 1x retained |
| LPVO 1–6x | Illuminated horseshoe and centre dot, lower angular ladder |
| Prism 2x | Amber chevron with its tip on the firing ray, lower angular marks |
| KV 1/2/4x | Open-centre cross, red dot, sparse wind-hold grid |
| PSO-1 / SVD factory | Primary chevron, angular windage marks, 1.7 m geometric stadia |
| DW715 2x | Duplex cross, restrained 4 mrad graduations for a small long-eye-relief aperture |
| Thermal 1.5/3/8x | Mint cross, acquisition corners, mrad graduations and brighter cold detail |

One mrad is computed from the captured ray angle, using the current displayed
zoom. Numbers and half-mrad ticks disappear when too closely spaced in pixels.
Dark etched lines have a light contrast outline; illumination accents differ
by family. These are angular/ranging marks, not ammunition-specific ballistic
zeroes. PSO stadia assume a 1.7 m reference height.

## Integration

`UsesPhysicalScope` and `GetPhysicalScopeView` bind by the selected optic and its
real material slots. Every existing host of LPVO, prism, KV, thermal and Russian
PSO attachments uses the same system. SVD's factory glass remains in its native
skeletal mesh. Static fitted variants use their own sight socket transforms.
The bow's previously requested presentation is a separate system and is not
changed by this gun-optic migration.

The active glass and obsolete physical reticle overrides are restored on ADS
exit, actions, weapon/part changes, menus, third-person views and destruction.
There is one asynchronous resource request per owning widget and one bounded
1024-square HDR render target, configurable 512–1536. Nothing captures for
remote players or inactive scopes. No global model visibility is changed.

The thermal target/depth-occlusion implementation is retained, while its
post-process now runs in the lens capture. Lens zoom and mouse gain share the
same interpolated multiplier. LPVO, KV and thermal wheel transitions are smooth.
The M24 upper red-dot branch and existing attachment availability remain intact.

## Production

1. `author_glyphs.py` produces exact numeral/unit atlas source.
2. `run_assets.ps1 -Script build_assets.py -WithRHI` imports, compiles and saves
   the four assets in `/Game/Weapons/SharedPhysicalOptics20261030`.
3. `build_editor.ps1` performs the full Editor target build under the existing
   project batch mutex, after any current build finishes.

The authoring-input JSON records source ocular surfaces; model geometry is not
modified. Receipts distinguish saved assets, material compilation and DLL link.
No game, screenshot pass, input test or multiplayer/performance acceptance is
part of this modification delivery. The earlier 17 screenshots are before-images.
