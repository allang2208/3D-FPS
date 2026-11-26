# New Firearm Registration Inventory — FPSGAME (UE 5.8.2)

**Scope:** read-only audit of `D:\FPS3D\FPSGAME`. No files modified.
**Templates:** `ue_m870` / `SK_M870_V7` (`/Game/Weapons/M870/Tactical20261015/`), `ue_super90` / `M4Super90` (`/Game/Weapons/Super90/Cransh20261006/`). `ue_svd` used as cross-check.
**Method:** full-tree text scans of `Source/FPSGAME/**/*.{h,cpp}`, `Content/ColdSteelData/*.json`, `Config/*.ini`, `Tools/**`, `SourceAssets/**`; JSON structure dumped via Python.

> **Counts that matter:** 40 C++ lines contain a literal `TEXT("ue_m870")` / `TEXT("ue_super90")`; 4 JSON files under `Content/ColdSteelData/` carry a per-weapon entry; 1 generated header (699 paths) and 1 cook list must be regenerated.

---

## 1. C++ hardcoded definition ids and mesh-path checks

### 1.1 Canonical identity constants (add your new gun here first)

| File:Line | Excerpt |
| --- | --- |
| `Source/FPSGAME/Weapons/M870WeaponAssets.h:6` | `inline constexpr const TCHAR* Definition=TEXT("ue_m870");` |
| `Source/FPSGAME/Weapons/Super90WeaponAssets.h:9` | `inline constexpr const TCHAR* Definition=TEXT("ue_super90");` |
| `Source/FPSGAME/Weapons/M870WeaponAssets.h:7` | `MeshPath=TEXT("/Game/Weapons/M870/Tactical20261015/SK_M870_V7.SK_M870_V7")` |
| `Source/FPSGAME/Weapons/Super90WeaponAssets.h:10` | `MeshPath=TEXT("/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7.SK_Super90_V7")` |

### 1.2 Character class / predicates — `Source/FPSGAME/FPSGAMECharacter.h`

The whole firearm family hinges on three inline predicates; every downstream system reads them.

| Line | Excerpt |
| --- | --- |
| 86 | `bool IsSuper90Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_super90"); }` |
| 87 | `bool IsM870Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_m870"); }` |
| 88 | `bool IsTubeShotgunWeapon() const { return IsSuper90Weapon() \|\| IsM870Weapon(); }` |
| 231 | `IsMuzzleSuppressed()` — `...(IsSuper90Weapon()&&MuzzleVariant==TEXT("shotgun_suppressor"))` |
| 615 | `void SetM870Optic(const FString& Variant);` (declaration only; impl in `M870OpticVisual.cpp:33`) |

`IsTubeShotgunWeapon()` is the single widest hook: it gates viewmodel mesh choice, animation remap, pellet count, reload path, crosshair, sprint family and server authority.

### 1.3 Mesh-path prefix / equality checks (non-generated)

| File:Line | Excerpt | Purpose |
| --- | --- | --- |
| `Weapons/TubeShotgunAssets.h:10` | `{return Definition==Super90WeaponAssets::Definition\|\|Definition==M870WeaponAssets::Definition;}` | `Supports(FString)` — family gate |
| `Weapons/TubeShotgunAssets.h:12` | `{return Definition==FName(Super90WeaponAssets::Definition)\|\|Definition==FName(M870WeaponAssets::Definition);}` | `Supports(FName)` |
| `Weapons/TubeShotgunAssets.h:14` | `{return Path==Super90WeaponAssets::MeshPath\|\|Path==M870WeaponAssets::MeshPath;}` | `MatchesMesh` — **exact equality, not prefix** |
| `Weapons/M870FurnitureAssets.cpp:40` | `if(!Mesh\|\|!Mesh->GetPathName().StartsWith(TEXT("/Game/Weapons/M870/CommonFurniture20261016/")))return FString();` | **the only `StartsWith("/Game/Weapons/M870/…")` in the codebase** |
| `Skills/QuickCombatRifleMotion.h:28` | `if (MeshPath.Contains(TEXT("/Super90/"))) return FVector(.030971f, 5.224671f, 51.443630f);` | quick-melee butt-plate anchor |
| `Weapons/CasingPortCalibration.h:32` | `{TEXT("/Weapons/Super90/"), FVector(2.250000, -1.300557, 2.240414), TEXT("WPN_root"), 1.0f}, // super90` | **ejection port missing for M870** — falls back to default |
| `Characters/FPSPlayerBodyEquipment.cpp:143` | `const bool bSuper90=Asset->GetPathName()==Super90WeaponAssets::MeshPath;` | exact match → M870 never gets this branch |
| `Characters/FPSPlayerBodyMotion.cpp:512` | `if(TubeShotgunAssets::MatchesMesh(Binding.Definition.Mesh.ToSoftObjectPath().ToString()))` | third-person loose-shell hide |
| `Characters/FPSPlayerBodyEquipment.cpp:555` | `const bool ParkedShell=TubeShotgunAssets::MatchesMesh(...) && MaterialSlotName==Super90WeaponAssets::LooseShellMaterial;` | |
| `Weapons/Super90SupportArmNode.cpp:37` | `bEnabled=Asset && TubeShotgunAssets::MatchesMesh(Asset->GetPathName());` | IK support-arm node |
| `Weapons/FPSWeaponFXComponent.cpp:367,493,1329` | three `TubeShotgunAssets::MatchesMesh(...)` guards | casing mesh / muzzle FX / tracer |
| `Weapons/M870PoseAudit.cpp:98` | `if(!Mesh\|\|!GetPathNameSafe(Mesh->GetSkeletalMeshAsset()).Contains(TEXT("SK_M870")))` | audit-only |
| `UI/M4GunsmithPreview.cpp:138` | `const bool bSuper90=TubeShotgunAssets::MatchesMesh(Asset->GetPathName());` | preview bounds |
| `UI/ColdSteelWeaponIcons.cpp:69` | `if(I.Definition==M870WeaponAssets::Definition)Result+=TEXT("\|gun_only=2");` | icon cache key |
| `Weapons/ShotgunWireAudit.cpp:122` | `bool Clean=Mesh->GetPathName()==M870WeaponAssets::MeshPath;` | audit-only |

Contrast — other families use **prefix** checks; if you copy an older gun instead of the shotguns you'll copy this pattern:

`Weapons/HK416WeaponAssets.h:16`, `Weapons/A762WeaponAssets.h:13`, `Weapons/PKMLowpolyWeaponAssets.h:28`, `Weapons/LMG201WeaponAssets.h:44`, `Weapons/SVDWeaponAssets.h:27`, `Movement/DoorPushPoseLayer.cpp:89`, `Weapons/M4TacticalSprintComponent.cpp:31,33,35`.

### 1.4 Gunplay / weapon handling — `Source/FPSGAME/FPSGAMECharacter.cpp`

| Line | Excerpt |
| --- | --- |
| 573–575 | `if (IsTubeShotgunWeapon()) { ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,IsM870Weapon()?M870WeaponAssets::MeshPath:Super90WeaponAssets::MeshPath); ... }` |
| 581 | `QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*(IsM870Weapon()?M870WeaponAssets::AnimationPath(TEXT("quick_melee")):...))` |
| 598 | `if(IsTubeShotgunWeapon())Super90WeaponAssets::SetLooseShellVisible(AKMViewmodel,false);` |
| 624–625 | `Super90WalkAnimation=IsTubeShotgunWeapon()?LoadAKMAnimation(TEXT("A_AKM_walk")):nullptr;` (run likewise) |
| 725–726 | Sprint family: `: IsM870Weapon() ? ERifleSprintWeapon::M870 : IsSuper90Weapon() ? ERifleSprintWeapon::Super90` |
| 2540 | `return IsTubeShotgunWeapon()?FMath::Max(TubeShotgunAssets::MinimumInterval(ActiveInventoryWeaponDefinition),Interval):Interval;` |
| 2719 / 2963 | `NativePelletCount=IsTubeShotgunWeapon()?Super90WeaponAssets::PelletCount:1` — **8 pellets hardwired to the Super90 namespace for both guns** |
| 3332–3341 | `LoadAKMAnimation` shotgun remap: `aim→idle, aim_fire→fire, reload→reload_continuous, reload_empty→reload_full`; `if(IsM870Weapon()&&Clip==TEXT("fire_last"))Clip=TEXT("fire");` |
| 3437–3455 | `LoadAKMSound` shotgun cue map; M870 → `M870WeaponAssets::SoundPath(Cue)`; else literal `TEXT("/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_%s.S_Super90_%s")` |

Family implementation files (whole-file, all M870-specific):
`FPSGAMECharacterM870.cpp` (45 lines — pump rate/cues/interrupt), `FPSGAMECharacterSuper90.cpp` (per-shell reload clock), `FPSGAMECharacterReloadCamera.cpp:57–81`, `FPSGAMECharacterReload.cpp:88,139,152`.

### 1.5 ADS / framing / recoil / reload handoff

| File:Line | Excerpt |
| --- | --- |
| `Weapons/RifleHipFraming.cpp:12` | `return (Definition == TEXT("ue_super90") \|\| Definition == TEXT("ue_m870")) \|\| Definition == TEXT("ue_m4a1") …` (`Supports()` whitelist) |
| `Weapons/RifleHipFraming.cpp:26` | `if (Definition == TEXT("ue_m870")) return FVector(-1.900510f, 1.680418f, 9.498009f);` (per-weapon wrist offset) |
| `Weapons/RifleHipFraming.cpp:32` | `else if (Definition == TEXT("ue_super90")) Forward = 6.f;` |
| `Weapons/RifleHipFraming.cpp:92` | `GunUpAxis = (Definition == TEXT("ue_super90") \|\| Definition == TEXT("ue_m870")) ? -FVector::RightVector : FVector::UpVector;` |
| `Weapons/RifleAxialRecoil.h:11–18` | `ForWeapon()` — returns `EProfile::None` for both shotguns (no axial profile) |
| `Weapons/RifleReloadHandoff.h:14–17` | whitelist includes neither shotgun |
| `Weapons/WeaponReloadStages.cpp:42–43` | default arm returns generic `{54/60, 88/60, 130/60}` — shotguns bypass via `AdvanceSuper90Reload` |
| `Weapons/WeaponStatEvaluation.cpp:37,52` | `TubeShotgunAssets::Supports(...)` → clamps interval to `MinimumInterval` |
| `Weapons/Super90Spread.h:9–10` | pellet cone from `Super90WeaponAssets::PelletConeDegrees` |
| `Weapons/GunsmithSystem.cpp:337–345` | speedloader recalc: `if((D==Super90WeaponAssets::Definition\|\|D==M870WeaponAssets::Definition) && Part(...)==Super90SpeedloaderAssets::Id)` |
| `Weapons/GunsmithSystem.cpp:157–162` | `if(D==Super90WeaponAssets::Definition && Slot==TacticalDeviceVariants::SecondarySlot)` legacy slot migration |
| `Weapons/GunsmithSystem.cpp:203` | `if(!W\|\|W->Ammo!=TEXT("ammo_12g")\|\|...)` — **pellet spread only for `ammo_12g`** |

### 1.6 Gunsmith / quick-melee / attachment visuals

| File:Line | Excerpt |
| --- | --- |
| `Weapons/GunsmithModificationTier.h:32–34` | `((Weapon==TEXT("ue_super90")&&Id==TEXT("super90_extended_tube"))\|\|(Weapon==TEXT("ue_m870")&&Id==TEXT("m870_tube_extension")));` + `M870Trigger` |
| `Weapons/TacticalDeviceVariants.h:64–65` | `if(Definition==TEXT("ue_super90"))return TEXT("Super90"); if(Definition==TEXT("ue_m870"))return TEXT("M870");` |
| `Weapons/TacticalDeviceVariants.h:22–26` | `SupportsSecondary()` — **neither shotgun listed** (single underside mount) |
| `Weapons/M4DrumVisual.cpp:61,70,274–275` | `if(IsM870Weapon()){…M870TubeMagazineAssets…}` / `if(IsSuper90Weapon()){…}` |
| `Weapons/M4GunsmithVisual.cpp:34–35` | `if (IsM870Weapon()) { SetM870Optic(Variant); return; }` / Super90 |
| `Weapons/M4MuzzleVisual.cpp:40` | `if(IsSuper90Weapon())` — M870 has muzzle `false` only |
| `Weapons/M4HandstopVisual.cpp:60,69` | foregrip dispatch per gun |
| `Weapons/PhantomRearGripVisual.cpp:32,40` | rear-grip dispatch |
| `Weapons/SkeletonStockVisual.cpp:51,59` | stock dispatch |
| `Weapons/ThermalScopeVisual.cpp:13,32` | thermal optic dispatch |
| `Weapons/SVDGripProfiles.cpp:22–23` | grip profile dispatch (`IsSuper90Weapon()…` / `IsM870Weapon()…`) |
| `Weapons/TacticalDeviceComponent.cpp:522` | `Family=IsM870Weapon()?TEXT("M870"):IsSuper90Weapon()?TEXT("Super90"):…` |
| `Weapons/ThermalScopeAssets.h:21,26` | `if(D==TEXT("ue_m870"))return TEXT("/Game/Weapons/M870/Optics20261016/Meshes/SM_M870_thermal_scope");` (+`_selector`) |
| `UI/M4GunsmithLayout.cpp:349` | `:Weapon==TEXT("ue_m870")&&SlotKey==TEXT("magazine")&&Id==TEXT("m870_tube_extension")?TEXT("super90_extended_tube"):Id;` (icon reuse) |
| `UI/M4GunsmithLayout.cpp:355` | `\|\|(Weapon==TEXT("ue_m870")&&Id==TEXT("m870_lightweight_trigger_kit")))` → shared trigger pictogram |
| `UI/M4GunsmithOverview.cpp:101` | `if(...W->Ammo==TEXT("ammo_12g"))` → pellet-spread row |

### 1.7 Audio selection

| File:Line | Excerpt |
| --- | --- |
| `FPSGAMECharacter.cpp:3435–3455` | `LoadAKMSound` — full shotgun cue remap; M870 pump cues `PumpPull`/`PumpPush`/`Equip` |
| `Weapons/M870WeaponAssets.h:19–22` | `SoundPath()` → `/Game/Weapons/M870/Tactical20261015/Audio/S_M870_%s` |
| `Weapons/ShotgunSuppressorAssets.h:8` | `SoundPath=TEXT("/Game/Weapons/CommonShotgun/Suppressor20261015/Audio/S_Super90_Suppressed")` |
| `Weapons/Super90LoaderAudioReference.h:10–16` | 7 hardcoded loader contact cue paths + times |
| `Characters/FPSPlayerBodyGunEffects.cpp:85,264–265` | `AddBank(C->Super90LoaderSounds)`, shotgun shot-sound substitution |
| `Characters/FPSPlayerBodyGunEffects.cpp:290` | `PresentSuper90Shot(...)` — multicast entry used by **both** guns |
| `Multiplayer/ColdSteelPlayerState.cpp:1007,1154` | pellet-count divisor for hit-token cost & damage |

### 1.8 Third-person representation

| File:Line | Excerpt |
| --- | --- |
| `Characters/FPSPlayerBodyEquipment.cpp:143,156–160,555,610` | `bSuper90` exact-path flag; `M870_FactoryFurniture` / `M870_FactoryTubeCap` slot names; `S90_*` slot prefixes |
| `Characters/FPSPlayerBodyMotion.cpp:512–513` | `TubeShotgunAssets::MatchesMesh(...) → Super90WeaponAssets::SetLooseShellVisible(Mesh,false)` |
| `Characters/FPSPlayerBodyGunEffects.cpp:124,146,232,264–268` | shotgun rejected from generic shot FX; own multicast |
| `Weapons/FPSWeaponFXComponent.cpp:369–370` | `Super90CasingMesh=…SM_Super90_Casing` + `M_S90_12gauge` — **shared by M870** |
| `Weapons/FPSWeaponFXComponent.cpp:1211` | `const float Delay=M870WeaponAssets::PumpEject/…` |
| `Weapons/FPSWeaponFXComponent.cpp:1270` | `const bool Pump=bWorldGun?WorldGunDefinition==FName(M870WeaponAssets::Definition):…IsM870Weapon();` |
| `Weapons/M4TacticalSprintComponent.h:11` | `enum class ERifleSprintWeapon : uint8 { None, M4, AKM, QBZ191, ASH12, M16, PKM, SVD, Super90, M870 };` → **new enum member** |
| `Weapons/M4TacticalSprintComponent.cpp:57–72` | `if (Weapon==ERifleSprintWeapon::M870){…M870WeaponAssets::AnimationPath(Role)…}` / Super90 |
| `Weapons/WeaponActionCameraComponent.h:15` | `Super90Loader, Super90LoaderEmpty, Super90LoaderCycle` camera actions |
| `Multiplayer/ColdSteelPlayerState.h:186–199` | `RequestSuper90Shot` / `RequestSuper90Reload` / `RequestM870PumpInterrupt` RPC surface |
| `Multiplayer/ColdSteelSuper90Authority.cpp:79,91,165,308,347,420` | `M870WeaponAssets::Definition` + 5× `TubeShotgunAssets::Supports(...)` fan-outs |
| `Multiplayer/Super90NetworkTypes.h` | `FSuper90NetMagazine/FSuper90NetAmmoState/FSuper90ServerReload` payloads |

### 1.9 Inventory / icon / pickup lookups

| File:Line | Excerpt |
| --- | --- |
| `UI/ColdSteelWeaponIcons.cpp:52` | `Supports()` whitelist (see §4) |
| `UI/ColdSteelWeaponIcons.cpp:69` | `\|gun_only=2` cache-key suffix for M870 |
| `UI/ColdSteelWeaponIcons.cpp:239` | `case 8:Rig->SetSuper90Speedloader((I.Definition==Super90WeaponAssets::Definition\|\|I.Definition==M870WeaponAssets::Definition) && …)` |
| `UI/ColdSteelWeaponIconReadback.cpp:148` | `…\|\|Queue[0].Item.Definition==TEXT("ue_m870")` → `FrameVisiblePixels` |
| `UI/ColdSteelInventoryWidget.cpp:126` | `…\|\|I.Definition==TEXT("ue_m870")` → `FrameImportedTexture` |
| `UI/ColdSteelIconResources.cpp:146–147` | icon preload: `if(D==TEXT("ue_super90")){…}` / `if(D==M870WeaponAssets::Definition){…}` |
| `UI/ColdSteelIconResources.cpp:186,196,226,235,260,285,298,304,310` | per-attachment icon asset injection (9 branches) |
| `UI/ColdSteelIconResources.cpp:182` | `Family=D==TEXT("ue_akm")?…:TEXT("M4")` — shotgun family falls to `"M4"` default |
| `UI/ColdSteelPickupWeapon.cpp:28` | 16-term `!=` allowlist; `:36` flags re-init |
| `UI/ColdSteelPickupStudio.cpp:73` | duplicate 16-term allowlist |
| `UI/ColdSteelWarehouseModel.cpp:50` | `for (const TCHAR* Definition : {TEXT("ue_m870"), TEXT("ue_super90"), …})` — starting armory grant list |
| `UI/ColdSteelWarehouseModel.cpp:54` | magazine ternary: `(…==TEXT("ue_super90")\|\|…==TEXT("ue_m870"))?7:…` |
| `UI/ColdSteelWarehouseModel.cpp:56–59` | `{ if(!AddAmmoToState(State,TEXT("ammo_12g"),42))return false; }` |
| `UI/ColdSteelAmmoRuntime.cpp:212` | `I.InstanceId==WeaponId&&I.Definition==TEXT("ue_m870")` — pump-interrupt flag writer |
| `UI/ShotgunAmmoIconDiagnosisCommandlet.cpp:53` | `Gun.Definition=TEXT("ue_super90");Gun.LoadedAmmoType=TEXT("ammo_12g");` |

### 1.10 Whitelists that are easy to miss

| File:Line | Excerpt |
| --- | --- |
| `FPSGAMECharacterProfile.cpp:90` | `bInventoryWeaponReady=…\|\|I->Definition==TEXT("ue_super90")\|\|I->Definition==TEXT("ue_m870")\|\|…` — **without this the gun never equips** |
| `FPSGAMECharacterProfile.cpp:131` | per-gun visual flags (`bUseM4Infima`, `bUseQBZ191`, …) — shotguns set **none**; they rely on `IsTubeShotgunWeapon()` |
| `UI/ColdSteelWeaponIconCatalogCommandlet.cpp:25` | catalog-export definition list (see §4) |
| `Weapons/GunsmithModificationTier.h:34` | special-tier marking for `m870_lightweight_trigger_kit` |
| `Weapons/LegendaryTacticalStock.h:9–21` | `Family()` has no shotgun entry → `legendary_adjustable_tactical_stock` **silently unresolvable** (falls through to per-gun furniture classes instead) |
| `Weapons/FullAutoTrigger.cpp:17` | pistol-only (`ue_m1911`, `ue_pit_viper2011`) — irrelevant for shotguns |

---

## 2. Data files under `Content/ColdSteelData/` with per-weapon entries

Exactly **four** JSON files carry a per-weapon entry. Verified by recursive key walk over all 67 JSON files.

| # | File | Top-level container | Entry key | Location |
| --- | --- | --- | --- | --- |
| 1 | `items.json` | **object** (map, 227 entries, no wrapper) | `"ue_m870"` | L5356–5381 |
| 2 | `gunsmith.json` | `weapons` → **array**, member key `id` | `"id": "ue_m870"` | L9659–10222 |
| 3 | `combat-weapon-formulas.json` | **object** (map, flat) | `"ue_m870"` | L410 |
| 4 | `gun-assembly.json` | `recipes` → **array**, member key `output` | `"output": "ue_m870"` (recipe `id: "assemble_m870"`) | L2385 |

### 2.1 `items.json` — `ue_m870` field set (15 fields, verbatim order)

```
id, name, category, type, equipSlot, weaponType, weaponTypeTag,
isTwoHanded, stack_max, grid_w, grid_h, icon, ue_icon, stats, desc
```

Per AGENTS.md the project has **no** `rarity`/`grade` on equipment — the m870 entry correctly omits it. `stats` is an array of `{"name","value"}` (both strings).
Optional extras seen on other firearms (not required): `rangedType`, `icon_fallback`, `critDamageBonus`, `gunsmith_base_mag`, `gunsmith_parts`.

### 2.2 `gunsmith.json` — `ue_m870` field set (7 fields)

```
id, model, name, allowed, base, options, traits
```

`options` is `{"<slot>": [ {id, name, description, effects, stats}, … ]}`. `effects` is `[{"text","benefit"}]`; `stats` is a flat numeric map.
`default_parts` and `hit_stagger` are **optional** — only `ue_hk416` (and `ue_m16a2` for `hit_stagger`) use them; `ue_m870` has **neither**.

### 2.3 `combat-weapon-formulas.json` — `ue_m870` (L410)

```json
"ue_m870": {"base": 80, "enhanceFlat": 8,
  "attrs": [{"key":"con","base":1.6,"perEnhance":0.8},{"key":"wis","base":4.0,"perEnhance":1.2}],
  "source": "M870 (whole-cartridge aggregate)"}
```

### 2.4 `gun-assembly.json` — recipe `assemble_m870` (L2385)

Keys: `id, output, inputs, camera, look_at, position_tolerance_cm, angle_tolerance_deg, calibration_seconds, parts, body_mesh, body_position`.
`inputs` = ironIngot×16, copperIngot×5, wood×2, search_assembly_component_box×2; `parts` = 5 (`barrel, stock, pump, bolt, trigger`), each with `id, name, mesh, target[3], extent[3], loose[3], angle, radius`; `body_mesh = /Game/Weapons/M870/Tactical20261015/Assembly/SM_M870_Assembly_body`.

### 2.5 Related files that do **not** hold per-weapon entries

- `ammo_types.json` → `{"schema_version","types":[…]}`, keyed by **ammo** (`ammo_12g`, `ammo_12g_flechette`, `ammo_12g_slug` share `"group": "ammo_12g"`). A new gun on the same caliber needs nothing here; a new caliber needs all 3 tier rows plus `items.json` entries.
- `modular_outfits.json` → keyed by **mesh path** under `profiles`, not definition id: `"/Game/Weapons/M870/Tactical20261015/SK_M870_V7.SK_M870_V7": {"rig_profile":"Super90", "base":"/Game/Weapons/M870/Arms20261016/SK_M870_BareArmsV7…", "native_bare_arms":true, "hide_source_materials":[1,2,3], "shirt_covers":[0,1], "glove_covers":[2], "shirt":…, "gloves":…}`. **This is a required registration point** even though it is not id-keyed.
- `source-combat-items.json` → legacy keys `M870 短管型`, `Super90` (only used to derive formulas; not runtime).
- `provenance.json`, `warehouse_assets.json` → no weapon entries.

---

## 3. Weapon item definitions — `items.json` verbatim

Top-level is a **bare JSON object** (no wrapper): `{"ue_smoke_grey_capri": {…}, …, "ue_m870": {…}}`.

### 3.1 M870 weapon item — L5356–5381

```json
"ue_m870": {
  "id": "ue_m870",
  "name": "M870 Tactical",
  "category": "weapon",
  "type": "武器",
  "equipSlot": "weapon",
  "weaponType": "shotgun",
  "weaponTypeTag": "霰弹枪",
  "isTwoHanded": true,
  "stack_max": 1,
  "grid_w": 4,
  "grid_h": 2,
  "icon": "Icons/ue_m870.png",
  "ue_icon": "Icons/ue_m870.png",
  "stats": [
    { "name": "物理攻击", "value": "80" },
    { "name": "弹匣容量", "value": "7" }
  ],
  "desc": "雷明顿 870 系列的战术型泵动霰弹枪，采用管式弹仓和传统枪托。每次射击后拉动护木退壳，再前推完成供弹。适合近距离掌握节奏逐发射击；装填时从机匣下方逐发补弹，也可提前结束补弹。"
}
```

`ue_super90` (L4194–4219) is byte-for-byte the same schema; only `id`/`name`/`desc` differ.

### 3.2 Its ammo item — `ammo_12g`, L4302–4316

```json
"ammo_12g": {
  "id": "ammo_12g",
  "name": "12 号00 鹿弹",
  "category": "ammo",
  "type": "弹药",
  "stack_max": 60,
  "maxStack": 60,
  "grid_w": 1,
  "grid_h": 1,
  "rarity": "common",
  "icon": "Icons/Ammo12Gauge20261012/buckshot.png",
  "ue_icon": "Icons/Ammo12Gauge20261012/buckshot.png",
  "desc": "参考 LE133 00 的 12 号鹿弹。每发 8 颗弹丸，保留标准整发伤害与射程，无额外目标穿透和护甲穿透，适合近距离。",
  "world_mesh": "/Game/Items/Ammo12Gauge20261012/Meshes/SM_12G_Buckshot_Box.SM_12G_Buckshot_Box"
}
```

Note the asymmetry: **ammo keeps `rarity`; weapons do not.** `ammo_12g_flechette` (L4317) and `ammo_12g_slug` (L4332) sit immediately after, same shape.

---

## 4. Icon handling

### 4.1 `UColdSteelWeaponIcons::Supports()` — `Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp:52`

It is a **single-line `return` chain of 16 hardcoded ids**, not a list you can extend by data:

```
IsBow || ColdSteelMeleePreview::Supports || ProductionHarvestAssets::IsIconSubject
|| ColdSteelEquipmentIconMesh(I).IsValid()
|| (ue_m4a1 || ue_hk416) || ue_akm || ue_a762 || ue_lmg201 || ue_super90 || ue_m870
|| ue_svd || ue_pkm_lowpoly || ue_qbz191 || ue_ash12 || ue_m16a2
|| ((ue_m1911 || ue_g18 || ue_pit_viper2011) || (ue_dan_wesson715 || ue_rsh12))
```

If the new id is absent: no live render, silent fallback to the flat PNG, and a "生成中" placeholder. No crash, no log.

### 4.2 Catalog export list — `Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp:25`

Same 16 ids + melee/material subjects, with the governing comment at L20–22:
> "Every definition ColdSteelWeaponIcons::Supports must appear here: a weapon missing from this list has no catalog image…"

Default export **omits** `ue_super90.png`-only targets? No — both are present (`ue_m870`, `ue_super90` are the first two entries).

### 4.3 PNG directory convention

- **Path:** `Content/ColdSteelData/Icons/<definition>.png` — directory literal is built three ways, all equivalent:
  - `ColdSteelWeaponIconCatalogCommandlet.cpp:16` → `FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons")`
  - `ColdSteelInventoryWidget.cpp:119–120` → `TEXT("Icons/")+I.Definition+TEXT(".png")` under `…/ColdSteelData/`
  - `ColdSteelItemTooltip.cpp:124` → same
- **File name == definition id**, lowercase (`ue_m870.png`). No subfolders for weapons.
- **Size:** width is derived, height is fixed at **320**:
  `ColdSteelWeaponIcons.cpp:209` → `IconCanvasWidth=FMath::Max(256,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y)));`
  → `4×2` footprint ⇒ **640×320**. Measured on disk:

  | file | px | footprint |
  | --- | --- | --- |
  | `ue_m870.png` | **640×320** | 4×2 |
  | `ue_super90.png` | **640×320** | 4×2 |
  | `ue_svd.png` | 800×320 | derived 5×2 via `BaseFootprint` |
  | `ue_m4a1.png` | 800×320 | 5×2 |
  | `ue_pkm_lowpoly.png` | 800×320 | 5×2 |
  | `ue_rune_sword.png` | 384×768 | melee path, not firearms |

  Alpha bbox for `ue_m870` = `(29,103)-(611,217)`; `ue_super90` = `(29,96)-(611,224)` — both leave ~96 px top/bottom transparent, which is exactly what the framing fallback compensates for.
- **`.uasset` sidecar:** every weapon PNG has a sibling `<id>.uasset` (auto-generated import artifact). `ue_pkm_lowpoly.png` and `ue_super90.png` currently have **no** `.uasset` — inconsistent with the rest.
- **Generation:** `Tools/UI/build_weapon_catalog_icons.ps1` → `-run=ColdSteelWeaponIconCatalog -Definition=<id>`; output also mirrored to `SourceAssets/WeaponInventoryIcons20260913/export-<id>.log`.
- **Attachment icons** (separate convention, needed for the gunsmith panel): `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/`
  - per-weapon factory part: `<definition>_<slot>_<optionId>.png` e.g. `ue_m870_stock_false.png`, `ue_m870_reargrip_false.png`
  - shared/framed option: `<slot>_<optionId>.png` e.g. `magazine_super90_extended_tube.png`, `reload_device_super90_tube_loader.png`
  - category placeholder: `category_<slot>.png` (`category_trigger.png`, `category_magazine.png`, …)
  - **M870 currently ships 7 factory icons** (magazine, muzzle, optic, reargrip, reload_device, stock, underbarrel) and **no** `ue_m870_trigger_false.png`; it reuses the shared `trigger_m1911_lightweight_fast.png` (`M4GunsmithLayout.cpp:354–356`).

---

## 5. Gunsmith entry for `ue_m870` (`Content/ColdSteelData/gunsmith.json`, L9659–10222)

### 5.1 Envelope

| Field | Value |
| --- | --- |
| `id` | `ue_m870` |
| `model` | `M870` |
| `name` | `M870 Tactical` |
| `allowed` (8 slots, in order) | `optic`, `muzzle`, `trigger`, `underbarrel`, `stock`, `magazine`, `reload_device`, `tactical` |
| `default_parts` | **absent** (only `ue_hk416` uses it) |
| `traits` | 2 entries, both `"icon":"special"` |

Note: `allowed` has **no** `reargrip` (M870 has an integrated stock/rear-grip — 2026-10-17 audit `M870CompletionAudit20261017/offline_inventory.py:11` asserts this) and **no** `tactical_secondary` (see `TacticalDeviceVariants::SupportsSecondary`).
`slots` (global, L?) = `["optic","muzzle","magazine","reargrip","stock","trigger","tactical","tactical_secondary","underbarrel","reload_device","bipod"]`; `ue_m870.options` omits `reargrip`, `tactical_secondary`, `bipod`.

### 5.2 `base` block (13 keys, verbatim)

```json
{
  "ammo_item_id": "ammo_12g",
  "mag_size": 7,
  "ads_smooth": 12,
  "recoil": 290,
  "camera_shake": 120,
  "spread_mult": 1.2375,
  "fire_interval": 0.9,
  "reload_time": 1.65,
  "empty_reload_time": 7.066666666666666,
  "damage": 80,
  "bullet_speed": 380,
  "effective_range": 35,
  "stability_mult": 1
}
```

For reference, `ue_super90.base` differs in exactly 4 values: `spread_mult 2.25`, `fire_interval 0.06`, `reload_time 1.2692307692307692`, `empty_reload_time 5.435897435897435`.

### 5.3 `traits` (2 entries)

```json
[
  {"icon":"special","text":"泵动上膛：每发射击后完成后拉退壳与前推供弹。"},
  {"icon":"special","text":"管式弹仓逐发补弹，开火或瞄准可在当前入弹完成后结束装填。"}
]
```

⚠️ `Tools/Weapons/check_attachment_consistency.py:237–247` asserts that **every** weapon's traits contain a "可改造" slot-list line whose parsed labels equal `options ∪ allowed ∪ common_options ∪ {reargrip…}`. `ue_m870` (and `ue_super90`) have **no such line**, so this checker necessarily reports a violation for them — do not treat that as a regression from your new gun, and do not blindly satisfy it for shotguns.

### 5.4 Full option id list (ids + names, 30 entries)

| slot | count | `id` → `name` |
| --- | --- | --- |
| `optic` | 6 | `false`→原厂机械瞄具 · `holographic`→全息瞄准镜 · `eoth_holographic`→EOTH全息瞄准镜 · `panoramic_red_dot`→全景薄框红点瞄具 · `prism_scope_2x`→紧凑型二倍棱镜瞄具 · `lpvo_1_6x`→1–6× 低倍可变瞄准镜 |
| `muzzle` | 1 | `false`→原厂枪口 |
| `underbarrel` | 6 | `false`→泵动护木 · `vertical_foregrip`→垂直握把 · `canted_foregrip`→45°侧倾握把 · `tactical_vertical_foregrip`→战术垂直握把 · `prism_handstop`→棱镜阻手器 · `angled_foregrip`→共振二代前握把 |
| `stock` | 6 | `false`→原厂枪托 · `skeleton`→骨架枪托 · `core_stock`→镂空轻型枪托 · `qr_performance`→高性能后托 · `tactical_telescopic`→战术伸缩枪托 · `legendary_adjustable_tactical_stock`→可调式战术后托 |
| `magazine` | 2 | `false`→原厂管式弹仓 · `m870_tube_extension`→弹仓延长管 |
| `reload_device` | 2 | `false`→逐发装填 · `super90_tube_loader`→管式快速装填器 |
| `tactical` | 3 | `false`→无战术装置 · `laser`→红色激光镭射 · `flashlight`→战术手电筒 |
| `trigger` | 2 | `false`→原厂扳机套件 · `m870_lightweight_trigger_kit`→轻量化扳机套件 |

Plus **2 injected globals** merged by `UGunsmithSystem::Initialize` from `common_options`: `optic.thermal_scope` and `tactical.blessed_laser`. Merged optic set = the 6 above **+** `thermal_scope`.

Selected `stats` (the numbers a new gun must match to stay consistent — `check_attachment_consistency.py` enforces cross-gun byte equality for shared `(slot,id)`):

| option | `stats` |
| --- | --- |
| `m870_tube_extension` | `{"mag_delta": 3}` |
| `m870_lightweight_trigger_kit` | `{"fire_interval_mult":0.75,"recoil_mult":0.95,"stability_mult":1.05}` |
| `super90_tube_loader` | `{"reload_mult":1.5294117647058825,"empty_reload_mult":1.5294117647058825}` |
| `laser` | `{"hip_spread_mult":0.5,"ads_percent":-0.2}` |
| `legendary_adjustable_tactical_stock` | `{"recoil_mult":0.65,"stability_mult":1.3,"ads_percent":-0.1,"hip_spread_mult":1.15}` |
| `eoth_holographic` | `{"ads_percent":-0.05}` |

---

## 6. Build / tooling that enumerates weapons

| # | Path | What it enumerates | Action for a new gun |
| --- | --- | --- | --- |
| 1 | `Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h` (**generated, 699 paths, 714 lines**) | every literal `TEXT("/Game/…")` in `Source/FPSGAME/**/*.{h,cpp}` | Regenerate — see #2. M870 block at L551–574 (12 meshes, 4 profiles, body, optics, loader guide, tactical fits), Super90 at L652–667 |
| 2 | `Tools/Performance/generate_preload_registry.py` | `python generate_preload_registry.py --write` (default `--root Source/FPSGAME`); skips its own output; drops templates containing `%` and fragments ending in `/` or `_` | **Run after writing the new `<Gun>WeaponAssets.h`** — the registry is derived from your constants, so there is nothing to hand-edit |
| 3 | `Config/DefaultGame.ini:375–391` (`[/Script/UnrealEd.ProjectPackagingSettings]`) | `+DirectoriesToAlwaysCook=` lines | M870 is one line: `+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M870")` (L377); Super90 needs **8** because its assets are scattered (`Cransh20261006`, `GameDevAudio20261007`, `Optics20261007`, `Foregrips20261007`, `WS1Surface20261007`, `Speedloader20261007`, `TacticalBottom20261012`, `RearGrips20261012`, `CommonStocks20261013`, `ExtendedTube20261015`) + shared `CommonShotgun/*` |
| 4 | `Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp:65–88` | `ExpandRoots[]` — whole-subtree warm list (21 entries) | **Neither shotgun is listed**; they are covered only by the explicit literals in #1. A new gun whose assets live outside its one cooked folder would need a root here |
| 5 | `Tools/Weapons/check_attachment_consistency.py` (302 lines) | All `gunsmith.json` weapons: slot/allowed consistency, duplicate ids, required option fields (`id,name,description,effects,stats`), `stats` key allowlist (`KNOWN_KEYS` L33), description/effects cross-checks, cross-gun equality, traits↔slot-set, `items.json` 物理攻击/容量 vs `base.damage`/`base.mag_size` (L265–285) | **Runs automatically over any new weapon** — it fails if `items.json` stats disagree with `base`, or if a shared option's stats drift. `MODEL_TOKENS` (L37) whitelists model names; add yours or descriptions containing it will trip "残留未白名单数字" |
| 6 | `Tools/Weapons/dump_attachment_values.py` (343 lines) | `SHORT` dict L12–14 maps id→display name; iterates **all** `d['weapons']` | Add `'ue_<new>': '<Name>'` or the doc-generation raises `KeyError` |
| 7 | `Tools/UI/build_weapon_catalog_icons.ps1` | invokes the commandlet; `-Definitions <id>` for targeted export | Re-run with the new id (§4.3) |
| 8 | `SourceAssets/M870CompletionAudit20261017/offline_inventory.py:16–18,37–38` | asserts every `/Game/Weapons/M870/…` path in the generated registry exists on disk, and the cook line is present | Per-weapon audit script — copy the pattern for a new gun; not a shared registry |
| 9 | `Tools/Weapons/M870Icons20261017/build_and_export.ps1:14` | `-Definitions @('ue_m870')` | per-weapon |
| 10 | `SourceAssets/BenelliM4Super9020261006/publish_catalog.py` + `apply_runtime.py` | the *original* Super90 registration scripts — a complete, ordered checklist of every file touched (see §7) | best single reference for "what a new gun touches" |
| 11 | `Tools/Weapons/M870Icons20261017/Before/register_catalog.py` | the equivalent for M870: items→gunsmith→formulas→assembly→DefaultGame.ini | second reference |
| 12 | `SourceAssets/M870ThirdPerson20261017/install_furniture.before.py` | asserts the native mesh hash and the `M870_FactoryFurniture` slot exists before saving | pattern for reversible factory-section surgery |

`apply_runtime.py` is the most valuable single artifact: its 30 `edit(...)` calls in order are
`FPSGAMECharacter.cpp` (mesh/anim/quick-melee/reload/pellets) → `FPSGAMECharacter.h` (predicate+members) → `FPSGAMECharacterReload.cpp` → `FPSGAMECharacterProfile.cpp:79` (equip whitelist) → `RifleHipFraming.cpp:80–81` → `ColdSteelPickupStudio.cpp`/`ColdSteelPickupWeapon.cpp:82–83` → `ColdSteelWeaponIcons.cpp:84` → `ColdSteelIconResources.cpp:85–86` → `WeaponStatEvaluation.cpp:87` → `ColdSteelPlayerState.cpp:88–93`.

---

## 7. Minimum registration checklist for a new firearm

**Must-have (gun will not work without these)**
1. `Weapons/<Gun>WeaponAssets.h` — `Definition`, `MeshPath`, `AnimationPath()`, timing constants.
2. `FPSGAMECharacter.h` — `IsXWeapon()` + add to `IsTubeShotgunWeapon()` (and `IsMuzzleSuppressed` if it has a suppressor option).
3. `FPSGAMECharacterProfile.cpp:90` — equip whitelist (and `:131` family flags if it is not a shotgun).
4. `Content/ColdSteelData/items.json` — weapon entry + any new ammo entry.
5. `Content/ColdSteelData/gunsmith.json` — `weapons[]` entry with `allowed`/`base`/`options`/`traits`.
6. `Content/ColdSteelData/combat-weapon-formulas.json` — flat key with `base`/`enhanceFlat`/`attrs`.
7. `Content/ColdSteelData/modular_outfits.json` — `profiles["<MeshPath>"]` rig profile.
8. `Config/DefaultGame.ini` — `+DirectoriesToAlwaysCook` per asset folder.
9. Regenerate `FPSPreloadAssetRegistry.gen.h` (`generate_preload_registry.py --write`).

**Needed for it to look/behave right**
10. `UI/ColdSteelWeaponIcons.cpp:52` + `ColdSteelWeaponIconCatalogCommandlet.cpp:25` — id whitelists.
11. `UI/ColdSteelIconResources.cpp` — per-attachment icon preload branches.
12. `UI/ColdSteelInventoryWidget.cpp:126` + `ColdSteelWeaponIconReadback.cpp:148` — icon framing.
13. `UI/ColdSteelWeaponIcons.cpp:69` — cache-key suffix if the art needs extra silhouette room.
14. `UI/ColdSteelPickupWeapon.cpp:28` + `ColdSteelPickupStudio.cpp:73` — pickup-world allowlists.
15. `UI/ColdSteelWarehouseModel.cpp:50,54,56` — starting-armory grant + magazine count + reserve ammo.
16. `Weapons/RifleHipFraming.cpp:12,26/32,92` — `Supports()` + presentation offset + up-axis.
17. `Weapons/TacticalDeviceVariants.h:64/65` — `FamilyForDefinition` (mesh family string).
18. `Weapons/M4MuzzleVisual.cpp:40`, `M4HandstopVisual.cpp:60/69`, `M4DrumVisual.cpp:61/70`, `M4GunsmithVisual.cpp:34/35`, `SkeletonStockVisual.cpp:51/59`, `PhantomRearGripVisual.cpp:32/40`, `ThermalScopeVisual.cpp:13/32`, `SVDGripProfiles.cpp:22/23`, `TacticalDeviceComponent.cpp:522` — attachment dispatch.
19. `Weapons/GunsmithModificationTier.h` — special/legendary tier for its exclusive parts.
20. `Weapons/M4TacticalSprintComponent.{h,cpp}` — new `ERifleSprintWeapon` member + clip load branch.
21. `Weapons/CasingPortCalibration.h:17–33` — ejection-port entry (M870 is **missing**, inherits default).
22. `Skills/QuickCombatRifleMotion.h:24–35` — stock point for quick melee.
23. `Weapons/M870WeaponAssets.h:19` — `SoundPath()` style audio namespace (see `FPSGAMECharacter.cpp:3437–3455`).

**Only if multiplayer**
24. `Multiplayer/ColdSteelPlayerState.{h,cpp}` RPC surface, `ColdSteelSuper90Authority.cpp`, `Multiplayer/Super90NetworkTypes.h`; or add the id to `TubeShotgunAssets.h` and inherit the whole pipe.

**Tooling**
25. `Tools/Weapons/dump_attachment_values.py:12–14` `SHORT` map.
26. `Tools/Weapons/check_attachment_consistency.py:37` `MODEL_TOKENS` (avoid false positives).
27. Export the catalog PNG at `320 × grid_w/grid_h` (4×2 ⇒ 640×320) + factory attachment icons under `AttachmentIcons20260913/FramedFirearms/`.

---

## 8. Notable asymmetries / traps found

1. **`TubeShotgunAssets::MatchesMesh` uses `==`, not `StartsWith`** — a re-skinned or variant mesh path bypasses every shotgun branch silently.
2. **`M870FurnitureAssets.cpp:40` is the only `/Game/Weapons/M870/` prefix check** in the codebase; everything else compares against the `M870WeaponAssets::MeshPath` constant.
3. **`CasingPortCalibration.h` has no M870 row** — M870 casings use `FPort::Find()` default, unlike Super90 (L32).
4. **`PelletCount` lives in `Super90WeaponAssets` and is consumed for M870 too** (`FPSGAMECharacter.cpp:2719,2963`; `ColdSteelPlayerState.cpp:1007,1154`). A new shotgun inheriting this shares Super90's 8 pellets unless it carries its own constant.
5. **`ColdSteelIconResources.cpp:182` family fallback is `TEXT("M4")`** — any firearm not enumerated there resolves tactical-device meshes to the M4 family.
6. **`items.json` weapons have no `rarity`**, ammo does. Copying a `super90` item block with `rarity` re-introduces a forbidden field (AGENTS.md 2026-10-09).
7. **`ue_super90.png` and `ue_pkm_lowpoly.png` lack `.uasset` siblings** while every other weapon has one.
8. **`check_attachment_consistency.py` will always flag `ue_m870`/`ue_super90`** for the missing 可改造 traits line (L237–247) — pre-existing, not caused by a new gun.
9. **`common_options` injects `optic.thermal_scope` + `tactical.blessed_laser` into every weapon**, so a new gun's `m870_tube_extension`-style exclusive options must not collide with those ids.
10. **`ue_super90` `traits` include a "全部可改造" line listing reargrip**, but `ue_m870` does not — the two templates disagree on trait conventions; M870 is the newer and audit-verified one (`M870CompletionAudit20261017/offline_inventory.py`).

---

### Two source files worth opening before writing the new gun
- `SourceAssets/BenelliM4Super9020261006/apply_runtime.py` — 30 ordered `edit()` calls = the full C++ touch list for Super90.
- `Tools/Weapons/M870Icons20261017/Before/register_catalog.py` — 27 lines = the full data/ini touch list for M870.
