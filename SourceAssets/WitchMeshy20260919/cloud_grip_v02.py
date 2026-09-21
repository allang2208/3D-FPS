"""Cloud-native Witch motion, localized left-hand skin/grip authoring.

Keeps the Meshy skeleton/UV/materials; no full-body retarget or new generation.
No preview render, PIE, or gameplay test is performed.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(__file__).resolve().parent
AUTHOR=ROOT/'Authoring/CloudGripV02'; DELIVERY=ROOT/'Delivery/CloudGripV02'
AUTHOR.mkdir(parents=True,exist_ok=True); DELIVERY.mkdir(parents=True,exist_ok=True)
PLAN=json.loads((ROOT/'motion_plan.json').read_text())

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=120
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1

def export(path, animated):
    bpy.ops.object.select_all(action='DESELECT')
    objects=[o for o in bpy.context.scene.objects if o.type in {'MESH','ARMATURE','EMPTY'}]
    for o in objects: o.select_set(True)
    bpy.context.view_layer.objects.active=next((o for o in objects if o.type=='ARMATURE'),objects[0])
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH','EMPTY'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=animated,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)

def frame(value):
    bpy.context.scene.frame_set(math.floor(value),subframe=value-math.floor(value))

def smooth(v):
    v=max(0,min(1,v)); return v*v*(3-2*v)

def hand_frame(rig):
    rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    wrist=rest['LeftHand'].translation
    axis=(wrist-rest['LeftForeArm'].translation).normalized()
    forward=(rest['headfront'].translation-rest['Head'].translation).normalized()
    palm=(forward-axis*forward.dot(axis)).normalized()
    width=axis.cross(palm).normalized()
    return rest,wrist,axis,palm,width

def fit_hand(rig):
    rest,wrist,axis,palm,width=hand_frame(rig)
    touched=curled=0
    for mesh in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        fore=mesh.vertex_groups.get('LeftForeArm'); hand=mesh.vertex_groups.get('LeftHand')
        if not fore or not hand: continue
        inv=mesh.matrix_world.inverted()
        normals=[n.vector.copy() for n in mesh.data.corner_normals]
        bent_normals={}
        for vertex in mesh.data.vertices:
            weights={g.group:g.weight for g in vertex.groups}
            wfore=weights.get(fore.index,0); whand=weights.get(hand.index,0)
            if wfore+whand<.25: continue
            point=mesh.matrix_world@vertex.co; offset=point-wrist; distance=offset.length
            axial=offset.dot(axis)
            if distance>.20 or point.x<wrist.x-.035: continue
            blend=smooth((axial+.03)/.06)
            amount=wfore*blend
            if amount>1e-5:
                hand.add([vertex.index],whand+amount,'REPLACE')
                fore.add([vertex.index],max(0,wfore-amount),'REPLACE'); touched+=1
            # Keep palm/wrist shape. Curl the distal finger region into a static
            # staff grasp; the left hand retains its staff in all living actions.
            if axial>.045:
                radius=.027
                theta=min(2.65,(axial-.045)/radius)
                bent=.045+radius*math.sin(theta)
                inward=radius*(1-math.cos(theta))
                confidence=min(1,wfore+whand)*smooth((axial-.045)/.02)
                vertex.co=inv@(point+confidence*(axis*(bent-axial)+palm*inward))
                bent_normals[vertex.index]=Quaternion(width,theta*confidence)
                curled+=1
        for loop in mesh.data.loops:
            rotation=bent_normals.get(loop.vertex_index)
            if rotation:
                world_normal=mesh.matrix_world.to_3x3()@normals[loop.index]
                normals[loop.index]=(inv.to_3x3()@(rotation@world_normal)).normalized()
        mesh.data.normals_split_custom_set(normals)
    return {'reweighted_vertices':touched,'curled_vertices':curled,
            'grip_from_wrist_m':list(axis*.045+palm*.027),
            'shaft_axis_in_reference':list(-width),'finger_joints_added':False}

def native_motion(role, plan):
    clear()
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'Meshy'/('animation_'+role)/'downloads/result_animation_glb_url.glb'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    for obj in bpy.context.scene.objects:
        data=obj.animation_data
        if not data: continue
        action=data.action; slot=data.action_slot if action else None
        if not action:
            strip=next((s for t in data.nla_tracks for s in t.strips if s.action),None)
            if strip: action,slot=strip.action,strip.action_slot
        for track in list(data.nla_tracks): data.nla_tracks.remove(track)
        if action:
            data.action=action
            if slot: data.action_slot=slot
    action=rig.animation_data.action; begin,end=map(float,action.frame_range)
    duration=plan['target_duration_seconds']; count=round(duration*120)
    rest,wrist,axis,palm,width=hand_frame(rig)
    basis=Matrix((axis,palm,width)).transposed()
    target=Matrix((Vector((0,-1,0)),Vector((-1,0,0)),Vector((0,0,-1)))).transposed()
    hand_rotation=(target@basis.transposed()).to_quaternion()@rest['LeftHand'].to_quaternion()
    samples=[]
    for index in range(count+1):
        frame(begin+(end-begin)*index/count)
        samples.append({b.name:(b.location.copy(),b.rotation_quaternion.copy(),b.scale.copy()) for b in rig.pose.bones})
    rig.animation_data_clear(); rig.animation_data_create()
    output=bpy.data.actions.new('A_Witch_'+role+'_CloudGripV02'); rig.animation_data.action=output
    drift=samples[-1]['Hips'][0]-samples[0]['Hips'][0]
    # Determine the horizontal root correction in world space, retaining vertical
    # breathing/foot support and the death pelvis trajectory.
    hip=rig.data.bones['Hips']
    hip_to_world=(rig.matrix_world@hip.matrix_local).to_3x3()
    world_drift=hip_to_world@drift; world_drift.z=0
    local_drift=hip_to_world.inverted()@world_drift
    loop=plan['loop']; last={}
    for index,sample in enumerate(samples):
        bpy.context.scene.frame_set(index)
        phase=index/count
        close=smooth((phase-.92)/.08) if loop else 0
        for pose in rig.pose.bones:
            location,rotation,scale=(v.copy() for v in sample[pose.name])
            if loop and pose.name=='Hips': location-=local_drift*phase
            if close:
                first=samples[0][pose.name]
                location=location.lerp(first[0],close); rotation=rotation.slerp(first[1],close)
                scale=scale.lerp(first[2],close)
            pose.rotation_mode='QUATERNION'; pose.location=location; pose.rotation_quaternion=rotation; pose.scale=scale
        bpy.context.view_layer.update()
        if role!='DeathBackward':
            pose=rig.pose.bones['LeftHand']
            world=rig.matrix_world@pose.matrix
            pose.matrix=rig.matrix_world.inverted()@Matrix.LocRotScale(world.translation,hand_rotation,world.to_scale())
            bpy.context.view_layer.update()
        for pose in rig.pose.bones:
            if pose.name in last and pose.rotation_quaternion.dot(last[pose.name])<0: pose.rotation_quaternion.negate()
            last[pose.name]=pose.rotation_quaternion.copy()
            for channel in ['location','rotation_quaternion','scale']: pose.keyframe_insert(channel,frame=index,group=pose.name)
    skin=fit_hand(rig)
    scene=bpy.context.scene; scene.frame_start=0; scene.frame_end=count; scene.frame_set(0)
    for event,seconds in plan.get('events_seconds',{}).items(): scene.timeline_markers.new(event,frame=round(seconds*120))
    scene['route']='Meshy cloud applied animation; original hierarchy; left wrist/palm grip fit'
    scene['visual_or_runtime_tested']=False
    bpy.ops.file.pack_all()
    blend=AUTHOR/f'Witch_{role}_CloudGripV02.blend'; fbx=DELIVERY/f'A_Witch_{role}_CloudGripV02.fbx'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend)); export(fbx,True)
    return {'role':role,'source_seconds':(end-begin)/120,'seconds':duration,'fps':120,
            'skin':skin,'blend':str(blend.relative_to(ROOT)),'fbx':str(fbx.relative_to(ROOT))}

records=[native_motion(p['name'],p) for p in PLAN['actions']]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Witch_Rigged_Candidate_v01.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
skin=fit_hand(rig)
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(AUTHOR/'Witch_GripBodyV02.blend'))
export(DELIVERY/'SK_Witch_GripBodyV02.fbx',False)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Witch_Staff_Candidate_v01.blend'))
section=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH'
         for v in o.data.vertices if abs((o.matrix_world@v.co).z-.92)<.025]
staff_grip=[(min(p[i] for p in section)+max(p[i] for p in section))*.5 for i in (0,1)]+[.92]
for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
    obj.matrix_world=Matrix.Translation(Vector((-staff_grip[0],-staff_grip[1],0)))@obj.matrix_world
bpy.context.view_layer.update()
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(AUTHOR/'Witch_StaffGripV02.blend'))
export(DELIVERY/'SM_Witch_StaffGripV02.fbx',False)
manifest={'route':'Meshy cloud applied; no local full-body retarget','body_skin':skin,
          'staff_grip_local_cm':[v*100 for v in staff_grip],'actions':records,'tested':False}
(ROOT/'cloud_grip_v02_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('CLOUD_GRIP_V02_EXPORTED '+json.dumps(manifest))
