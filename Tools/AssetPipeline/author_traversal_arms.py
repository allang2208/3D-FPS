"""Retarget inspected Epic traversal poses to the existing, unmodified FPS arms.
Run in Blender. Source files stay untouched. Destination actions are non-looping.
"""
import bpy, json, math, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/GASPTraversal20260910/Native'
OUT.mkdir(parents=True,exist_ok=True)
REF=OUT.parent/'Reference'
CLIPS={'Vault':(.8,.27,.58,1.),'Mantle':(2.,.345,1.1,1.),'Climb':(3.333333,.74,2.25,2.5)}
def rigid(m):
    p,q,_=m.decompose()
    return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def at(r,f):
    bpy.context.scene.frame_set(math.floor(f),subframe=f-math.floor(f))
    bpy.context.view_layer.update()
    return {b.name:rigid(r.matrix_world@b.matrix) for b in r.pose.bones}
sources={}
for name,(duration,plant,release,height) in CLIPS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(REF/(name+'.fbx')))
    r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    at(r,1)
    bind={b.name:rigid(r.matrix_world@b.matrix_local) for b in r.data.bones}
    frames=[at(r,1+k/60*30) for k in range(round(duration*60)+1)]
    turn=Matrix.Rotation(math.pi,4,'Z')
    origin=turn@frames[0]['pelvis'].translation; origin.z=0
    shift=Matrix.Translation(-origin)@turn
    sources[name]={'bind':{n:shift@m for n,m in bind.items()},
                   'frames':[{n:shift@m for n,m in f.items()} for f in frames]}

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima']; arms=bpy.data.objects['SK_Manny_Arms_Export'];s=bpy.context.scene
def geometry_digest():
    return hashlib.sha256(repr([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in arms.data.vertices]).encode()).hexdigest()
digest=geometry_digest()
for o in list(s.objects):
    if o not in (r,arms): bpy.data.objects.remove(o,do_unlink=True)
r.animation_data_clear()
rest={b.name:rigid(r.matrix_world@b.matrix_local) for b in r.data.bones}
names=list(rest); parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
localrest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
for b in r.pose.bones:
    b.custom_shape=None
    for c in list(b.constraints):b.constraints.remove(c)
    b.matrix_basis=Matrix.Identity(4);b.rotation_mode='QUATERNION'
bpy.ops.object.select_all(action='DESELECT')
for o in (r,arms):o.hide_set(False);o.hide_render=False;o.select_set(True)
bpy.context.view_layer.objects.active=r
EXPORT=dict(use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_TraversalArms.fbx'),bake_anim=False,**EXPORT)

def palm(poses,side):
    h=poses['hand_'+side].translation
    front=(poses['middle_01_'+side].translation-h).normalized()
    across=(poses['index_01_'+side].translation-poses['pinky_01_'+side].translation).normalized()
    normal=across.cross(front).normalized();across=front.cross(normal).normalized()
    return Matrix((across,front,normal)).transposed().to_4x4()
def segment(oldhead,oldtail,newhead,newtail):
    q=(oldtail-oldhead).rotation_difference(newtail-newhead)
    m=q.to_matrix().to_4x4();m.translation=newhead-m.to_3x3()@oldhead
    return m
report={'geometry_before':digest,'materials':[m.name for m in arms.data.materials],'clips':{}}
for name,(duration,plant,release,height) in CLIPS.items():
    source=sources[name];bind=source['bind']
    a=bpy.data.actions.new('Traversal_'+name);a.use_fake_user=True;r.animation_data_create();r.animation_data.action=a
    s.render.fps=60;s.frame_start=0;s.frame_end=round(duration*60)
    correction={n:bind[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in names if n in bind}
    max_bone_error=0.;max_hand_error=0.
    for k,src in enumerate(source['frames']):
        p={n:m.copy() for n,m in rest.items()}
        for n in names:
            if n in src and n in correction:
                p[n]=Matrix.LocRotScale(src[n].translation,src[n].to_quaternion()@correction[n],Vector((1,1,1)))
        for side in ('l','r'):
            u,l,h=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
            shoulder=src[u].translation.copy();wrist=src[h].translation.copy()
            len1=(rest[l].translation-rest[u].translation).length
            len2=(rest[h].translation-rest[l].translation).length
            delta=wrist-shoulder
            if delta.length>len1+len2-.005:shoulder+=delta.normalized()*(delta.length-(len1+len2-.005))
            delta=wrist-shoulder;dist=max(abs(len1-len2)+1e-5,min(delta.length,len1+len2-1e-5));direction=delta.normalized()
            pole=src[l].translation-shoulder;perp=(pole-direction*pole.dot(direction)).normalized()
            along=(len1*len1+dist*dist-len2*len2)/(2*dist)
            elbow=shoulder+direction*along+perp*math.sqrt(max(0,len1*len1-along*along))
            p[u]=segment(rest[u].translation,rest[l].translation,shoulder,elbow)@rest[u]
            p[l]=segment(rest[l].translation,rest[h].translation,elbow,wrist)@rest[l]
            palm_delta=palm(src,side)@palm(rest,side).inverted()
            q=(palm_delta@rest[h]).to_quaternion()
            p[h]=Matrix.LocRotScale(wrist,q,Vector((1,1,1)))
            for n in names:
                if n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_')) and n in src:
                    par=parents[n]
                    # Carry source finger articulation in the target palm frame.
                    source_relative=src[h].inverted()@src[n]
                    bind_relative=bind[h].inverted()@bind[n]
                    native_relative=rest[h].inverted()@rest[n]
                    q=(p[h]@source_relative@bind_relative.inverted()@native_relative).to_quaternion()
                    p[n]=Matrix.LocRotScale((p[par]@localrest[n]).translation,q,Vector((1,1,1)))
                elif n.endswith('_'+side) and ('upperarm_twist' in n or 'lowerarm_twist' in n):
                    driver=u if 'upperarm' in n else l
                    p[n]=p[driver]@rest[driver].inverted()@rest[n]
            max_bone_error=max(max_bone_error,abs((p[l].translation-p[u].translation).length-len1),abs((p[h].translation-p[l].translation).length-len2))
            max_hand_error=max(max_hand_error,(p[h].translation-src[h].translation).length)
        s.frame_set(k)
        for n in names:
            par=parents[n];local=p[par].inverted()@p[n] if par else p[n]
            b=r.pose.bones[n];b.matrix_basis=localrest[n].inverted()@local
            b.keyframe_insert('location',frame=k,group=n);b.keyframe_insert('rotation_quaternion',frame=k,group=n);b.keyframe_insert('scale',frame=k,group=n)
    if a.slots:r.animation_data.action_slot=a.slots[0]
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_Traversal_'+name+'.fbx')),bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.,bake_anim_step=1.,**EXPORT)
    plantpose=source['frames'][round(plant*60)]
    edge=(plantpose['hand_l'].translation+plantpose['hand_r'].translation)*.5;edge.z=height
    report['clips'][name]={'duration':round(duration*60)/60,'contact':plant,'release':release,'reference_height':height,
        'edge_blender':list(edge),'max_bone_error_m':max_bone_error,'max_hand_error_m':max_hand_error}
    assert max_bone_error<1e-5 and max_hand_error<1e-5
assert geometry_digest()==digest
report['geometry_after']=geometry_digest()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TraversalArms_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TRAVERSAL_ARMS_AUTHORED')
