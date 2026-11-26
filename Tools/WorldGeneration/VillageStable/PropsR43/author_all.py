"""Master headless Blender 5.1 script: author all 5 StablePropsR43 AAA meshes, 3 LODs each, QC & editable .blend."""
import json
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(HERE))

OUT_ROOT = PROJECT / 'SourceAssets/HillsVillageStable/PropsR43'
EXCHANGE = OUT_ROOT / 'Exchange'
BLEND_PATH = OUT_ROOT / 'StablePropsR43.blend'
MANIFEST_PATH = OUT_ROOT / 'model-manifest.json'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

from build_tack import build_saddle_stand, build_tack_wall_rack
from build_yard_props import build_hay_wagon, build_jump_rail, build_yard_lamp_post


def main():
    EXCHANGE.mkdir(parents=True, exist_ok=True)
    builders = [
        build_saddle_stand,
        build_tack_wall_rack,
        build_jump_rail,
        build_hay_wagon,
        build_yard_lamp_post,
    ]
    records = []
    # Space master objects cleanly along +X in the editable .blend for visual inspection if ever opened
    offset_x = 0.0
    for fn in builders:
        rec = fn(EXCHANGE)
        records.append(rec)
        obj = bpy.data.objects.get(rec['name'])
        if obj is not None:
            obj.location.x = offset_x
            offset_x += max(2.2, rec['size_cm'][0] / 100.0 + 1.2)
        print(
            f"BUILT {rec['name']} lod0={rec['lods'][0]['triangles']} "
            f"lod1={rec['lods'][1]['triangles']} lod2={rec['lods'][2]['triangles']} "
            f"size_cm={rec['size_cm']} slots={len(rec['materials'])} open={rec['open_edges']}",
            flush=True,
        )

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    manifest = dict(
        revision='StablePropsR43',
        blender_version='.'.join(map(str, bpy.app.version)),
        blend_file=str(BLEND_PATH),
        assets=records,
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'STABLE_PROPS_R43_BLENDER_OK count={len(records)} manifest={MANIFEST_PATH}', flush=True)


if __name__ == '__main__':
    main()
