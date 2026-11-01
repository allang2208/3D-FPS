"""Retarget the ORIGINAL M24 timeline directly and preserve metric V9 morph coordinates."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;SRC=O.parent/'M24CustomScope20261026';X=O/'Exports'
(X/'Animations').mkdir(parents=True,exist_ok=True)
I=Matrix.Identity(4);C=Matrix.Rotation(math.pi,4,'Z')
def rigid(m):
    p,q,scale=m.decompose();return Matrix.LocRotScale(p,q,Vector((1,1,1)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC/'Donor/Source/source/arms@sniper.fbx'))
s=bpy.context.scene;donor=bpy.data.objects['Armature'];s.frame_set(1);bpy.context.view_layer.update()
sr={b.name:rigid(C@donor.matrix_world@b.matrix_local) for b in donor.data.bones}
objects={'WPN_root':'sniper','WPN_BoltCarrier':'boltrear','WPN_BoltHandle':'bolt',
 'WPN_CheekRest':'cheekrest','WPN_Trigger':'trigger','WPN_Magazine':'clip','WPN_Cartridge':'bullet','WPN_Suppressor':'silencer'}
sr.update({n:rigid(C@bpy.data.objects[o].matrix_world) for n,o in objects.items()})
source=[]
for f in range(1,202):
    s.frame_set(f);bpy.context.view_layer.update()
    row={b.name:rigid(C@donor.matrix_world@b.matrix) for b in donor.pose.bones}
    row.update({n:rigid(C@bpy.data.objects[o].matrix_world) for n,o in objects.items()});source.append(row)
# The intermediate native rig had changed the donor's evaluated arm poses. Do not sample it.
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24Repair20261027/M24_Repaired_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
r.animation_data_clear();r.matrix_world=I
for pb in r.pose.bones:pb.matrix_basis=I
s.frame_set(0);bpy.context.view_layer.update()
# Recover basis AND every corrective from the same accepted source in the same units.
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(SRC/'V9/M4_V9_Template.fbx'),use_anim=False)
added=[o for o in bpy.data.objects if o not in before]
tr=next(o for o in added if o.type=='ARMATURE');tm=next(o for o in added if o.type=='MESH')
slots={i for i,m in enumerate(tm.data.materials) if m and 'SkinV9' in m.name}
used=sorted({v for p in tm.data.polygons if p.material_index in slots for v in p.vertices})
transform=tr.matrix_world.inverted()@tm.matrix_world
for key in skin.data.shape_keys.key_blocks:
    original=tm.data.shape_keys.key_blocks[key.name]
    values=np.array([transform@original.data[i].co for i in used],dtype=np.float32)
    key.data.foreach_set('co',values.ravel());key.value=0
basis=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data],dtype=np.float32)
skin.data.vertices.foreach_set('co',basis.ravel());skin.data.update()
for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
r.matrix_world=I;r.scale=(1,1,1);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
# Reuse the established semantic hand-axis and two-bone solver, with raw donor inputs.
old=(SRC/'author_gameplay.py').read_text();tree=ast.parse(old)
for name in ('frame','under','solve_arm','retarget','mix','blend','ease','settled','held_motion','twists'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.unparse(node),'M24_source_'+name,'exec'))
exec(compile('corrections = {}; fmap = {}; offsets = {}'+old.split('corrections = {}; fmap = {}; offsets = {}')[1].split('\ndef solve_arm')[0],'M24_semantic_axes','exec'))
native_rows=[retarget(p) for p in source];idle=native_rows[0]
exec(compile(old[old.index("clips={'idle'"):old.index('\ndef twists')],'M24_actions','exec'))
# A quiet four-second held breathing loop. Both hands and the rifle share one motion;
# keep the aimed reference stationary and continue the existing locomotion system.
clips['aim']=[{n:m.copy() for n,m in idle.items()} for _ in range(2)]
breath=[]
for f in range(121):
    phase=2*math.pi*f/120
    d=Matrix.Translation((.0008*math.sin(phase),.0010*(1-math.cos(phase)),.0015*math.sin(phase)))
    breath.append(held_motion(d))
clips['idle']=breath
# Author all affected returns from the same corrected hold; preserve mechanical clocks.
for a in list(bpy.data.actions):
    if a.name.startswith('A_M24_'):bpy.data.actions.remove(a)
report={'source':'raw original arms@sniper.fbx; no intermediate native animation bake',
 'fps':30,'shape_keys':len(skin.data.shape_keys.key_blocks),'clips':{},'idle_bones':{n:list(m.translation) for n,m in idle.items()},
 'skin_basis_extent_m':list(basis.max(0)-basis.min(0))}
def bake(role,rows):
    twists(rows)
    a=bpy.data.actions.new('A_M24_'+role);a.use_fake_user=True;r.animation_data_create();r.animation_data.action=a
    for pb in r.pose.bones:
        pb.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):pb.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for l in a.layers for st in l.strips for bag in st.channelbags for c in bag.fcurves}
    for n in rest:
        values=[];previous=None
        for row in rows:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n]
            p,q,scale=(local_rest[n].inverted()@local).decompose()
            if previous is not None and q.dot(previous)<0:q.negate()
            values.append((p,q,scale));previous=q.copy()
        for prop,k,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)]
                curve.keyframe_points.clear();curve.keyframe_points.add(len(rows))
                curve.keyframe_points.foreach_set('co',[x for f,row in enumerate(values) for x in (f,row[k][axis])])
                for key in curve.keyframe_points:key.interpolation='LINEAR'
                curve.update()
    r.animation_data.action_slot=a.slots[0];s.frame_start=0;s.frame_end=len(rows)-1;s.render.fps=30;s.frame_set(0)
    report['clips'][role]={'action':a.name,'duration':(len(rows)-1)/30,'frames':len(rows)}
for role,rows in clips.items():bake(role,rows)
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=120;s.frame_set(0);bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Hold_Editable.blend'))
report['skin_basis_extent_m']=[float(v) for v in report['skin_basis_extent_m']]
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_HOLD_AUTHORED',len(clips),report['skin_basis_extent_m'],flush=True)
