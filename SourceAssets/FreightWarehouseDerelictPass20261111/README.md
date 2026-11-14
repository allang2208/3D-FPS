# Warehouse derelict art pass

Target: `/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`.

Primary reference: [Quixel Derelict Corridor](https://www.fab.com/listings/d825ff9c-77da-45a4-9619-c989e6dfdda6). The public example establishes the direction: layered deterioration, clutter and debris that support an abandoned interior, with a readable route. This pass adapts that direction to an abandoned cargo warehouse. The complete reference project has not been imported or inspected locally.

Supporting method references: [FontainebleauDemo](https://github.com/Unity-Technologies/FontainebleauDemo) for limited-asset variation and layered surface response; [Practical Real-Time Hex-Tiling](https://github.com/mmikk/hextile-demo) for the distinction between texture repetition and authored use marks. No third-party shader code or Unity assets are copied. The concrete base remains untouched; this revision uses local, non-repeating overlay placements rather than replacing its sampling with hex tiling.

## Production scope

- Preserve the accepted entrance's 35 decorative mesh placements, original walls/floors and concrete bindings, rack/cargo structure, all lights and exposure, containers, main route and spawn.
- Keep packing, storage, loading and maintenance visually distinct. Remove 32 earlier decorations: generic cargo rubble, loose metal scatter and the mixed electrical-corner clutter.
- Add 23 supported decorations: two scanned wooden cable reels, upper-shelf maintenance remnants, small scanned pipe joints, cargo-related cardboard/forms and four concrete fragments linked to nearby wall damage.
- Add 15 local surface overlays: two scanned concrete damage patches, shelf dust, localized activity marks and a dock-wall leakage patch.
- Update existing owned dust/scuff/damp/oil overlays with texture-dependent opacity and spatially varying roughness. All use existing source masks; leakage uses a scanned Quixel source with a softened projection edge and vertical UV orientation.
- Create handled/settled native prop material instances. They preserve original PBR maps and native normal/detail blending, adjusting the native slope-based dust layer and restrained wood detail strength.
- Large existing added dock pallets/crates/drums receive scoped static collision copies; original gameplay actors are not touched.

## Source assets

UndergroundTunnel supplies pallets, crates, dolly, boards, tools and cardboard. HospitalCorridor supplies distinct grime/scuff masks. Existing FacilityQuixel20261108 supplies scanned WoodenCableReel, RustyPipeJoint, ConcreteRubble, DamagedConcrete and Leakage. TransitIncidentDetail supplies curled dispatch forms. No new purchase or asset-pack acquisition was required.

## Authoring and save

`inputs.json` records the pre-edit scene and material input data. `author_layout.py` reuses the preceding source-triangle contact routines without rerunning its sample authoring. `materials.py` owns a new material namespace. `install.py` backs up the exact current map and external packages, then saves only the requested map and owned assets. `Receipts/install.json` records completion separately from visual acceptance.

The previous two passes are retained as authoring dependencies and restore points. They are not rerun to rebuild this revision. The saved before-weathering comparison map remains unchanged.

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

No game, screenshot, render, navigation, performance or visual acceptance tests are run. The user tests the saved scene.
