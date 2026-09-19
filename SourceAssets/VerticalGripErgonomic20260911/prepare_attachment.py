import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
for variant in ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'FinalFit.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.view_layer.update();fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])
 fit['attachment_local']={ob.name:[list(row) for row in G.inverted()@ob.matrix_world] for ob in bpy.context.scene.objects if ob.name.startswith('VG_' if variant=='vertical' else 'PH_')}
 (d/'fit_final.json').write_text(json.dumps(fit,indent=2))
