"""Meshy Starblade + current Manny arms, VRE grasp, CC0 sword motion adaptation.
Produces editable source and game assets; arm inspection is separately user-authorized.
"""
import bpy,json,math,sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).parent))
from arm_solver import ArmSolver
from diagonal_motion import poses,READY,IDLE_FACE,WINDUP_END,CONTACT_START,CONTACT_END,ATTACK_END
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).parent; ROOT=P.parent; OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
motion=json.loads((ROOT/'Reference/motion.json').read_text())
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def export(path,obs,animation=False):
    select(obs)
    bpy.ops.export_scene.fbx(filepath=str(OUT/path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=animation,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,mesh_smooth_type='FACE',use_tspace=True)
source=ROOT.parent/'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;s.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];arms=bpy.data.objects['SK_Manny_Arms_Export']
select([r]);bpy.ops.object.mode_set(mode='EDIT')
wr=r.data.edit_bones['WPN_root'].matrix.copy()
for name,z in [('Blade_Base',.03),('Blade_Tip',1.0)]:
    b=r.data.edit_bones.new(name);b.parent=r.data.edit_bones['WPN_root'];b.head=wr@Vector((0,0,z));b.tail=wr@Vector((0,.025,z));b.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
pose={b.name:b.matrix.copy() for b in r.pose.bones}
fit=json.loads((ROOT.parent/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G=pose['WPN_root']@Matrix(fit['grip_in_root']);S=Matrix.Diagonal((-1,1,1,1));GR=S@G@S
leftnames=[b.name for b in r.pose.bones if b.name.endswith('_l') and any(b.name.startswith(x) for x in ['index','middle','ring','pinky','thumb'])]
left_rel={n:pose['hand_l'].inverted()@pose[n] for n in leftnames}
mirrored={n[:-1]+'r':S@(pose[n]@rest[n].inverted())@S@rest[n[:-1]+'r'] for n in ['hand_l']+leftnames}
right_rel={n:mirrored['hand_r'].inverted()@m for n,m in mirrored.items() if n!='hand_r'}
HL=Matrix.Translation((0,0,.06))@G.inverted()@pose['hand_l']
HR=Matrix.Translation((0,0,.06))@GR.inverted()@mirrored['hand_r']
for o in list(bpy.context.scene.objects):
    if o not in [r,arms]:bpy.data.objects.remove(o,do_unlink=True)
r.animation_data_clear()
for b in r.pose.bones:
    for c in list(b.constraints):b.constraints.remove(c)
    b.matrix_basis=Matrix.Identity(4)
r.name='SK_RuneSword_Rig'
for m in arms.modifiers:
    if m.type=='ARMATURE':m.object=r
bpy.ops.import_scene.fbx(filepath=str(next((ROOT/'Original').rglob('*.fbx'))))
sword=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=arms)
sword.data.transform(sword.matrix_world);sword.matrix_world=Matrix.Identity(4);sword.name='SM_AzureRunesword'
# Real grip contact, not bounds centering: guard at original z=-0.32 m.
# Retain blade silhouette; reshape only the oversized generated handle to fit two fists.
for v in sword.data.vertices:
    z=v.co.z;v.co*=.80;v.co.z=(z+.32)*.80
    if z<-.32:v.co.z*=.70
    if -.79<z<-.365:
        blend=min(1,(z+.79)/.045,(-.365-z)/.035);blend=max(0,blend)
        v.co.x*=1-.60*blend;v.co.y*=1-.38*blend
mat=bpy.data.materials.new('M_AzureRunesword');mat.use_nodes=True;sword.data.materials.clear();sword.data.materials.append(mat)
nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
texroot=next((ROOT/'Original').rglob('*.fbx')).parent;stem=next(texroot.glob('*.fbx')).stem
for suffix,socket,colorspace in [('', 'Base Color','sRGB'),('_metallic','Metallic','Non-Color'),('_roughness','Roughness','Non-Color'),('_emission','Emission Color','sRGB'),('_normal','Normal','Non-Color')]:
    img=bpy.data.images.load(str(texroot/(stem+suffix+'.png')),check_existing=True);img.colorspace_settings.name=colorspace
    node=nt.nodes.new('ShaderNodeTexImage');node.image=img
    if suffix=='_normal':
        normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(node.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    else:nt.links.new(node.outputs['Color'],bs.inputs[socket])
bs.inputs['Emission Strength'].default_value=3.5
sword.data.calc_loop_triangles();count=len(sword.data.loop_triangles)
# Keep original as separate asset source, use 48k triangle game mesh.
dec=sword.modifiers.new('Game LOD0 silhouette','DECIMATE');dec.ratio=min(1,48000/count);dec.use_collapse_triangulate=True
select([sword]);bpy.ops.object.modifier_apply(modifier=dec.name)
# Uniform 80 percent of the accepted V3 geometry, pivoted at the guard.
for v in sword.data.vertices:v.co*=.8
# Existing static mesh and skin remain installed; this revision authors animation only.
canonical=sword.data.copy()
base=READY
face_flip=IDLE_FACE
# Keep the hand anatomy intact; close the palm-to-hilt radial gap by 2.5 mm.
for grasp in [HL,HR]:
    radial=Vector((grasp.translation.x,grasp.translation.y,0))
    if radial.length>.0025:grasp.translation-=radial.normalized()*.0025
solver=ArmSolver(rest,{'l':HL,'r':HR},{'l':left_rel,'r':right_rel})
solver.ready_pose(base)
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
def apply(gripframe,angles,support=None,swordframe=None):
    swordframe=swordframe if swordframe is not None else gripframe@face_flip
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:solver.apply_arm(p,side,solver.hand(side,gripframe,angles[side]),support[side] if support else None)
    p['WPN_root']=swordframe
    for n in ['Blade_Base','Blade_Tip']:
        local=rest['WPN_root'].inverted()@rest[n];local.translation*=.8
        p[n]=swordframe@local
    for b in r.pose.bones:
        b.matrix_basis=localrest[b.name].inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
    bpy.context.view_layer.update()
# Bind the blade to the existing weapon bone without modifying Manny rest pose.
sword.data.transform(rest['WPN_root']);sword.parent=r
vg=sword.vertex_groups.new(name='WPN_root');vg.add(list(range(len(sword.data.vertices))),1,'REPLACE')
mod=sword.modifiers.new('Weapon bone','ARMATURE');mod.object=r
sword.name='RuneSword_Blade'
r.data.pose_position='POSE'
report={}

# Bake the blade's contact sweep into two lightweight, camera-author-space
# crescent meshes. U reveals time along the slash; V fades the ribbon edges.
for clip in ['Slash1','Slash2']:
    verts=[];faces=[];uvs=[];segments=80;across=6
    for i in range(segments+1):
        u=i/segments;_,sf=poses(clip,CONTACT_START+(CONTACT_END-CONTACT_START)*u)
        for j in range(across+1):
            v=j/across;verts.append(tuple(sf@Vector((0,0,(.25+.83*v)*.8))));uvs.append((u,v))
    for i in range(segments):
        for j in range(across):
            a=i*(across+1)+j;faces.append((a,a+1,a+across+2,a+across+1))
    mesh=bpy.data.meshes.new('RuneRift_'+clip);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new('SM_RuneRift_'+clip,mesh);s.collection.objects.link(ob)
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
    export('SM_RuneRift_'+clip+'.fbx',[ob]);bpy.data.objects.remove(ob,do_unlink=True)

clips=[('Slash1',ATTACK_END),('Slash2',ATTACK_END)]
s.render.fps=240;s.render.fps_base=1
apply(base,solver.ready)
for name,duration in clips:
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action
    s.frame_start=0;s.frame_end=round(duration*240);previous={}
    paired_frames=[poses(name,f/240) for f in range(s.frame_end+1)]
    frames=[pair[0] for pair in paired_frames]
    hold=(math.ceil(WINDUP_END*240),math.floor(CONTACT_START*240))
    grasp_path=solver.fit_path(frames,False,hold)
    support_path=solver.fit_support(frames,grasp_path,hold)
    support_path=solver.separate_arms(frames,grasp_path,support_path,hold)
    (P/('grasp_path_'+name+'.json')).write_text(json.dumps(grasp_path))
    for f in range(s.frame_end+1):
        s.frame_set(f);t=f/240
        sf=frames[f];apply(sf,{side:grasp_path[side][f] for side in ['l','r']},{side:support_path[side][f] for side in ['l','r']},paired_frames[f][1])
        for b in r.pose.bones:
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_quaternion=q;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    export('A_RuneSword_'+name+'.fbx',[r],True)
    report[name]={'duration':duration,'fps':240,'frames':s.frame_end+1,'loop':False,'contact_window':[CONTACT_START,CONTACT_END],'hold_window':[WINDUP_END,CONTACT_START]}
    print('AUTHORED',name,flush=True)
# Retain exact accepted idle/locomotion/equip actions in the editable source.
with bpy.data.libraries.load(str(ROOT/'WeightLeftV5/AzureRunesword_Manny_Editable.blend'),link=False) as (src,dst):
    dst.actions=['A_RuneSword_'+n for n in ['Idle','Walk','Equip','Sprint']]
r.animation_data.action=bpy.data.actions['A_RuneSword_Idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=800;s.frame_set(0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'DiagonalHeavyV6','geometry_scale_from_v3':.8,'idle_blade_roll_degrees':115,'blade_contact_orientation':'width axis tangent to diagonal arc; independent of idle face','windup_seconds':WINDUP_END,'hold_seconds':CONTACT_START-WINDUP_END,'fast_phase_seconds':[CONTACT_START,CONTACT_END],'attack_seconds':ATTACK_END,'contact_arc_degrees':220,'followthrough_arc_end_degrees':208,'load_guard_cm':[27,30,10],'finish_guard_cm':[-37,26,-31],'second_slash':'mirror weapon trajectory across X; preserve anatomical left/right grips','ready_grasp_degrees':{k:math.degrees(v) for k,v in solver.ready.items()},'clips':report,'source':str(source),'retained_actions_source':str(ROOT/'WeightLeftV5/AzureRunesword_Manny_Editable.blend'),'arm_solution':'continuous grasp path, fixed load hold, joint elbow separation, unchanged bone lengths/rest/weights'},indent=2))
