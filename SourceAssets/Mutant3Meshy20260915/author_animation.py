"""Adapt CC0 poses and retain the user's locomotion on the original Meshy skin."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(__file__).parent
OUT=ROOT/'final'; OUT.mkdir(exist_ok=True)
FPS=120
meta=json.loads((ROOT/'authoring_inputs.json').read_text())
native=json.loads((ROOT/'native_retarget.json').read_text())

def activate(rig, action):
    rig.animation_data_create(); rig.animation_data.action=action
    if action and action.slots: rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute=True

def frame_at(f): bpy.context.scene.frame_set(math.floor(f), subframe=f%1)

cache={}
for role in ['Idle','Scratch','Stagger','Death','Rage','Walking','Running','RunFast']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    original=role in meta['meshy_clips']
    if original: bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'Meshy_{role}_Source.blend'))
    else: bpy.ops.import_scene.fbx(filepath=str(ROOT/f'native_retarget/A_Mutant3_Raw_{role}.fbx'))
    donor=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=donor.animation_data.action; activate(donor,action)
    rate=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    start=action.frame_range[0]
    seconds=meta['meshy_clips'][role]['seconds'] if original else native['A_Mutant3_Raw_'+role]['seconds']
    rest={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
    samples=[]
    intervals=round(seconds*FPS)
    for i in range(intervals+1):
        frame_at(start+(i/FPS)*rate)
        samples.append({b.name:donor.matrix_world@b.matrix for b in donor.pose.bones})
    cache[role]=(rest,samples)

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Mutant3_Meshy_Source.blend'))
scene=bpy.context.scene; scene.render.fps=FPS; scene.render.fps_base=1
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
for ob in list(bpy.data.objects):
    if ob not in [rig]+meshes: bpy.data.objects.remove(ob,do_unlink=True)
activate(rig,None)
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
world_rest={n:rig.matrix_world@m for n,m in rest.items()}
inverse_world=rig.matrix_world.inverted()
ordered=list(rig.pose.bones)
for pb in ordered: pb.rotation_mode='QUATERNION'

mat=bpy.data.materials.new('M_Mutant3_Meshy'); mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
for i,(socket,suffix) in enumerate([('Base Color','_texture_0.png'),('Normal','_texture_0_normal.png'),('Roughness','_texture_0_roughness.png'),('Metallic','_texture_0_metallic.png')]):
    im=bpy.data.images.load(str(next((ROOT/'sources/meshy').rglob('*'+suffix))),check_existing=True)
    im.colorspace_settings.name='sRGB' if socket=='Base Color' else 'Non-Color'; im.pack()
    node=mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image=im; node.location=(-600,300-i*250)
    output=node.outputs['Color']
    if socket=='Normal':
        normal=mat.node_tree.nodes.new('ShaderNodeNormalMap')
        mat.node_tree.links.new(output,normal.inputs['Color']); output=normal.outputs['Normal']
    mat.node_tree.links.new(output,bsdf.inputs[socket])
for mesh in meshes: mesh.data.materials.clear(); mesh.data.materials.append(mat)

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a))); return t*t*(3-2*t)

def pose(role, phase):
    raw_rest, samples=cache[role]
    index=max(0,min(1,phase))*(len(samples)-1)
    lo=int(index); hi=min(lo+1,len(samples)-1); alpha=index-lo
    matrices={}
    for name, r in rest.items():
        a,b=samples[lo][name],samples[hi][name]
        q=a.to_quaternion().slerp(b.to_quaternion(),alpha)
        delta=q@raw_rest[name].to_quaternion().inverted()
        q=(inverse_world.to_quaternion()@delta@world_rest[name].to_quaternion()).normalized()
        bone=rig.data.bones[name]
        if bone.parent: position=matrices[bone.parent.name]@(rest[bone.parent.name].inverted()@r).translation
        else:
            # Native UE FBX animation positions already evaluate in meters.
            position=inverse_world@a.translation.lerp(b.translation,alpha)
            if role in meta['meshy_clips']:
                drift=inverse_world.to_3x3()@(samples[-1][name].translation-samples[0][name].translation)
                position-=Vector((drift.x,drift.y,0))*phase
        m=Matrix.LocRotScale(position,q,Vector((1,1,1))); matrices[name]=m
        rig.pose.bones[name].matrix_basis=((rest[bone.parent.name].inverted()@r).inverted()@matrices[bone.parent.name].inverted()@m if bone.parent else r.inverted()@m)
    bpy.context.view_layer.update()

def ground(role,phase):
    # The supplied running includes airborne phases: retain its authored height.
    if role in meta['meshy_clips']: return
    deps=bpy.context.evaluated_depsgraph_get(); low=float('inf')
    for mesh in meshes:
        evaluated=mesh.evaluated_get(deps); data=evaluated.to_mesh()
        low=min(low,min((evaluated.matrix_world@v.co).z for v in data.vertices))
        evaluated.to_mesh_clear()
    correction=.003-low
    if role=='Death' and correction<0: correction*=smooth(.48,.7,phase)
    hips=rig.pose.bones['Hips']; m=hips.matrix.copy()
    m.translation+=inverse_world.to_3x3()@Vector((0,0,correction)); hips.matrix=m
    bpy.context.view_layer.update()

specs={'Idle':('Idle',352,True),'Attack':('Scratch',138,False),
       'Stagger':('Stagger',108,False),'Death':('Death',260,False),
       'Rage':('Rage',440,False),'Walking':('Walking',114,True),
       'Running':('Running',74,True),'RunFast':('RunFast',54,True)}
actions={}; contract={}
for name,(source,intervals,loop) in specs.items():
    action=bpy.data.actions.new('A_Mutant3_'+name); action.use_fake_user=True; activate(rig,action)
    scene.frame_start=0; scene.frame_end=intervals
    previous={}; first={}
    for frame in range(intervals+1):
        scene.frame_set(frame); phase=frame/intervals
        if name=='Stagger':
            seconds=frame/FPS
            source_phase=(.24*smooth(0,.1,seconds) if seconds<=.6 else .24+.76*smooth(.6,.9,seconds))
        else: source_phase=phase
        pose(source,source_phase); ground(source,source_phase)
        if frame==0: first={pb.name:pb.matrix_basis.copy() for pb in ordered}
        # Blend the last 80 ms into the first pose without flattening the stride.
        seam=smooth(max(0,1-.08/(intervals/FPS)),1,phase) if loop else 0
        for pb in ordered:
            if seam>0:
                loc,q,scale=pb.matrix_basis.decompose(); endloc,endq,endscale=first[pb.name].decompose()
                pb.matrix_basis=Matrix.LocRotScale(loc.lerp(endloc,seam),q.slerp(endq,seam),scale.lerp(endscale,seam))
            q=pb.rotation_quaternion.copy()
            if pb.name in previous and q.dot(previous[pb.name])<0: q.negate()
            pb.rotation_quaternion=q; previous[pb.name]=q.copy(); pb.scale=(1,1,1)
            for prop in ['location','rotation_quaternion','scale']: pb.keyframe_insert(prop,frame=frame,group=pb.name)
        if frame%120==0: print(f'MUTANT3_AUTHOR {name} {frame}/{intervals}',flush=True)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points: key.interpolation='LINEAR'
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+meshes: ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'A_Mutant3_{name}.fbx'),use_selection=True,
        object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',path_mode='STRIP')
    actions[name]=action
    contract[name]={'source':meta['meshy_clips'][source]['action'] if source in meta['meshy_clips'] else meta['donor_clips'][source]['source'],
        'origin':'User Meshy archive' if source in meta['meshy_clips'] else 'Mesh2Motion CC0',
        'fps':FPS,'frames':[0,intervals],'seconds':intervals/FPS,'loop':loop}
activate(rig,actions['Idle']); scene.frame_start=0; scene.frame_end=352; scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Mutant3_Meshy_Animated.blend'))
(ROOT/'animation_contract.json').write_text(json.dumps({'clips':contract,'attack_contact_seconds':[.40,.51],
    'parry':'immediate cancel and knockback; rewind from contact pose 0.3s then Stagger',
    'death_ragdoll_fraction':.6,'state':'Authored assets; user gameplay/visual testing pending'},indent=2),encoding='utf-8')
print('MUTANT3_ANIMATION_AUTHORING_COMPLETE',flush=True)
