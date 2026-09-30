"""Save both FK clips on the actual V7 reference skin and current 201 surface.

Neutral authoring materials only; this file does not replace production meshes.
"""
import json, math
from pathlib import Path
import bpy, numpy as np
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).resolve().parent;P=O.parents[2]
d=json.loads((O/'input.json').read_text());keys=json.loads((O/'keys.json').read_text())
skin=json.loads((P/'SourceAssets/PKMLowpoly20260922/LeftState50/Input/Bare.json').read_text())
weapon=json.loads((O.parent/'Refine12/201_surface.json').read_text())
bones=d['meshes']['201']['bones'];reflect=Matrix.Diagonal((1.,-1.,1.))
def converted(v,reference=None):
    q=v['q'];r=Quaternion((q[3],*q[:3])).to_matrix();m=(reflect@r@reflect).to_4x4()
    if reference is not None:
        scale=Vector(v['s'])/100.0
        m=m@Matrix.Diagonal((*scale,1.))
    m.translation=reflect@Vector(v['p'])*.01
    return m
def ue(v):
    q=v['q'];return Matrix.LocRotScale(Vector(v['p']),Quaternion((q[3],*q[:3])),Vector(v['s']))
def from_world(m):
    p,q,s=m.decompose();return {'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(s)}
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=120
arm=bpy.data.armatures.new('201_Native_FK');rig=bpy.data.objects.new(arm.name,arm)
bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n,v in bones.items():
    b=arm.edit_bones.new(n);b.matrix=converted(v);b.length=.025
for n,v in bones.items():
    if v['parent'] in bones:arm.edit_bones[n].parent=arm.edit_bones[v['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
rig['MotionSource']='Installed PKMLowpoly ArmJoint49 + FingerClearance20260926'
rig['Method']='Native complete FK arms. Weapon translation adapts contact. No IK or twist solver.'
rig['RuntimeAssets']='LMG201/Reload11/A_LMG201_reload_belt and reload_belt_empty'
for n in bones:rig.pose.bones[n].rotation_mode='QUATERNION'
def mesh_object(label,s,fi,color):
    used=sorted({v for i in fi for v in s['triangles'][i]});remap={v:i for i,v in enumerate(used)}
    pos=s.get('positions',s.get('vertices'));me=bpy.data.meshes.new(label)
    me.from_pydata([(pos[i][0]*.01,-pos[i][1]*.01,pos[i][2]*.01) for i in used],[],
                  [[remap[v] for v in s['triangles'][i]] for i in fi]);me.update()
    obj=bpy.data.objects.new(label,me);bpy.context.collection.objects.link(obj);obj.parent=rig
    obj.modifiers.new('Native skin','ARMATURE').object=rig
    mat=bpy.data.materials.new(label+'_Neutral');mat.diffuse_color=color;me.materials.append(mat)
    for name in sorted({n for i in used for n in s['weights'][i] if n in bones}):obj.vertex_groups.new(name=name)
    for vi,old in enumerate(used):
        for name,w in s['weights'][old].items():
            if name in obj.vertex_groups:obj.vertex_groups[name].add([vi],w,'REPLACE')
    for f in me.polygons:f.use_smooth=True
    if 'normals' in s:me.normals_split_custom_set([(x,-y,z) for i in fi for x,y,z in s['normals'][i]])
    return obj
mesh_object('V7_BareArms',skin,list(range(len(skin['triangles']))),(.63,.44,.32,1.))
fi=[i for i,m in enumerate(weapon['material_ids']) if 'Manny' not in weapon['materials'][m] and 'Magazine' not in weapon['materials'][m]]
mesh_object('201_Weapon_Neutral',weapon,fi,(.13,.16,.19,1.))
rest={n:arm.bones[n].matrix_local.copy() for n in bones}
inverse_local={n:(rest[bones[n]['parent']].inverted()@rest[n]).inverted() if bones[n]['parent'] in bones else rest[n].inverted() for n in bones}
rig.animation_data_create()
for key in ('reload','reload_empty'):
    target=d['clips']['201_'+key];name=target['asset'].rsplit('/',1)[-1];spec=keys['clips'][name]
    action=bpy.data.actions.new(name+'_PKMFK19');action.use_fake_user=True
    slot=action.slots.new(id_type='OBJECT',name=rig.name)
    layer=action.layers.new('Native FK and contact placement');strip=layer.strips.new(type='KEYFRAME')
    bag=strip.channelbag(slot,ensure=True)
    channels={n:{'location':[],'rotation_quaternion':[],'scale':[]} for n in bones}
    previous={n:None for n in bones}
    for i,row in enumerate(target['poses']):
        local={n:ue(spec['tracks'][n][i] if n in spec['tracks'] else v['local']) for n,v in row.items()}
        worlds={}
        def evaluate(n):
            if n not in worlds:
                parent=bones[n]['parent'];worlds[n]=evaluate(parent)@local[n] if parent in local else local[n]
            return worlds[n]
        posed={n:converted(from_world(evaluate(n)),True) for n in bones}
        for n in bones:
            parent=bones[n]['parent'];m=inverse_local[n]@(posed[parent].inverted()@posed[n] if parent in posed else posed[n])
            p,q,s=m.decompose()
            if previous[n] is not None and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy()
            channels[n]['location'].append(tuple(p));channels[n]['rotation_quaternion'].append(tuple(q));channels[n]['scale'].append(tuple(s))
    frames=np.arange(1,target['frames']+1,dtype=float)
    for n,properties in channels.items():
        for prop,values in properties.items():
            a=np.asarray(values)
            for axis in range(a.shape[1]):
                f=bag.fcurves.new(data_path=f'pose.bones["{n}"].{prop}',index=axis)
                f.keyframe_points.add(len(frames));f.keyframe_points.foreach_set('co',np.column_stack([frames,a[:,axis]]).ravel())
                for point in f.keyframe_points:point.interpolation='LINEAR'
                f.update()
    rig.animation_data.action=action;rig.animation_data.action_slot=slot
    print('PKMFK19_EDITABLE_ACTION',name,flush=True)
scene.frame_start=1;scene.frame_end=793;scene.frame_set(79)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=1.15;area.spaces.active.region_3d.view_location=Vector((0,.10,0))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_PKMFK19_Editable.blend'))
print('PKMFK19_EDITABLE_SAVED',flush=True)
