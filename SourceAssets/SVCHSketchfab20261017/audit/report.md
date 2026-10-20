# SVCh 308 - source asset audit (read-only)

**Asset:** `SVCh 308.fbx` - Sketchfab download, "Low-Poly SVCh 308" by TastyTony, CC-BY-4.0
**Primary file analysed:** `download/source/source/SVCh 308.fbx` - FBX 7400, created by *Blender (stable FBX IO) 2.79*
**Cross-check:** `download/svch.glb` (Sketchfab-generated glTF 2.0)
**Tool:** Blender 5.1.2, background mode, `bpy.ops.import_scene.fbx` with default settings
**Companion data:** [`measurements.json`](measurements.json) - every number below, machine-readable

> **Import note.** The FBX *does* import, but Blender 5.1's bundled `io_scene_fbx` crashes on this file's light node
> (`AttributeError: 'CyclesLightSettings' object has no attribute 'cast_shadow'`, removed in Blender 5.x).
> The import was therefore run with `blen_read_light` re-executed **in memory** minus that one line. No source file was
> modified; mesh, armature, materials and transforms are exactly what the default importer produces. All findings were
> cross-checked against the GLB.

---

## 0. Headline findings

| Area | Finding |
|---|---|
| **Overall size** | **107.31 x 29.61 x 6.49 cm** = **1.073 x 0.296 x 0.065 m** at 1 unit = 1 cm. Plausible for a 7.62x54R DMR (real SVCh ~1.15 m). |
| **Barrel** | **63.87 cm** breech-face to muzzle (0.639 m), or 56.9 cm to the start of the brake. Real SVCh barrel is 620 mm, so the model is 103 %. |
| **Units** | Native units are **centimetres**. FBX `UnitScaleFactor = 1.0` / `OriginalUnitScaleFactor = 1.0`, i.e. the file *declares* metres but the geometry is centimetres. **This is the main scale trap.** |
| **Imported world size** | In Blender the object lands at **9.64 x 2.66 x 0.72 m** because the node carries `Lcl Scaling = (8.980, 11.136, 8.980)` under a 100x armature. Needs a **0.1114** correction (section 2). |
| **Origin** | Origin sits **inside the receiver**, on the bore centreline in Y, **~95 mm behind the breech face** (cartridge base at x = 9.46). X = 0 is neither the muzzle nor the centre of mass - it is an arbitrary Sketchfab pivot. |
| **Coordinate frame** | Object space: **+X = forward (muzzle)**, **+Z = up**, **-Y = shooter's right**. UE projection `(x, -y, z)` gives `(forward, right, up)` exactly. |
| **Textures** | **NONE.** 0 image nodes, 0 UV layers, 0 vertex colours, 0 Texture/Video nodes in the FBX; 0 textures/images in the GLB. Flat PBR colours only - and the FBX lost even those. |
| **Bullet geometry** | **PRESENT** - 3 complete 7.62x54R cartridges (600 tris, 8.6 %) inside the magazine, on two dedicated bones. **Delete for a game weapon.** |
| **Bipod** | **ABSENT** - no bipod geometry exists. |
| **Topology** | Clean: 0 duplicate faces, 0 loose verts, 0 inverted shells, 3 degenerate faces, 173 boundary edges on 13 intentionally open shells. **Double-sided** (all 10 materials `doubleSided: true`). |
| **Rig** | 12 bones / 7 deforming, but the "skin" is **rigid**: all 3775 verts have exactly one group at weight 1.0. No blending, no deformation - a part hierarchy wearing a skin. |
| **Animation** | **None.** 0 actions, 0 animation curves. Every motion (bolt travel, selector throw, mag drop) must be authored. |
| **GLB is wrong** | The GLB applied the non-uniform node scale on a different axis: it is 24 % taller and 19 % narrower than the FBX. **Use the FBX.** |

---

## 1. Scene inventory

### 1.1 Objects

| Object | Type | Parent | Verts | Tris | Material slots | Dominant vertex group | Share | Local bbox (cm) |
|---|---|---|---:|---:|---|---|---:|---|
| `Armature` | ARMATURE | — | — | — | — | — | — | — |
| `Camera` | CAMERA | — | — | — | — | — | — | — |
| `Cube.004` | MESH | Armature | 3775 | 6963 | 10 slots | body | 74.2% | 107.3 × 6.5 × 29.6 |
| `Lamp` | LIGHT | — | — | — | — | — | — | — |

The FBX contains exactly **one mesh** (`Cube.004`, data `Cube.006`), **one armature** (`Armature`, 12 bones), plus a light and
a camera that Sketchfab left in the scene. In the GLB the same mesh is split into 10 primitives named
`Cube.004_Material.XXX_0`, one per material slot.

**Mesh totals:** 3775 verts / 10531 edges / 6963 faces - **100 % triangles** (0 quads, 0 ngons), all smooth-shaded with
custom split normals. World-space bbox in the imported Blender scene:
`min (-4.7346, -0.2061, -1.5027)` to `max (4.9014, 0.5165, 1.1558)` m.

### 1.2 Parts, bones and triangle budget

Part boundaries come from the 139 connected shells and the per-face dominant vertex group, so the tri counts below
**sum exactly to 6963**.

| Part | Bone | Tris | Islands | Size X×Y×Z (mm) | X range (mm) | Materials |
|---|---|---:|---:|---|---|---|
| **Receiver / body (upper + lower + stock tube + magwell)** | `body` | 1245 | 17 | 817.0 × 39.3 × 117.0 | -274 … 543 | M004, M005, M006, M007, M008, M010 |
| **Handguard** | `body` | 864 | 1 | 325.6 × 29.0 × 53.6 | 218 … 544 | M007 |
| **Barrel + muzzle device (one tube island)** | `body` | 516 | 1 | 541.8 × 22.0 × 31.4 | 191 … 733 | M005, M007 |
| **Stock (buttstock)** | `body` | 452 | 7 | 86.9 × 21.5 × 151.1 | -340 … -253 | M005, M006, M007 |
| **Pistol grip** | `body` | 204 | 1 | 100.6 × 20.0 × 123.6 | -91 … 10 | M005 |
| **Trigger blade** | `body` | 40 | 1 | 14.1 × 6.5 × 34.5 | 20 … 35 | M008 |
| **Trigger guard** | `body` | 210 | 4 | 71.1 × 15.2 × 38.9 | 9 … 80 | M007, M008 |
| **Magazine** | `mag` | 732 | 21 | 106.2 × 22.5 × 194.7 | 82 … 189 | M005, M007 |
| **Bolt / bolt carrier** | `bolt` | 154 | 3 | 115.7 × 21.0 × 40.3 | 77 … 193 | M006, M009 |
| **Charging handle** | `bolt` | 96 | 2 | 27.3 × 36.1 × 22.3 | 160 … 187 | M006, M009 |
| **Fire selector** | `selector` | 80 | 2 | 25.3 × 35.7 × 16.9 | -30 … -4 | M005 |
| **Magazine release** | `magrelease` | 68 | 1 | 43.1 × 27.8 × 41.7 | 34 … 77 | M005 |
| **Front sight (folding, hooded post)** | `body` | 406 | 7 | 54.0 × 32.0 × 78.7 | 504 … 558 | M005, M006, M008 |
| **Rear sight (folding aperture)** | `body` | 564 | 8 | 50.7 × 38.9 × 65.0 | -46 … 5 | M005, M006, M008 |
| **Picatinny rail** | `body` | 600 | 50 | 634.9 × 18.7 × 4.1 | -92 … 543 | M006 |
| **Cartridge / bullet geometry (3 rounds)** | `bullet + bullets` | 600 | 6 | 88.5 × 18.1 × 33.5 | 95 … 183 | M001, M002, M003 |
| **Bipod** | n/a | 0 | 0 | — | — | — |
| **Handguard small hardware (vents, screws, QD points)** | `body` | 132 | 7 | 356.3 × 30.5 × 46.4 | 200 … 556 | M005, M006, M008 |

**Notes on specific parts**

* **Receiver / body** - `Material.004` supplies the actual shell geometry: upper receiver 405 tris (open top for the bolt,
  plus an 87.5 x 17.5 mm ejection-port aperture), lower trigger housing 268 tris, stock tube 48 tris, front block 20 tris.
  Everything else counted here is rail base and small hardware that lives on the receiver.
* **Barrel and muzzle device are ONE shell** (island 14, 516 tris, x 19.14 to 73.33). The 70 mm brake is modelled as part
  of the same 24-sided tube, so it **cannot be detached** without cutting the mesh. There is no separate muzzle-device object.
* **Handguard** is a single clean 864-tri shell with five lightening slots; no barrel-nut or heat-shield geometry.
* **Bolt / carrier vs charging handle** both ride the `bolt` bone. The carrier is `Material.009` (70 tris) and is the piece
  visible through the port; the handle is the `Material.006` arm + knob on the **left (+Y)** flank.
* **Rear sight 564 tris / front sight 406 tris** are heavy for iron sights - together 14 % of the mesh.
* **Rail = 600 tris** for 47 teeth + 3 end caps: 12 tris per tooth, more than the real thing needs.
* **Cartridges = 600 tris (8.6 %)** in 6 shells (3 cases at 148 tris + 3 bullets at 52 tris). All are **interior**
  geometry that is never visible with the magazine inserted. **Delete.**

### 1.3 Shell inventory (top 30 by triangle count)

| # | Part (auto-labelled) | Bone | Tris | Verts | Materials | Bbox X / Y / Z (cm) | Closed |
|---:|---|---|---:|---:|---|---|---|
| 128 | handguard shell (5 slots) | `body` | 864 | 398 | M007 | 21.83…54.39 / -1.45…1.45 / 2.50…7.86 | yes |
| 14 | barrel + muzzle brake (single tube) | `body` | 516 | 246 | M005, M007 | 19.14…73.33 / -1.10…1.10 / 4.00…7.15 | yes |
| 122 | upper receiver shell (ejection-port side) | `body` | 405 | 219 | M004 | -10.32…21.85 / -1.48…1.52 / 1.25…7.25 | no |
| 102 | magazine body | `mag` | 276 | 145 | M007 | 8.25…18.87 / -1.01…1.01 / -14.54…4.62 | no |
| 123 | lower receiver / trigger housing | `body` | 268 | 150 | M004 | 7.94…20.65 / -1.39…1.39 / -2.63…2.58 | no |
| 0 | pistol grip | `body` | 204 | 104 | M005 | -9.06…1.00 / -1.00…1.00 / -11.05…1.31 | yes |
| 134 | rear sight tower | `body` | 164 | 84 | M006 | -3.90…0.47 / -1.28…1.28 / 8.50…10.69 | yes |
| 129 | trigger guard | `body` | 158 | 84 | M007 | 0.93…8.01 / -0.68…0.68 / -2.72…1.17 | no |
| 18 | cartridge (DELETE) | `bullets` | 148 | 78 | M003, M001 | 9.46…15.83 / -0.92…0.18 / 1.20…2.77 | no |
| 20 | cartridge (DELETE) | `bullets` | 148 | 78 | M003, M001 | 9.46…15.83 / -0.21…0.89 / 1.90…3.48 | no |
| 138 | cartridge (DELETE) | `bullet` | 148 | 78 | M003, M001 | 9.46…15.83 / -0.74…0.36 / 2.97…4.55 | no |
| 33 | stock skeleton (main) | `body` | 144 | 72 | M007 | -32.50…-25.52 / -0.90…0.90 / -7.58…6.58 | yes |
| 15 | top cover / dust cover | `body` | 124 | 64 | M006, M007 | -10.31…54.33 / -1.34…1.34 / 3.04…8.39 | yes |
| 32 | stock skeleton (lower arm) | `body` | 92 | 46 | M007 | -31.14…-25.29 / -0.58…0.58 / -7.69…3.04 | yes |
| 5 | rear sight left wing | `body` | 92 | 48 | M005, M006 | -4.60…-1.70 / -1.85…-1.30 / 8.57…11.47 | yes |
| 9 | rear sight blade carrier | `body` | 92 | 48 | M006 | -3.60…-2.33 / -0.44…0.44 / 9.56…13.74 | yes |
| 25 | bolt carrier body (lower lug) | `bolt` | 92 | 48 | M006 | 10.55…19.29 / -0.73…0.73 / 3.34…5.43 | yes |
| 30 | stock hinge / cheek riser | `body` | 80 | 42 | M005, M006 | -30.86…-26.36 / -0.56…0.56 / 3.69…5.30 | yes |
| 10 | front sight post | `body` | 80 | 42 | M006 | 50.41…51.62 / -0.38…0.38 / 9.43…13.71 | yes |
| 127 | gas block / front sight base | `body` | 80 | 42 | M005 | 52.73…55.79 / -0.60…0.60 / 6.67…8.39 | yes |
| 13 | receiver right-side detail (-Y knob) | `body` | 76 | 40 | M005, M007 | -11.81…-9.10 / 0.67…2.23 / 3.50…6.40 | yes |
| 135 | front sight hood base | `body` | 74 | 39 | M006 | 50.39…53.35 / -1.25…1.25 / 8.54…10.68 | yes |
| 36 | butt plate | `body` | 68 | 36 | M005 | -33.98…-30.34 / -1.08…1.08 / -7.70…7.41 | yes |
| 26 | stock sling tab (Material.010) | `body` | 68 | 36 | M006, M010 | -22.93…-21.33 / -1.64…1.08 / 0.87…2.72 | yes |
| 1 | mag release | `magrelease` | 68 | 36 | M005 | 3.42…7.73 / -1.39…1.39 / -5.59…-1.42 | yes |
| 23 | charging-handle arm + knob (left side) | `bolt` | 68 | 36 | M006 | 16.75…18.68 / 1.81…4.64 / 5.47…7.70 | yes |
| 11 | rear sight aperture ring + blade | `body` | 64 | 32 | M006 | -3.00…-2.54 / -0.49…0.49 / 13.55…14.77 | yes |
| 4 | rear sight base plate (rear) | `body` | 56 | 30 | M005, M008 | -3.65…-2.20 / -1.36…2.04 / 8.27…9.95 | yes |
| 3 | rear sight base plate (front) | `body` | 56 | 30 | M005, M008 | -1.27…0.19 / -1.36…2.04 / 8.27…9.95 | yes |
| 2 | front sight base plate | `body` | 56 | 30 | M005, M008 | 51.55…52.91 / -1.30…1.90 / 8.60…10.17 | yes |

The remaining 109 shells are 12-tri rail teeth, 20-tri magazine ribs, screws and pins. All 139 are listed in
[`measurements.json`](measurements.json) under `scene_inventory.islands`.

---

## 2. Real-world scale check

### 2.1 Measured dimensions

| Axis | Native units | If 1 unit = 1 cm | Object scale applied | Verdict |
|---|---:|---:|---:|---|
| Length (X) | 107.307 | **1.0731 m** | 9.636 m | plausible as cm |
| Height (Z) | 29.605 | **0.2961 m** | 2.658 m | plausible as cm |
| Width (Y) | 6.490 | **0.0649 m** | 0.723 m | plausible as cm |

### 2.2 Assumed unit scale

**1 native unit = 1 centimetre.** Justification:

1. `GlobalSettings.UnitScaleFactor = 1.0` and `OriginalUnitScaleFactor = 1.0`, so the FBX declares **metres**.
2. But the raw `Vertices` array in the FBX `Geometry` node spans **107.3 units** in X. Read as metres that is a
   **107-metre rifle**.
3. Read as centimetres it is **1.073 m**, matching the real SVCh (~1.15 m) to within 7 %.
4. The feature scale agrees: barrel OD 22 mm, muzzle opening 14.2 mm, pistol grip 84 x 20 mm, rail pitch 12.2 mm - all sane only
   in millimetres/centimetres.

**Conclusion: the FBX's declared unit (metres) is wrong by 100x. Treat the geometry as centimetres.**

### 2.3 Derived real-world numbers

| Measurement | Model | Real SVCh (7.62x54R) | Ratio |
|---|---:|---:|---:|
| Overall length | **1073 mm** | ~1155 mm | 93 % |
| Barrel (breech to muzzle) | **639 mm** | 620 mm | 103 % |
| Barrel (breech to brake start) | 569 mm | - | - |
| Overall height (sight top to mag floor) | **296 mm** | - | - |
| Sight radius | **538 mm** | - | - |

### 2.4 Scale verdict

> **PLAUSIBLE - with one caveat.** At 1 unit = 1 cm the model is a correctly sized rifle (1.073 m vs ~1.155 m real, -7 %).
> It is **not** a giant or a toy. **However**, the file's declared unit is metres, so a naive import that trusts
> `UnitScaleFactor` produces a 107 m gun, and Blender's importer *also* applies the stray node scale, landing at 9.64 m.
> Both are wrong. The corrective factor from the imported scene is **x 0.11136** (uniform), i.e. `1 / 8.9798`.

### 2.5 Why the imported numbers look wrong

Two independent scale errors stack up:

1. **Armature node** `Lcl Scaling = (100, 100, 100)` - the usual Sketchfab centimetre-to-metre factor.
2. **Mesh node** `Lcl Scaling = (8.980, 11.136, 8.980)` - a **non-uniform, non-round** scale baked into the original
   Blender 2.79 scene.

Net imported world scale = `(0.0898, 0.1114, 0.0898)`, giving 9.64 x 0.72 x 2.66 m.

The **non-uniform** part is the real problem: Y is 24 % larger than X/Z. In the FBX this stretches **width**
(correct-looking gun); in the GLB the same factor lands on **height** (24 % too tall, 19 % too narrow). For a clean
asset, export the mesh at **uniform scale 1 unit = 1 cm** and drop both node scales.

---

## 3. Pivot / origin and landmark positions

### 3.1 Where the origin sits

| Question | Answer |
|---|---|
| Along the length? | **x = 0 is ~95 mm behind the breech face** (cartridge base at x = 9.46) and **340 mm in front of the butt plate** - over the trigger / rear of the magwell, i.e. near the centre of the receiver. Not the muzzle, not the butt, not the centre of mass. |
| Across? | **y = 0 is exactly the bore centreline.** The model is symmetric about y = 0 through receiver and barrel; only the ejection port, charging handle and selector break it. |
| Vertically? | **z = 0 is 55.8 mm below the bore axis**, roughly the bottom of the receiver / top of the trigger guard. |
| Good game pivot? | **No.** For first person you want the pivot at the grip or receiver rear. Blender origin to grip centre = `(-4.8, 0, -6.6)` cm. |

Handedness matters for this asset, so note the measured asymmetry: the **ejection port is on -Y** (shooter's right,
x 9.5 to 18.25) and the **charging handle is on +Y** (shooter's left, x 15.95 to 18.68). A raycast from +Y at port height
hits solid receiver (`Material.004` at y = +1.523); the same ray from -Y reaches the bolt (`Material.009` at y = -1.01).
This is right-side ejection with left-side charging - the standard SVCh / Kalashnikov layout.

### 3.2 Landmark table

| Landmark | Object-space (cm) | Metres | Basis |
|---|---|---|---|
| Muzzle tip (bore exit) | 73.33, 0.00, 5.58 | 0.7333, 0.0000, 0.0558 | max X of the barrel tube |
| Muzzle cap centre | 73.14, -0.00, 5.58 | 0.7314, -0.0000, 0.0558 | centroid of the 30 muzzle-face verts |
| Bore axis point | 0.00, 0.00, 5.58 | 0.0000, 0.0000, 0.0558 | least-squares fit of 12 barrel rings |
| Bore axis direction | (1, 0, 0) | — | slope 0.000000 in Y and Z |
| Rear sight aperture centre | -2.77, 0.00, 14.16 | -0.0277, 0.0000, 0.1416 | centre of the 4.9 × 2.0 mm ring opening |
| Front sight post tip | 51.00, 0.00, 14.18 | 0.5100, 0.0000, 0.1418 | top of the front post |
| Ejection port centre | 13.88, -1.01, 6.12 | 0.1388, -0.0101, 0.0612 | mid-point of the −Y wall aperture |
| Magazine interface (well plane) | 13.57, 0.00, 4.62 | 0.1357, 0.0000, 0.0462 | top face of the magazine body |
| Pistol grip centre | -4.84, 0.00, -6.57 | -0.0484, 0.0000, -0.0657 | bbox centre of the grip island |
| Trigger blade centre | 2.54, 0.00, -0.56 | 0.0254, 0.0000, -0.0056 | bbox centre of the trigger blade |
| Charging handle (rest) | 17.76, 2.73, 6.59 | 0.1776, 0.0273, 0.0659 | bbox centre of the handle + knob |
| Charging handle (full rear) | 10.04, 2.73, 6.59 | 0.1004, 0.0273, 0.0659 | rest − 77.2 mm bolt stroke |
| Stock butt plate | -33.60, 0.00, 5.94 | -0.3360, 0.0000, 0.0594 | bbox centre of the rear pad |

Additional interface points:

| Landmark | Object-space (cm) | Notes |
|---|---|---|
| Bore axis line | point (0, 0, 5.5755), direction **(1, 0, 0)** | Least-squares fit over 12 barrel rings; slope **0.000000** in Y and Z - bore perfectly axis-aligned, no droop or cant. |
| Muzzle face | x = 73.327, outer ring **D 20.9 mm**, inner opening **D 14.2 mm** | 4 concentric rings at radii 7.09 / 8.26 / 8.97 / 10.44 mm; the brake body itself is 19.4 x 27.7 mm at the last ring. |
| Ejection port | centre (13.88, -1.01, 6.12), x 9.5 to 18.25, z 5.25 to 7.00 | **87.5 x 17.5 mm** aperture on the -Y wall. |
| Magazine well | top face z = 4.625, x 7.94 to 20.65, y +/-1.39 | The mag body's top face is the interface plane. |
| Trigger pivot (est.) | (2.54, 0, 1.17) | Top of the trigger blade where it enters the receiver. |
| Butt plate | centre (-33.60, 0, 5.94), x -33.98 to -33.23 | 7.5 mm thick, 21.5 x 15.1 mm. |
| Charging handle travel | rest x = 17.76 to full-rear x = **10.04** | **77.2 mm** rearward (-X). **Derived, not authored** - the file has no animation; 77.2 mm is the 7.62x54R cartridge OAL, the standard bolt stroke. |

---

## 4. Orientations

### 4.1 Object-space axes (whole model)

| Axis | Meaning | Evidence |
|---|---|---|
| **+X** | **Forward, toward the muzzle** | Muzzle at x = +73.33, butt at x = -33.98; bore direction (1, 0, 0). |
| **+Z** | **Up** | Rail top at z = +9.48, sights at z = +14.2 to +14.8, magazine hangs to z = -14.84. |
| **-Y** | **Shooter's right** | Ejection port on -Y; charging handle on +Y. |
| **+Y** | Shooter's left | |

The model is stored **Z-up, right-handed**, which is already Blender-native. FBX `GlobalSettings` says `UpAxis = 1`
(Y-up) with `FrontAxis = 2`, so the exporter used the standard Blender-to-FBX axis swap and Blender's importer reverses
it correctly.

### 4.2 Per-part forward / up / right

All parts are rigid children of the same object, so **every part shares one local frame**: forward = +X, up = +Z,
right = -Y. No part carries its own rotation. The only exceptions are the bones, whose own axes differ.

### 4.3 Armature bones as authored

The armature object carries `Lcl Rotation = (-90.000, -0.000, -90.000)` and `Lcl Scaling = (100, 100, 100)`; the mesh
object carries `Lcl Rotation = (-90.000, 0, 0)` and `Lcl Scaling = (8.980, 11.136, 8.980)`. The rest positions below are
expressed **in mesh space** (both node transforms undone), so they compare directly with the geometry.

| Bone | Parent | Authored Lcl Translation | Authored Lcl Rotation (°) | Rest head (cm) | Rest tail (cm) | Length (cm) | Verts | Role |
|---|---|---|---|---|---|---:|---:|---|
| `body` | — | (0.000, 0.000, 0.000) | (90.000, -0.000, 0.000) | (26.89, -0.00, 3.99) | (46.21, 0.00, 3.99) | 19.32 | 2800 | root / whole gun |
| `bolt` | `body` | (-0.197, -1.755, -0.000) | (0.000, 0.000, 0.000) | (7.34, -0.00, 6.18) | (18.48, 0.00, 6.18) | 11.14 | 138 | bolt carrier + charging handle |
| `bolt_end` | `bolt` | (0.000, 1.000, 0.000) | (0.000, 0.000, 0.000) | (18.48, 0.00, 6.18) | (29.61, 0.00, 6.18) | 11.14 | 0 | bolt tail helper (no verts) |
| `mag` | `body` | (0.241, -0.802, -0.000) | (-0.000, 0.000, -89.931) | (17.96, -0.00, 1.31) | (17.97, 0.00, -6.72) | 8.03 | 433 | magazine |
| `bullet` | `mag` | (0.705, -0.230, -0.000) | (-0.000, -0.000, 89.931) | (10.10, -0.00, 3.86) | (17.16, 0.00, 3.86) | 7.05 | 108 | single cartridge #1 |
| `bullet_end` | `bullet` | (0.000, 0.633, 0.000) | (0.000, 0.000, 0.000) | (17.16, 0.00, 3.86) | (24.21, 0.00, 3.86) | 7.05 | 0 | helper (no verts) |
| `bullets` | `mag` | (0.696, -0.086, 0.000) | (-0.000, -0.000, 89.931) | (10.21, -0.00, 2.26) | (17.26, 0.00, 2.26) | 7.05 | 216 | two stacked cartridges #2/#3 |
| `bullets_end` | `bullets` | (0.000, 0.633, 0.000) | (0.000, 0.000, 0.000) | (17.26, 0.00, 2.26) | (24.31, 0.00, 2.26) | 7.05 | 0 | helper (no verts) |
| `magrelease` | `body` | (0.466, -1.761, -0.000) | (97.236, 90.000, 0.000) | (7.28, 0.00, -1.20) | (6.77, 0.00, -5.17) | 4.00 | 36 | mag release |
| `magrelease_end` | `magrelease` | (0.000, 0.359, 0.000) | (0.000, 0.000, 0.000) | (6.77, 0.00, -5.17) | (6.27, 0.00, -9.14) | 4.00 | 0 | helper (no verts) |
| `selector` | `body` | (0.145, -2.512, -0.000) | (171.343, 90.000, 6.925) | (-1.08, -0.00, 2.37) | (-3.02, 0.00, 1.84) | 2.01 | 44 | fire selector |
| `selector_end` | `selector` | (0.000, 0.180, 0.000) | (0.000, 0.000, 0.000) | (-3.02, 0.00, 1.84) | (-4.95, 0.00, 1.30) | 2.01 | 0 | helper (no verts) |

**Bone-space axis convention (in mesh space):**

| Bone | own +X | own +Y | own +Z |
|---|---|---|---|
| `body`, `bolt`, `bolt_end`, `bullet`, `bullets`, `*_end` | (0, 0, -1) | **(1, 0, 0) = forward** | (0, -1, 0) |
| `mag` | (-1, 0, 0) | (0, 0, -1) = down | (0, -1, 0) |
| `magrelease`, `selector` | (0, 1, 0) | approx (0, 0, +/-1) | - |

So `body` / `bolt` / `bullet` / `bullets` point **forward along their own +Y**, and the magazine bone points **down its
own +Y**. That is the standard Blender bone convention (bones point along local +Y) after the 2.79 FBX exporter's
`LimbNode` conversion.

**Authored Lcl Rotations** are the raw FBX values and look odd (`body` = 90 deg, `mag` = -89.93 deg, `selector` =
171.34 / 90 / 6.92 deg). They are the result of baking the Y-up-to-Z-up conversion into each bone's local space. The
*effective* rest orientation is what the mesh-space axes show, and those are clean and axis-aligned. **Use the
mesh-space axes, not the raw Euler values.**

**Helper bones:** `bolt_end`, `bullet_end`, `bullets_end`, `magrelease_end`, `selector_end` are zero-length extensions
carrying **no vertices**. They exist only so the exporter had a two-bone chain per part, and can be deleted.

---

## 5. Symmetry and cleanliness

| Metric | Value |
|---|---:|
| Vertices | 3775 |
| Edges | 10531 |
| Faces | 6963 |
| Triangles | 6963 |
| Shells (connected components) | 139 |
| Closed shells | 126 |
| Open shells | 13 |
| Non-manifold edges (all are boundary) | 173 |
| Boundary (open) edges | 173 |
| Non-manifold vertices | 0 |
| Loose vertices | 0 |
| Duplicate faces | 0 |
| Zero-area (degenerate) faces | 3 |
| Inverted shells | 0 |
| Edges with inconsistent winding | 5 |
| UV layers | 0 |
| Textures | 0 |
| Vertex colour layers | 0 |

### 5.1 What the numbers mean

* **Non-manifold: 173 edges, but every one is a *boundary* edge.** There are **0** true non-manifold edges (no edge
  shared by 3+ faces) and **0** non-manifold vertices. The mesh is closed shells plus 13 deliberately open ones.
* **The 13 open shells** are: upper receiver (28-edge loop around the ejection port and top opening), lower trigger
  housing (19 + 15-edge loops where it meets the receiver), magazine body (13-edge loop = floor plate), 3 cartridges x 2
  parts (7-edge loops at the case mouth), bolt carrier (9-edge loop at the front), trigger guard (9-edge loop) and 2
  magazine ribs (23-edge loops).
* **Inverted faces: 0.** Every closed shell has positive signed volume; no normal points inward.
* **Doubled faces: 0.** No two faces share the same vertex set.
* **Degenerate faces: 3.** Zero-area triangles out of 6963 (0.04 %). Harmless but worth cleaning.
* **Winding inconsistencies: 5 edges.** Five edges whose two faces wind the same way - a local defect, not a global flip.
* **Smooth shading:** all 6963 faces are smooth, with **custom split normals** baked in. That is why a low-poly model
  still reads as hard-surface. **Preserve custom normals on import** or the silhouette goes soft.

### 5.2 Single- vs double-sided

**Double-sided.** All 10 GLB materials declare `doubleSided: true`, and all 10 Blender materials import with
`use_backface_culling = False`. The FBX stores no material properties at all, so this is only knowable from the GLB.

**Recommendation:** thin parts (rail teeth, sight blades, cartridge cases, magazine ribs) genuinely need it, but for a
game asset it is cheaper to give those parts real thickness and enable backface culling. As shipped the mesh doubles the
pixel/overdraw cost.

---

## 6. Material summary

> ### There are NO textures in this asset.
> Zero image nodes, zero UV layers, zero vertex-colour layers, zero `Texture`/`Video` objects in the FBX, and
> `textures = 0 / images = 0` in the GLB. Every material is a **flat Principled BSDF with a constant base colour**.
> The FBX export additionally **lost even that**: all ten `Material` nodes have empty `Properties70`, so Blender shows
> every slot as default 0.8 grey / metallic 1.0 / roughness 0.5528 / a Normal Map node with no image.
> The colours below are the **authored values recovered from the GLB** (same scene, exported by Sketchfab, which
> preserved them).

| Slot | Material | Base colour linear (RGB) | sRGB hex | Metallic | Roughness | Specular | Alpha | Tris | Used by |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 0 | `Material.005` | 0.0119, 0.0119, 0.0119 | `#1C1C1C` | 0.00 | 1.000 | 0.00 | 1.00 | 1306 | barrel, pistol grip, mag release, butt plate, sight bases, gas block, selector levers |
| 1 | `Material.008` | 0.0363, 0.0363, 0.0363 | `#363636` | 0.00 | 1.000 | 0.00 | 1.00 | 352 | small hardware: trigger blade, detents, screws, pins, sight screws |
| 2 | `Material.006` | 0.0297, 0.0297, 0.0297 | `#303030` | 0.00 | 1.000 | 0.00 | 1.00 | 1552 | picatinny rail teeth + rail base, top cover, front/rear sight posts, charging-handle knob |
| 3 | `Material.007` | 0.0176, 0.0176, 0.0176 | `#242424` | 0.00 | 1.000 | 0.00 | 1.00 | 2290 | barrel, stock body, magazine body, handguard shells |
| 4 | `Material.002` | 0.8000, 0.8000, 0.8000 | `#E7E7E7` | 0.00 | 0.958 | default | 1.00 | 156 | bullet projectile nose (copper) - DELETE |
| 5 | `Material.003` | 0.8000, 0.8000, 0.8000 | `#E7E7E7` | 0.00 | 0.958 | default | 1.00 | 48 | cartridge rim / neck ring - DELETE |
| 6 | `Material.001` | 0.8000, 0.8000, 0.8000 | `#E7E7E7` | 0.00 | 0.958 | default | 1.00 | 396 | cartridge case / bullet body (brass) - DELETE |
| 7 | `Material.009` | 0.0400, 0.0388, 0.0373 | `#383736` | 0.00 | 0.958 | 0.00 | 1.00 | 70 | bolt carrier / bolt (seen through the ejection port) |
| 8 | `Material.010` | 0.0119, 0.0119, 0.0119 | `#1C1C1C` | 0.00 | 1.000 | 0.00 | 1.00 | 52 | stock left-side sling/adjuster tab |
| 9 | `Material.004` | 0.0194, 0.0194, 0.0194 | `#262626` | 0.00 | 1.000 | 0.00 | 1.00 | 741 | receiver shell: upper receiver (ejection port), lower trigger housing, magwell, stock tube |

### 6.1 Palette

A **nine-shade dark grey/black palette** plus three near-white "brass" slots for the cartridges:

| Group | Materials | sRGB |
|---|---|---|
| Dark body | M005, M010 | `#1C1C1C` |
| Receiver / furniture | M004, M007 | `#262626`, `#242424` |
| Rail / top cover | M006 | `#303030` |
| Hardware | M008 | `#363636` |
| Bolt | M009 | `#383736` (slightly warm) |
| Cartridges (DELETE) | M001-M003 | `#E7E7E7` |

The five body colours span only **#1C1C1C to #363636** - a 0.012 to 0.036 linear range. That is very dark and very flat;
with no textures the gun will read as a silhouette in most lighting. Expect to add grunge/wear maps or at least widen
the value spread.

### 6.2 Metallic / roughness

* **Metallic = 0.0 for all ten** materials. The asset is entirely dielectric - there is no metal anywhere, despite being
  a rifle. For a gun this is wrong: receiver, barrel and bolt should be around 0.8 to 1.0 metallic.
* **Roughness** 1.0 for the seven body materials, 0.958 for M009 and the cartridges. Effectively fully rough.
* **Specular = 0.0** via `KHR_materials_specular` on 7 of 10. Combined with metallic 0 and roughness 1 these surfaces
  are almost pure diffuse and will look like matte plastic, not steel.
* **Alpha = 1.0 everywhere**, `alphaMode = OPAQUE`. No transparency needed or present.

### 6.3 Material to part map

| Material | Parts |
|---|---|
| `Material.004` | upper receiver shell (with ejection port), lower trigger housing, stock tube, magwell |
| `Material.005` | barrel, pistol grip, mag release, butt plate, front/rear sight bases, gas block, selector levers |
| `Material.006` | rail teeth + rail base, top cover, sight posts, charging-handle arm/knob |
| `Material.007` | barrel, stock body, magazine body, handguard shell |
| `Material.008` | trigger blade, detents, screws, pins, sight inserts |
| `Material.009` | bolt carrier (the part visible through the ejection port) |
| `Material.010` | stock left-side sling/adjuster tab |
| `Material.001`-`.003` | the 3 cartridges - **delete** |

The mapping is **not** clean 1:1: `Material.005` and `Material.007` both cover the barrel, and `Material.005` also covers
the grip and the butt plate. Any re-material pass needs per-face work, not per-object assignment.

---

## 7. Sight line

### 7.1 Geometry

| Quantity | Value |
|---|---:|
| Bore axis height | z = **5.5755 cm** |
| Rear sight aperture centre | z = **14.16 cm** |
| Front sight post tip | z = **14.18 cm** |
| Sight line height | z ~ **14.17 cm** |
| **Height above bore axis** | **8.59 cm = 85.9 mm** |
| Sight radius (rear to front) | **53.8 cm = 537.7 mm** |

85.9 mm over bore is high but not absurd for a railed DMR with a folding sight tower - roughly the height of an Aimpoint
on a riser, which is exactly what this rail is for. The two sights agree to within 0.2 mm, so the **sight line is level
and parallel to the bore** - a good, usable setup.

### 7.2 Are the sights usable?

**Yes - both are genuine open apertures**, verified by raycasting through them on a 0.375 mm grid:

| Sight | Opening | Shape |
|---|---|---|
| **Rear** | **4.9 mm wide x 2.0 mm tall** (z 14.05 to 14.25) | Hexagonal ghost-ring aperture, centred on y = 0 |
| **Front** | **7.9 mm clear width x 2.0 mm** (z 14.20 to 14.40) | Hooded post: two side windows with the post itself in the centre |

Both apertures are **centred on y = 0** and line up on the bore axis, so the iron sights are functionally correct.

**Caveat:** at 2.0 mm tall these openings are slits, not circles - a real ghost ring is 2 to 4 mm in diameter. The rear
aperture is a hexagonal hole only 2 mm high and will read as a thin slot in first person. If the sights are meant to be
used, open the rear aperture to at least 3 mm diameter. There is also **no elevation or windage adjustment** modelled;
the sights are fixed.

### 7.3 Rail

47 teeth at **12.16 mm pitch** (MIL-STD-1913 is 10 mm, so 22 % coarse), tooth 6.2 mm / slot 5.96 mm, top plane
z = 9.4795, spanning x -9.19 to 54.30 (**634.9 mm** of rail). The rail is continuous over receiver and handguard, so an
optic can mount anywhere along it - clearly the intended use, with the folding iron sights as backup.

---

## 8. Red flags and action list

| # | Issue | Severity | Action |
|---|---|---|---|
| 1 | **No textures, no UVs** - flat colours only, and the FBX lost even those | High | Re-author materials or bake. Add UVs before any texture work. |
| 2 | **All materials metallic = 0, specular = 0, roughness = 1** - reads as matte plastic | High | Set metal parts to metallic 0.8-1.0, roughness 0.25-0.45. |
| 3 | **3 cartridges present** (600 tris, 2 bones) | Medium | Delete the 6 cartridge shells plus `bullet` / `bullets` / `*_end` bones. |
| 4 | **Declared unit is metres but geometry is centimetres** | Medium | Force 1 unit = 1 cm on import; never trust `UnitScaleFactor` here. |
| 5 | **Non-uniform node scale (8.98, 11.14, 8.98)** | Medium | Bake to uniform scale. The GLB already got this wrong (24 % too tall). |
| 6 | **No animation at all** - 0 actions | Medium | Author bolt travel (77.2 mm), selector throw, mag drop. |
| 7 | **Pivot is ~95 mm behind the breech face**, mid-receiver | Low | Re-pivot to grip or receiver rear for FPS use. |
| 8 | **Double-sided everywhere** | Low | Give thin parts thickness, enable backface culling. |
| 9 | 3 degenerate faces, 5 inconsistent-winding edges | Low | Cleanup pass in Blender. |
| 10 | Rail pitch 12.16 mm vs 10 mm spec | Low | Cosmetic; matters only if real rail accessories are snapped on. |
| 11 | 5 dead helper bones with 0 verts | Low | Delete on import. |
| 12 | Front + rear sights are 970 tris (14 %) | Low | Decimate or leave; acceptable for a hero weapon. |
| 13 | **No bipod** | Info | Not modelled; add if the design needs one. |
| 14 | Light and camera left in the FBX | Info | Strip on import (also the cause of the 5.1 importer crash). |

### Licensing

The GLB metadata records **`license: CC-BY-4.0`**, author **"TastyTony"**, source
`https://sketchfab.com/3d-models/low-poly-svch-308-739390f40fef4b22ac9a71b72f7a95b8`. Attribution is **required** if this ships.

---

## 9. Method and reproducibility

All measurements come from `bpy` on the imported scene - no values are estimated or guessed.

| Script | Purpose |
|---|---|
| `work/extract.py` | Imports FBX/GLB, dumps objects, materials, bones, bboxes, weights |
| `work/fbxparse.py` | Parses the raw binary FBX (GlobalSettings, Models, Geometry, Deformers, Clusters) - proves `UnitScaleFactor` and the authored `Lcl` transforms |
| `work/analyze.py`, `work/landmarks.py` | Shell splitting, signed volumes, boundary loops, per-material bboxes |
| `work/precision.py` | Bore-axis least-squares fit, muzzle cap, bone frames in mesh space, ortho renders |
| `work/aperture.py`, `work/detail.py` | Raycast grids through the sights and the ejection port |
| `work/partsums.py` | Shell-to-part assignment; the per-part triangle counts |
| `work/assemble.py`, `work/gen_tables.py` | Build `measurements.json` and the tables in this report |

Reference renders (Workbench, orthographic, untextured): [`ortho_side_right.png`](ortho_side_right.png),
[`ortho_side_left.png`](ortho_side_left.png), [`ortho_top.png`](ortho_top.png).

### Coordinate conversion cheat-sheet

```
object space (cm)  --(x, y, z)/100-->  metres, Z-up, +X forward, -Y right
UE                 =  ( x, -y,  z )    with +X forward, +Y right, +Z up
Blender import     needs /8.9798 (uniform) to undo the baked node scale
```
