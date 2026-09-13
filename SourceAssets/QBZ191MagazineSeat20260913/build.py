"""Seat the separate source magazine and author QBZ-specific reload contact.

Preserves the current folding sights, common Manny hands and action clocks.
Authoring/export only; no post-change rendering or runtime test.
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'VREGripExtensions20260912/ReferenceWorkflow'))
from front_pose import solve_arm
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191Folding20260913/QBZ191_Folding_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['QBZ191_Export'];hands=bpy.data.objects['SK_Manny_Arms_Export']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
def pose(action,f):
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}
def smooth(t):
    t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
def mix(a,b,t):
    al,aq,asc=a.decompose();bl,bq,bsc=b.decompose()
    if aq.dot(bq)<0:bq.negate()
    return Matrix.LocRotScale(al.lerp(bl,t),aq.slerp(bq,t),asc.lerp(bsc,t))
def shifted(m,v):
    out=m.copy();out.translation+=Vector(v);return out
def track(keys,f):
    if f<=keys[0][0]:return keys[0][1].copy()
    for (a,A),(b,B) in zip(keys,keys[1:]):
        if f<=b:return mix(A,B,smooth((f-a)/(b-a)))
    return keys[-1][1].copy()
def retain(mesh,predicate):
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if not predicate(f)],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()
def export(name,objects,kinds,animation=False,end=0):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    s.render.fps=60;s.frame_start=0;s.frame_end=end if animation else 180
    path=O/(name+'.fbx');path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types=kinds,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=animation,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0,mesh_smooth_type='FACE',use_tspace=False)
    return str(path)

# Derive the correction from the supplied parts, not the donor magazine bone.
measure=json.loads((O/'source-contact.json').read_text())
neck=measure['source_mag_top_12mm'];source_top=measure['source_components']['93']['max'][2]
center_x=.000688;lip_z=measure['well_vertical_rays']['0.016,-0.13'][2]
insertion_depth=.020
offset=Vector((center_x-(neck['min'][0]+neck['max'][0])/2,0,lip_z+insertion_depth-source_top))
idle=pose(bpy.data.actions['QBZ191_base_idle'],0)
mag0=idle['WPN_root'].inverted()@idle['WPN_SOCKET_Magazine']
correction_in_mag=mag0.inverted()@Matrix.Translation(offset)@mag0
bind_correction=rest['WPN_SOCKET_Magazine']@correction_in_mag@rest['WPN_SOCKET_Magazine'].inverted()
mag_indices={i for i,m in enumerate(gun.data.materials) if m.name=='M_QBZ191_Magazine'}
mag=gun.copy();mag.data=gun.data.copy();mag.name='QBZ191_Magazine_Export';s.collection.objects.link(mag)
retain(mag.data,lambda f:f.material_index in mag_indices)
retain(gun.data,lambda f:f.material_index not in mag_indices)
mag.data.transform(bind_correction)
# The complete shell, feed mouth and baseplate share one rigid mechanical bone.
mag.vertex_groups.clear();mag.vertex_groups.new(name='WPN_SOCKET_Magazine').add(list(range(len(mag.data.vertices))),1,'REPLACE')

metadata={}
for family in ['base','vertical','canted','prism','angled']:
    for kind,end in [('reload',126),('reload_empty',164)]:
        source=bpy.data.actions['QBZ191_'+family+'_'+kind]
        held_pose=pose(source,0);held=held_pose['WPN_root'].inverted()@held_pose['hand_l']
        contact=pose(source,95)
        grasp=correction_in_mag@contact['WPN_SOCKET_Magazine'].inverted()@contact['hand_l']
        source49=pose(source,49);pickup=source49['WPN_root'].inverted()@source49['WPN_SOCKET_Magazine']
        seat_hand=mag0@grasp
        samples=[];previous={}
        for k in range(end*4+1):
            f=k*.25;p=pose(source,f);root=p['WPN_root'];old_hand=p['hand_l'].copy()
            if f>=49:
                # Feed mouth reaches the measured rim at frame 76. From there
                # it travels only up the well axis, locking at frame 95.
                M=track([(49,pickup),(56,shifted(mag0,(.10,.07,-.32))),(68,shifted(mag0,(.016,.009,-.09))),(72,shifted(mag0,(0,0,-.035))),(76,shifted(mag0,(0,0,-insertion_depth))),(91,shifted(mag0,(0,0,-.0025))),(95,mag0)],f)
                p['WPN_SOCKET_Magazine']=root@M
            else:M=root.inverted()@p['WPN_SOCKET_Magazine']
            if 30<f<49:
                delta=p['WPN_SOCKET_Magazine']@correction_in_mag@p['WPN_SOCKET_Magazine'].inverted()
                target=mix(old_hand,delta@old_hand,smooth((f-30)/19))
            elif 49<=f<=98:target=p['WPN_SOCKET_Magazine']@grasp
            elif 98<f<126:
                target=root@track([(98,seat_hand),(106,shifted(seat_hand,(.07,0,-.004))),(115,shifted(held,(.05,.006,-.01))),(126,held)],f)
            else:target=None
            if target is not None:
                hand_delta=target@old_hand.inverted()
                finger_targets={n:hand_delta@p[n] for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))}
                solve_arm(p,rest,target,root,.7)
                p.update(finger_targets)
            row={}
            for n in names:
                B=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=B.decompose()
                if n in previous and previous[n].dot(q)<0:q.negate()
                previous[n]=q.copy();row[n]=(loc,q,scale)
            samples.append(row)
        action=bpy.data.actions.new('QBZ191_Seated_'+family+'_'+kind);action.use_fake_user=True;r.animation_data.action=action
        for n in names:
            b=r.pose.bones[n];b.rotation_mode='QUATERNION'
            for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
        bag=action.layers[0].strips[0].channelbag(action.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
        for n in names:
            for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
                for axis in range(count):
                    curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(samples))
                    curve.keyframe_points.foreach_set('co',[v for k,row in enumerate(samples) for v in (k*.25,row[n][field][axis])])
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
                    curve.update()
        r.animation_data.action_slot=action.slots[0];s.frame_set(0)
        name='A_QBZ191_'+('' if family=='base' else family+'_')+kind
        path=export('Animations/'+family+'/'+name,[r],{'ARMATURE'},True,end)
        metadata[family+':'+kind]={'name':name,'family':family,'file':path,'sample_rate':240,'duration':end/60,'action':action.name}
        (O/'build.json').write_text(json.dumps(metadata,indent=2));print('QBZ_SEATED_CLIP',family,kind,flush=True)
pose(bpy.data.actions['QBZ191_base_idle'],0)
r.data.pose_position='REST';bpy.context.view_layer.update()
export('SK_QBZ191_Manny',[r,gun,mag,hands],{'ARMATURE','MESH'})
r.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_MagazineSeat_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'source':'QBZ191Folding20260913/QBZ191_Folding_Editable.blend','magazine_object':mag.name,'magazine_bone':'WPN_SOCKET_Magazine','assembly_correction_root_m':list(offset),'well_lip_z_m':lip_z,'seated_insertion_m':insertion_depth,'contact_frames':{'guide_aligned':72,'mouth_at_well':76,'locked':95,'release':98,'return_complete':126},'clips':len(metadata),'status':'authored and exported; no rendered or runtime acceptance'},indent=2))
print('QBZ_MAGAZINE_SEAT_EXPORTED',list(offset),flush=True)
