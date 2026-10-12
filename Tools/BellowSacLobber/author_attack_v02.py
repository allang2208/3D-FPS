"""Original non-linear pressure/spit and close shove on the unchanged SmartRig."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012')
OUT=ROOT/'CombatV02'
OUT.mkdir(exist_ok=True)
# Reuse the existing anatomical rest/leg solver without executing its exports.
source=Path('D:/FPS3D/FPSGAME/Tools/BellowSacLobber/author_locomotion.py').read_text(encoding='utf-8')
exec(compile(source.split('for obj in bpy.context.scene.objects:')[0], 'bellow_original_leg_solver', 'exec'))

def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]

def attack_pose(t,kind):
    desired={}
    if kind=='Lob':
        load=curve(t,[(0,0),(.30,.28),(.88,1),(1.08,1),(1.25,0),(2.2,0)])
        recoil=curve(t,[(0,0),(1.13,0),(1.28,1),(1.48,-.22),(1.85,0),(2.2,0)])
        settle=curve(t,[(0,0),(.9,1),(1.08,1),(1.22,-.3),(1.6,.18),(2.2,0)])
        offset=Vector((.006*load,.052*load+.07*recoil,-.065*load-.02*recoil))
        pitch=math.radians(-2.2*load+2.8*recoil)
        chest_pitch=math.radians(-3.0*load+3.6*recoil)
        sac=curve(t,[(0,0),(.32,.02),(.95,.085),(1.10,.095),(1.25,-.055),(1.55,-.022),(2.2,0)])
        nozzle=curve(t,[(0,0),(.45,3),(.90,7),(1.12,7),(1.23,-5),(1.48,2),(2.08,0)])
    else:
        load=curve(t,[(0,0),(.25,1),(.40,0),(.60,0),(1.05,0)])
        thrust=curve(t,[(0,0),(.28,0),(.40,1),(.49,.85),(.76,.22),(1.05,0)])
        offset=Vector((0,.045*load-.13*thrust,-.035*load-.018*thrust))
        pitch=math.radians(-1.5*load+2.3*thrust)
        chest_pitch=math.radians(2.0*thrust)
        sac=.012*load-.025*thrust
        nozzle=-3.5*thrust
    pivot=heads['Bone_000']
    body=Matrix.Translation(offset) @ Matrix.Translation(pivot) @ Matrix.Rotation(pitch,4,'X') @ Matrix.Translation(-pivot)
    desired['Bone_000']=body @ rest['Bone_000']
    cp=heads['Bone_001']
    chest=body @ Matrix.Translation(cp) @ Matrix.Rotation(chest_pitch,4,'X') @ Matrix.Translation(-cp)
    for n in ('Bone_001','Bone_003','Bone_002'):desired[n]=chest @ rest[n]
    for n,weight in (('Bone_017',.32),('Bone_016',1.)):
        mat=chest @ rest[n]
        desired[n]=Matrix.LocRotScale(mat.translation,mat.to_quaternion(),Vector((1+sac*weight,1+sac*.75*weight,1+sac*weight)))
    # Apply pitch about the model's transverse axis, transformed to each bone.
    for i,n in enumerate(('Bone_031','Bone_030','Bone_029','Bone_028')):
        parent=rig.data.bones[n].parent.name
        mat=desired[parent] @ rest[parent].inverted() @ rest[n]
        axis=mat.to_quaternion().inverted() @ Vector((1,0,0))
        # Model forward is -Y: negative X rotation raises the nozzle.
        desired[n]=mat @ Quaternion(axis,math.radians(-nozzle)*(.30 if i<2 else .20)).to_matrix().to_4x4()
    for chain in chains.values():solve_leg(chain,chest,Vector((0,0,0)),desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:desired[n]=desired[parent] @ rest[parent].inverted() @ rest[n] if parent else rest[n].copy()
        pb.matrix_basis=rest[n].inverted() @ rest[parent] @ desired[parent].inverted() @ desired[n] if parent else rest[n].inverted() @ desired[n]
    bpy.context.view_layer.update()

for o in bpy.context.scene.objects:o.select_set(False)
rig.select_set(True)
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=rig
clips=[]
for kind,duration,contact in [('Lob',2.2,1.2),('Shove',1.05,.4)]:
    action=bpy.data.actions.new('A_BellowSacLobber_'+kind+'_v02');action.use_fake_user=True
    rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*60)+1
    for i in range(scene.frame_end):
        scene.frame_set(i+1);attack_pose(i/60.,kind)
        for pb in rig.pose.bones:
            for prop in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=prop,frame=i+1,group=pb.name)
    fbx=OUT/('A_BellowSacLobber_'+kind+'_v02.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=True,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',mesh_smooth_type='FACE',use_mesh_modifiers=False,
        bake_anim=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0.)
    clips.append({'role':kind,'file':str(fbx),'duration':duration,'contact':contact,'fps':60,'root_motion':False})
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BellowSacLobber_attack_v02.blend'))

# Projectile meshes: opaque lobed membrane capsule and a thin contact-plane warning ring.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,radius=1.)
capsule=bpy.context.object;capsule.name='SM_BellowSacCapsule'
for v in capsule.data.vertices:
    p=v.co.normalized();angle=math.atan2(p.y,p.x)
    rib=.028*math.sin(angle*7.+p.z*2.3)*(1.-p.z*p.z)
    wrinkle=.008*math.sin(p.x*29.+p.y*11.)*math.sin(p.z*17.)
    v.co=Vector((p.x*.083,p.y*.083,p.z*.097))*(1.+rib+wrinkle)
for p in capsule.data.polygons:p.use_smooth=True
capsule_path=OUT/'SM_BellowSacCapsule.fbx'
bpy.ops.export_scene.fbx(filepath=str(capsule_path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',bake_anim=False)
capsule.select_set(False)
vertices=[];faces=[]
for i in range(96):
    a=2*math.pi*i/96
    for radius in (.99,1.):vertices.append((radius*math.cos(a),radius*math.sin(a),0))
for i in range(96):
    j=(i+1)%96;faces.append((i*2,j*2,j*2+1,i*2+1))
mesh=bpy.data.meshes.new('BellowRuptureRing');mesh.from_pydata(vertices,[],faces);mesh.update()
ring=bpy.data.objects.new('SM_BellowRuptureRing',mesh);scene.collection.objects.link(ring)
ring.select_set(True);bpy.context.view_layer.objects.active=ring
ring_path=OUT/'SM_BellowRuptureRing.fbx'
bpy.ops.export_scene.fbx(filepath=str(ring_path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BellowSac_projectile_source_v02.blend'))
record={'clips':clips,'capsule_mesh':str(capsule_path),'ring_mesh':str(ring_path),'target_lock_seconds':.85,
    'release_seconds':1.2,'impact_fuse_seconds':.65,'blast_radius_cm':140,'nozzle_bone':'Bone_028',
    'muzzle_local_offset':[0,.13,0],'model_and_skin':'unchanged V01','runtime_tested':False}
(OUT/'combat_manifest_v02.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('BELLOW_COMBAT_AUTHORED '+json.dumps(record),flush=True)
