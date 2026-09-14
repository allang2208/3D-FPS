"""Meshy Starblade + current Manny arms, VRE grasp, CC0 sword motion adaptation.
Produces editable source and game assets; arm inspection is separately user-authorized.
"""
import bpy,json,math,sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).parent))
from arm_solver import ArmSolver
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
export('SM_AzureRunesword.fbx',[sword])
canonical=sword.data.copy()
base=Matrix.Translation((.13,.48,-.08))@Matrix.Rotation(math.radians(-18),4,'X')@Matrix.Rotation(math.radians(65),4,'Z')
# Keep the hand anatomy intact; close the palm-to-hilt radial gap by 2.5 mm.
for grasp in [HL,HR]:
    radial=Vector((grasp.translation.x,grasp.translation.y,0))
    if radial.length>.0025:grasp.translation-=radial.normalized()*.0025
solver=ArmSolver(rest,{'l':HL,'r':HR},{'l':left_rel,'r':right_rel})
solver.ready_pose(base)
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
def apply(swordframe,angles,support=None):
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:solver.apply_arm(p,side,solver.hand(side,swordframe,angles[side]),support[side] if support else None)
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
r.data.pose_position='REST';export('SK_AzureRunesword_Manny.fbx',[arms,sword,r]);r.data.pose_position='POSE'
idle=Matrix(motion['Sword_Idle'][0]['right']);C=Matrix.Rotation(math.pi,4,'Z');report={}
def sample(name,t):
    data=motion[name];x=min(len(data)-1,max(0,t*24));i=int(x);j=min(i+1,len(data)-1);a=Matrix(data[i]['right']);b=Matrix(data[j]['right']);u=x-i
    return Matrix.LocRotScale(a.translation.lerp(b.translation,u),a.to_quaternion().slerp(b.to_quaternion(),u),Vector((1,1,1)))

# The CC0 source's first slash winds up on the right and finishes down-left;
# the second gathers on the left and returns right. Reconstruct those phases
# around a two-hand grip, using a wide torso-led arc instead of damped wrist motion.
# Each row: seconds, guard position in metres, yaw / blade tilt / grip roll in degrees.
# Keys retain V2 source time; source_time() compresses contact to 0.23--0.345 s.
ready=(.13,.48,-.08,0,-18,65)
sweep_keys={
    'Slash1':[
        (0,*ready),
        (.07,.14,.36,-.07,-82,-18,45),
        (.14,.18,.32,-.03,-100,-80,30),
        (.23,.18,.34,-.06,-80,-85,25),
        (.335,0,.42,-.04,0,-85,25),
        (.46,-.18,.34,-.09,80,-85,25),
        (.55,-.20,.32,-.12,96,-85,30),
        (.65,-.12,.35,-.06,95,-18,45),
        (.75,.08,.44,-.07,40,-18,60),
        (20/24,*ready)],
    'Slash2':[
        (0,*ready),
        (.07,-.10,.36,-.08,85,-18,45),
        (.14,-.18,.32,-.09,100,-85,30),
        (.23,-.18,.34,-.09,80,-85,25),
        (.34,0,.42,-.04,0,-85,25),
        (.46,.18,.34,-.06,-80,-85,25),
        (.54,.20,.32,-.03,-96,-82,30),
        (.65,.16,.35,-.04,-95,-18,45),
        (.75,.14,.44,-.07,-40,-18,60),
        (20/24,*ready)]}

def source_time(t):
    if t<=.23:return t
    if t<=.345:return .23+(t-.23)*2
    return .46+(t-.345)*((20/24-.46)/(20/24-.345))

def sweep_pose(name,t):
    t=source_time(t)
    keys=sweep_keys[name]
    i=next((j for j in range(len(keys)-1) if t<=keys[j+1][0]),len(keys)-2)
    a,b=keys[i:i+2];dt=b[0]-a[0];u=max(0,min(1,(t-a[0])/dt))
    h00=2*u**3-3*u*u+1;h10=u**3-2*u*u+u
    h01=-2*u**3+3*u*u;h11=u**3-u*u
    values=[]
    for k in range(1,7):
        # Non-uniform cubic tangents keep the blade moving across the contact
        # interval, while first/last zero velocity gives a settled ready pose.
        ma=0 if i==0 else (b[k]-keys[i-1][k])/(b[0]-keys[i-1][0])
        mb=0 if i+1==len(keys)-1 else (keys[i+2][k]-a[k])/(keys[i+2][0]-a[0])
        values.append(h00*a[k]+h10*dt*ma+h01*b[k]+h11*dt*mb)
    x,y,z,yaw,tilt,roll=values
    return Matrix.Translation((x,y,z))@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(tilt),4,'X')@Matrix.Rotation(math.radians(roll),4,'Z')

# Bake the blade's contact sweep into two lightweight, camera-author-space
# crescent meshes. U reveals time along the slash; V fades the ribbon edges.
for clip in ['Slash1','Slash2']:
    verts=[];faces=[];uvs=[];segments=80;across=6
    for i in range(segments+1):
        u=i/segments;sf=sweep_pose(clip,.23+.115*u)
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

def pose_at(name,donor,t,duration):
    if name in sweep_keys:
        sf=sweep_pose(name,t)
    elif donor:
        m=sample(donor,t);delta=C.to_3x3()@(m.translation-idle.translation)*.70
        q=C.to_quaternion()@(m.to_quaternion()@idle.to_quaternion().inverted())@C.to_quaternion().inverted()
        sf=Matrix.LocRotScale(base.translation+delta,q@base.to_quaternion(),Vector((1,1,1)))
        if name=='Sprint':sf=Matrix.Translation((.03,-.04,-.09))@sf@Matrix.Rotation(math.radians(-32),4,'X')
        if name in ['Walk','Sprint']:
            # Periodic authoring closes the donor walk's asymmetric endpoint.
            fade=max(0,(t/duration-.78)/.22);fade=fade*fade*(3-2*fade)
            first=base if name=='Walk' else Matrix.Translation((.03,-.04,-.09))@base@Matrix.Rotation(math.radians(-32),4,'X')
            sf=Matrix.LocRotScale(sf.translation.lerp(first.translation,fade),sf.to_quaternion().slerp(first.to_quaternion(),fade),Vector((1,1,1)))
    else:
        u=t/duration;u=u*u*(3-2*u)
        sf=Matrix.Translation((0,-.08*(1-u),-.35*(1-u)))@base@Matrix.Rotation(math.radians(-42)*(1-u),4,'X')
    return sf

clips=[('Idle','Sword_Idle',80/24),('Walk','Sword_Walk',22/24),('Slash1','Sword_Slash1',20/24),('Slash2','Sword_Slash2',20/24),('Equip',None,.55),('Sprint','Sword_Walk',22/24)]
s.render.fps=240;s.render.fps_base=1
apply(base,solver.ready)
for name,donor,duration in clips:
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action
    s.frame_start=0;s.frame_end=round(duration*240);previous={}
    frames=[pose_at(name,donor,f/240,duration) for f in range(s.frame_end+1)]
    grasp_path=solver.fit_path(frames,name in ['Idle','Walk','Sprint'])
    support_path=solver.fit_support(frames,grasp_path)
    (P/('grasp_path_'+name+'.json')).write_text(json.dumps(grasp_path))
    for f in range(s.frame_end+1):
        s.frame_set(f);t=f/240
        sf=frames[f];apply(sf,{side:grasp_path[side][f] for side in ['l','r']},{side:support_path[side][f] for side in ['l','r']})
        for b in r.pose.bones:
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_quaternion=q;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    export('A_RuneSword_'+name+'.fbx',[r],True)
    report[name]={'duration':duration,'fps':240,'frames':s.frame_end+1,'loop':name in ['Idle','Walk','Sprint'],'reference':donor,'contact_window':[.23,.345] if name.startswith('Slash') else None}
    print('AUTHORED',name,flush=True)
r.animation_data.action=bpy.data.actions['A_RuneSword_Idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=800;s.frame_set(0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'CompactNaturalV4','geometry_scale_from_v3':.8,'blade_roll_from_v3_degrees':-20,'ready_guard_cm':[13,48,-8],'idle_blade_roll_delta_degrees':70,'fast_phase_seconds':[.23,.345],'fast_phase_speed_multiplier':2,'ready_grasp_degrees':{k:math.degrees(v) for k,v in solver.ready.items()},'contact_yaw_degrees':160,'sweep_keys_in_v2_source_time':sweep_keys,'clips':report,'grips_cm':{'right_below_guard':7.2,'left_below_guard':17.2},'source':str(source),'donor':'BigAndCrispy/Unity-First-Person-Melee CC0 (one-handed phases reconstructed as two-handed sweeps)','source_triangles':count,'game_triangles':len(canonical.polygons)},indent=2))
