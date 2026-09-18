# Runtime heightfield ground material (FPSGAME temperate hills)

The hills world does not use a Landscape actor. Terrain is CPU-built `UDynamicMeshComponent`
chunks streamed around the player, so every Landscape-specific node is unavailable:
no `LandscapeLayerCoords`, no `LandscapeLayerBlend`, no `LandscapeGrassOutput`, no RVT
volume, no Nanite and no tessellation. The surface look therefore has to come entirely
from one ordinary material driven by world coordinates.

Live assets (2026-09-18).

| Asset | Role |
| --- | --- |
| `/Game/WorldGeneration/TemperateHills/M_TemperateGround` | Layered hill ground itself |
| `/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround` | **What `DA_TemperateHillsStreaming.GroundMaterial` points at**: hill ground plus the river bank/pebble blend |
| `Tools/WorldGeneration/build_hills_ground_v2.py` | Idempotent rebuild of both materials |
| `Tools/WorldGeneration/dump_ground_hlsl.py` + `validate_ground_hlsl.ps1` | Offline shader compile check |

Read `Docs/WorldGeneration/ground-material-layered-20260918.md` for the full design,
parameter table and open boundaries.

## Contract with the terrain code

`TemperateHillsStreaming.cpp` writes one vertex colour per terrain vertex:
`FVector4f(Bank, Wet, PebbleCover, 1)`.

| Channel | Meaning | Consumers |
| --- | --- | --- |
| R | river bank mask | bank/pebble blend, and it suppresses the hill parallax |
| G | damp/wetness by height above the water | darkening, roughness, relief flattening |
| B | seeded pebble bars | bank height blend |
| A | 1 | — |

`ATemperateHillsWorld::Tick` drives the `Wetness` scalar from the weather manager. Keep
both the vertex-colour layout and the `Wetness` parameter name: both are cross-module
interfaces, not material details.

## Layout that works for a runtime heightfield

1. **Several families at deliberately different world scales** (non-integer ratios). One
   tiled sheet at one scale is the single biggest tell that the ground is a texture.
2. **Height-weighted blending**, not plain weight averaging. Compute a base mask (slope
   plus low-frequency patch noise), then `boost = saturate((h - bias) * contrast + 1)` from
   each family's own height map and renormalise. Families then interlock along their relief.
3. **Bounded parallax occlusion** for near-field depth. March a composite of two height
   maps, fade out by ~7 m, gate on the view angle, and multiply the depth by `(1 - vertex R)`
   so a region with its own relief march never stacks two of them.
4. **Whiteout normal blending** (`normalize(float3(a.xy + b.xy*w, a.z*b.z))`). Averaging
   normals flattens the relief the height maps just produced.
5. **Macro variation at two scales** on albedo and roughness; distance-faded fine-grain
   detail from a family already loaded (no fifth texture set).
6. **Cavity AO from the same height maps**, which costs nothing extra and is what sells
   the layering under indirect light.

## Hard rules learned the hard way

- **A TextureSample's sampler type must come from the texture's compression settings, not
  its sRGB flag.** `UTexture::GetMaterialType()` decides in this order: `TC_Masks` →
  `SAMPLERTYPE_MASKS`, `TC_Normalmap` → `SAMPLERTYPE_NORMAL`, `TC_Grayscale`/`TC_Alpha`/
  `TC_Displacementmap` likewise, and only `TC_Default` falls through to
  `sRGB ? SAMPLERTYPE_COLOR : SAMPLERTYPE_LINEAR_COLOR`. This project's height maps and
  RHAOM masks are `TC_Masks` — linear, but they must be sampled as Masks. Getting this wrong
  is a **hard material compile error**, and the only in-game symptom is that the whole
  terrain silently reverts to the default checkerboard material:

  ```
  LogMaterial: Warning: [AssetLog] .../M_PebbleShoreGround.uasset:
    Failed to compile Material for platform PCD3D_SM6, Default Material will be used in game.
    (Node TextureSample) Sampler type is Linear Color, should be Masks for ground_I_height
  ```

  Derive the sampler type from the texture at build time (`required_sampler_type()` in
  `build_hills_ground_v2.py`) so the mismatch cannot be authored, and gate with
  `Tools/WorldGeneration/check_ground_samplers.py` (walks every sample node and compares).

- **A Custom node cannot declare helper functions.** The material compiler wraps node code
  in a function body, so `float vn(float2 p){...}` is a syntax error. Spell the maths out
  inline, or move the helper into a Material Function asset. The inline value-noise form
  the project already uses is:

  ```
  float2 q=P.xy*FREQ+float2(OX,OY);float2 i=floor(q),f=frac(q);f=f*f*(3-2*f);
  float4 h=frac(sin(float4(dot(i,float2(127.1,311.7)),dot(i+float2(1,0),float2(127.1,311.7)),
      dot(i+float2(0,1),float2(127.1,311.7)),dot(i+float2(1,1),float2(127.1,311.7))))*43758.5453);
  float n=lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
  ```

- **Texture samples are `float4` inside Custom nodes.** `float4(hG,hS,hR,0.5)` with sampled
  inputs is an arity error; mask the sample with `.r` instead (`float4(hG.r,hS.r,hR.r,0.5)`).
- **Compute `ddx`/`ddy` outside the loop** and pass `Texture2DSampleGrad(Texture,TextureSampler,uv,gx,gy)`
  inside it, or the material fails to compile with a gradient-in-loop error. Declare the
  height texture as a `MaterialExpressionTextureObject` input so the node gets both the
  texture and the implicit `<PinName>Sampler`.
- **A commandlet does not compile material shaders.** `recompile_material` returns an empty
  error list even when nothing was compiled, so a headless "success" proves nothing about
  the HLSL or the graph. Validate in two layers instead: the graph check below, and HLSL out
  of process.

## Validating material work without rendering

1. **Graph level** — `Tools/WorldGeneration/check_ground_samplers.py` walks every
   TextureSample/TextureObject node in both ground materials, derives the sampler type each
   texture demands, and reports mismatches. This is the check that would have caught the
   checkerboard-terrain bug before it shipped.
2. **HLSL level** — headless `dump_ground_hlsl.py` writes one `.hlsl` per Custom node,
   inferring each input's component count from the connected expression (`TextureSample`/
   `VertexColor` = float4, `WorldPosition`/normals/camera = float3, `ScalarParameter` = float,
   `Custom` = its `output_type`) and stubbing `Texture2DSampleGrad`. `validate_ground_hlsl.ps1`
   then compiles every file with the Windows SDK `fxc /T ps_5_0` and `dxc -T ps_6_0`.
3. **Real compile** — `UnrealEditor-Cmd.exe <uproject> -run=DerivedDataCache -fill` actually
   compiles material shaders for PCD3D_SM6 and logs the same
   `Failed to compile Material ... Default Material will be used in game` line on failure.
   It walks every asset in the project and is slow (minutes to tens of minutes), so use it
   as the final gate rather than the inner loop.

These catch syntax, arity, declaration and sampler errors that otherwise only appear as a
failed material compile in the editor. None of them validates the picture.

## Ground detail in PCG

`GetGroundDebrisPlacements` (`TemperateHillsGroundDebris.cpp`) rides the grass PCG layer
instead of adding a fifth layer:

- Reuses `Assets->Rocks` and derives each instance scale from a **target edge length in cm**
  (`GroundDebrisSizeCm`), so swapping the rock set does not change the stone size.
- Aligns the mesh's own base centre and sinks it 30-54% of the edge length, which reads as
  bedded stone rather than grit lying on the surface.
- Gated by slope, a ~250 m dry-patch field, path distance and river bank mask, so stones
  arrive with the dry ground the material paints instead of dusting everything evenly.
- Decorative only: `NoCollision`, no harvest identity, reserved candidate-ID byte (`0x40`);
  `0x60` belongs to river pebbles and `0x80` to grass accents.

## Failure handling

- Symptom: the whole ground renders as the default grey checkerboard, nothing else.
  - Locate: `Saved/Logs/FPSGAME.log` for `Failed to compile Material ... Default Material
    will be used in game`, and read the `(Node TextureSample) ...` lines under it.
  - Fix: correct the offending sampler type from the texture's compression settings; a
    material that fails to compile does not fall back per-node, it drops the entire surface
    to the default material. Then run `check_ground_samplers.py`.
- Symptom: ground reads as one flat tiled sheet.
  - Locate: family projections sharing a scale, or the macro variation scalar at 0.
  - Fix: give every family a different tiling, raise `GroundMacroStrength`, and check the
    base weight noise still varies across the map.
- Symptom: layer transitions look like soft gradients, not interlocking surfaces.
  - Locate: `GroundHeightBias` / `GroundHeightContrast`, or a family height map that is
    actually featureless.
  - Fix: raise the contrast and lower the bias; verify the family's height map has relief
    before trusting it in the blend.
- Symptom: bumpiness disappears past a few metres, or the near ground looks flat.
  - Locate: `GroundReliefFadeM` and `GroundReliefDepthCm`.
  - Fix: raise both, but keep the fade short enough that the march stays a near-field cost.
- Symptom: two relief patterns fight each other near a river.
  - Locate: the hill march's `(1 - vertex colour R)` gate.
  - Fix: the region that runs its own march has to zero the other one; never let both run.
- Symptom: terrain shading looks identical after a material rebuild.
  - Locate: whether the data asset points at the material that was rebuilt. The live one is
    `M_PebbleShoreGround`, not `M_TemperateGround`.
  - Fix: rebuild the material the data asset references, or update the reference.
- Symptom: a headless material rebuild "succeeds" but the editor still reports a compile error.
  - Locate: the commandlet never compiled the shader.
  - Fix: run the offline fxc/dxc check before trusting it.
