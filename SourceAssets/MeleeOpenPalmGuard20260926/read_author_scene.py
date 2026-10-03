import bpy, json
from pathlib import Path
P = Path(__file__).parent
source = P.parents[1] / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
record = {'objects': [{'name': o.name, 'type': o.type, 'matrix': [list(v) for v in o.matrix_world]}
                      for o in bpy.data.objects]}
for rig in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    record['rig'] = rig.name
    record['bones'] = {b.name: {'parent': b.parent.name if b.parent else None,
                              'rest': [list(v) for v in b.matrix_local]} for b in rig.data.bones}
(P / 'bare_scene.json').write_text(json.dumps(record, separators=(',', ':')), encoding='utf-8')
print('GUARD_BARE_AUTHOR_SCENE ' + json.dumps({'rig': record.get('rig'), 'objects': [o['name'] for o in record['objects']]}))
