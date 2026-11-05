"""Read existing canonical device coordinates for the M24 side-rail fitting."""
from pathlib import Path
import bpy,json
from mathutils import Matrix
O=Path(__file__).resolve().parent;S=O.parent
ash=json.loads((S/'ASH12TacticalDevices20260920/installed.json').read_text())['parts']
blessed=json.loads((S/'BlessedLaser20261006/Model/authoring.json').read_text())['ASH12']
report={}
for kind in ('laser','flashlight','blessed_laser'):
    source=blessed['fbx'] if kind=='blessed_laser' else ash[kind]['fbx']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source,use_custom_normals=True)
    bodies=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@v.co for o in bodies for v in o.data.vertices]
    near=max(p.y for p in points)
    contact=[p for p in points if p.y>near-.001]
    def bounds(ps):return [[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)]
    report[kind]={'source':source,'bounds':bounds(points),'inner_contact':bounds(contact),'objects':[o.name for o in bodies],
        'materials':[m.name for o in bodies for m in o.data.materials]}
(O/'source_coordinates.json').write_text(json.dumps(report,indent=2))
print('M24_TACTICAL_SOURCE_COORDINATES',json.dumps(report),flush=True)
