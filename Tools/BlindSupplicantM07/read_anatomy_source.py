"""Read the retained whole-body authoring source and save bone/mesh input data.
No render, simulation or gameplay test is performed.
"""
import bpy, json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'Authoring'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT.parent / 'WitchMeshy20260919/Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE), use_anim=False)
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
rig.data.pose_position = 'REST'
record = {
    'source': str(SOURCE),
    'armature_world_matrix': [list(row) for row in rig.matrix_world],
    'bones': [{'name': b.name, 'parent': b.parent.name if b.parent else None,
               'head_m': list(rig.matrix_world @ b.head_local),
               'tail_m': list(rig.matrix_world @ b.tail_local)} for b in rig.data.bones],
    'meshes': [{'name': o.name, 'vertices': len(o.data.vertices),
                'materials': [m.name if m else None for m in o.data.materials],
                'dimensions_m': list(o.dimensions)} for o in bpy.context.scene.objects if o.type == 'MESH'],
    'source_use': 'Whole anatomical source already used by WitchRebuilt; preserve donor rig and body continuity',
    'tested': False,
}
(OUT / 'anatomy_source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'saved': str(OUT / 'anatomy_source.json'), 'bone_count': len(record['bones']),
                  'meshes': record['meshes']}, ensure_ascii=False), flush=True)
