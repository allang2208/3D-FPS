"""Extract matching grip surfaces for native-715 gun registration; no pose edits."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
side=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(B/'Donor'/side/'SK_DW715_Donor.fbx'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE')
root=r.data.bones['WPN_root'].matrix_local;ri=root.inverted()
trigger=(ri@r.data.bones['WPN_Trigger'].matrix_local).translation
donor=[]
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    slots={i for i,m in enumerate(ob.data.materials) if m and 'Hero_Grip' in m.name}
    ids={i for p in ob.data.polygons if p.material_index in slots for i in p.vertices}
    to_root=ri@r.matrix_world.inverted()@ob.matrix_world
    donor.extend([list(to_root@ob.data.vertices[i].co) for i in sorted(ids)])
raw=json.loads((B/'canonical_parts.json').read_text())
grip=next(p for p in raw if p['name']=='9_l')
data=dict(side=side,donor_grip=donor,rsh_grip=grip['verts'],donor_trigger=list(trigger),rsh_trigger=[0,.086,.011])
(O/(side+'_grip_input.json')).write_text(json.dumps(data),encoding='utf8')
print('NATIVE_GRIP_INPUT',side,len(donor),len(grip['verts']),list(trigger),flush=True)
