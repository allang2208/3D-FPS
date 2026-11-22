# Shared physical gun optics

The 2026-10-30 screenshot review found black screen surrounds, hidden weapon
models and low-contrast generic marks. This revision sends one owner-local
scene capture to the original ocular glass. Scope frames, installation sockets,
weapon meshes and animations are retained. The normal ADS camera supplies the
surrounding scene. Only the current optic captures, only while aiming.

## Reticles

| Optic | Glass and markings |
| --- | --- |
| M24 factory 6× | The fine silver crossing gains darker outer shoulders, following the [earlier wire design](../../Source/FPSGAME/UI/M24ScopeDrawing.cpp). It follows the rear glass during the bolt cycle. The upper 1× dot follows its own socket. |
| LPVO 1–6× | The original red fluorescent centre dot and four short fine arms. The arm spacing follows the [original ocular mesh](../LPVO1to6X20260911/build_model.py). The dot uses a 3.2-render-pixel core and a narrow dark-red edge. |
| Prism 2× | The red dot and four short red arms follow the [original prism mesh](../PrismScope2X20260911/build_model.py) at the scale of its own rear glass. |
| KV 1/2/4× | The [release design](../../Docs/Weapons/kv-scope-universal-20261019.md) specifies a central cross. Cool-white wires intersect at the illuminated centre. The horizontal pair retains its two short nicks. |
| SVCh KV | A pale celadon point with a low, separated T leaves the upper field clear. |
| PSO-1 4× | The main tip meets the warm red point. One lower chevron and short side wires recall the [release engraving](../../Docs/Weapons/scope-optics-refinement-20260927.md). The display sits inside the rubber cup. |
| SVD integral 4× | Two fine bronze wires and a small lower notch around a honey-coloured point. |
| DW715 2× | The [original two-weight cross](../../Docs/Weapons/dw715-compact-scope-20260927.md) uses a fine warm-silver intersection and darker, wider outer arms. |
| Thermal 1.5/3/8× | A fixed red centre and four short corners. Surface colour and normals separate cold terrain from white-hot creatures. Fire retains its amber tint. |
| Clearfield 2× | Green centre fibre and fine crosswires on lightly green-coated glass. |
| Farwatch 4× | Fine green wires and two equal-width lower crossbars follow the [fixed bow glass geometry](../BowSingleLensOptics20260927/author_assets.py). |
| Peakwatch 3–6× | Two shallow green peak shoulders, a solid green centre and one short lower reference follow the [bow design](../../Docs/Weapons/peakwatch-reticle-v3-20261028.md). Draw and release tint the shoulders. |

The four saved materials use `Reticle.hlsl` for pane-local geometry and `ReticleInk.hlsl` for illumination. The shaded side of an etched line turns with the glass. The point stays visible while peripheral strokes taper or dim. The two fixed bow lenses use the original green illuminant, a 3.6-pixel solid point and the existing Fresnel coating response. Zoom changes the scene independently of the engraving.

## Integration

`GetPhysicalScopeView` resolves the active eyepiece and material slot. It supplies two axes and a centre on the animated mesh. The lens material computes its engraving in that local frame. Zoom controls the captured scene independently.

Settled ADS places the firearm eyepiece datum 7 cm from the view camera (previously 9 cm), in both right- and left-hand rigs. Fixed bow glass retains its main-camera zoom and glass UVs. Its owner-only projection increases glass diameter by a design factor of 1.50 at 2× and 1.32 at 4×. Peakwatch targets 80% of the shorter viewport dimension, previously 72%. These are framing settings, independent of the magnified scene.

The LPVO capture uses the fitted housing bounds and first-person projection for coverage. Its engraving uses the glass radius. The glass coverage compares the surface position before first-person morphing against the rear element.

The LPVO and prism fittings for A762, LMG201, ASH12, PKM and SVD use alternate material-slot names. The game resolves both the glass and the original etched section by their paired slot names. M16's extra mount occupies the first slot.

The active glass and obsolete physical reticle overrides are restored on ADS
exit, actions, weapon/part changes, menus, third-person views and destruction.
During local ADS, one HDR target updates on each world tick from the same camera
view as the glass projection. Its side is budgeted at 75% of the shorter viewport
axis, rounded up to a multiple of 64, with a 384-pixel floor. The default gun
ceiling is 1024. Peakwatch allows a higher ceiling for its larger aperture.
At 1920×1080 the default target is 832×832 for both.

The glass composites after temporal AA and motion blur. A scene-depth comparison
keeps opaque geometry in front of it visible. The current material update is
`publish_motion_clarity.py`. It also updates the fixed bow lenses.

The thermal pass reads the base colour and world normal from the captured scene.
`thermal_material.py` wires both inputs into `M_PhysicalThermalScene`.
The shared lens applies the screen's exposure compensation when displaying thermal imagery.

The thermal target/depth-occlusion implementation is retained, while its
post-process now runs in the lens capture. Lens zoom and mouse gain share the
same interpolated multiplier. LPVO, KV and thermal wheel transitions are smooth.
The M24 upper red-dot branch and existing attachment availability remain intact.

## Production

1. Edit the family patterns in `Reticle.hlsl`, their common palette in `ReticleInk.hlsl`, and captured-scene compositing in `lens.hlsl`.
2. Run `publish_motion_clarity.py` in a rendering-enabled UE authoring batch to compile and save the shared gun lens, Peakwatch and both fixed bow glasses.
3. Build the game and editor targets after changing the C++ projection or mounting logic.

The authoring-input JSON records the source ocular surfaces. The production index links the saved material hashes, per-optic readback and previous packages.
