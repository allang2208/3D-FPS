"""Meshy Starblade + current Manny arms, VRE grasp, CC0 sword motion adaptation.
Produces editable source and game assets. No acceptance renders or tests.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).parent; OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
motion=json.loads((P/'Reference/motion.json').read_text())
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def export(path,obs,animation=False):
    select(obs)
    bpy.ops.export_scene.fbx(filepath=str(OUT/path),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=animation,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,mesh_smooth_type='FACE',use_tspace=True)
source=P.parent/'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;s.frame_set(0);r=bpy.data.objects['SK_M4_Infima'];arms=bpy.data.objects['SK_Manny_Arms_Export']
select([r]);bpy.ops.object.mode_set(mode='EDIT')
wr=r.data.edit_bones['WPN_root'].matrix.copy()
for name,z in [('Blade_Base',.03),('Blade_Tip',1.0)]:
    b=r.data.edit_bones.new(name);b.parent=r.data.edit_bones['WPN_root'];b.head=wr@Vector((0,0,z));b.tail=wr@Vector((0,.025,z));b.use_deform=True
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
pose={b.name:b.matrix.copy() for b in r.pose.bones}
fit=json.loads((P.parent/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
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
bpy.ops.import_scene.fbx(filepath=str(next((P/'Original').rglob('*.fbx'))))
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
texroot=next((P/'Original').rglob('*.fbx')).parent;stem=next(texroot.glob('*.fbx')).stem
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
export('SM_AzureRunesword.fbx',[sword])
canonical=sword.data.copy()
base=Matrix.Translation((.15,.36,-.13))@Matrix.Rotation(math.radians(-18),4,'X')@Matrix.Rotation(math.radians(-5),4,'Z')
grips={'l':Matrix.Translation((0,0,-.215))@Matrix.Rotation(math.radians(65),4,'Z')@HL,'r':Matrix.Translation((0,0,-.09))@Matrix.Rotation(math.radians(-65),4,'Z')@HR}
localrest={n:(rest[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in rest.items()}
def arm(p,side,H):
    un,fn,hn=[x+'_'+side for x in ['upperarm','lowerarm','hand']]
    A=rest[un].translation.copy();T=H.translation
    l1=(rest[fn].translation-A).length;l2=(rest[hn].translation-rest[fn].translation).length
    axis=(T-A).normalized();dist=(T-A).length
    if dist>l1+l2-.003:A+=axis*(dist-(l1+l2-.003));dist=(T-A).length
    pole=Vector((-.55 if side=='l' else .55,-.40,-.4));pole-=axis*pole.dot(axis);pole.normalize()
    along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p['clavicle_'+side].translation+=A-rest[un].translation
    for n,start,end,oldend in [(un,A,E,rest[fn].translation),(fn,E,T,rest[hn].translation)]:
        direction=(end-start).normalized();old=(oldend-rest[n].translation).normalized()
        q=old.rotation_difference(direction)@rest[n].to_quaternion()
        p[n]=Matrix.LocRotScale(start,q,Vector((1,1,1)))
    neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion()
    q=H.to_quaternion()@neutral.inverted();v=(T-E).normalized()
    twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
    # Distribute wrist rotation along the existing twist chain.
    for prefix,parent in [('upperarm',un),('lowerarm',fn)]:
        for idx,weight in [('01',.75),('02',.35)]:
            n=f'{prefix}_twist_{idx}_{side}'
            if n not in rest:continue
            m=p[parent]@rest[parent].inverted()@rest[n]
            if prefix=='lowerarm':m=Matrix.LocRotScale(m.translation,Quaternion(v,twist*weight)@m.to_quaternion(),Vector((1,1,1)))
            p[n]=m
    p[hn]=H
    for n,m in (left_rel if side=='l' else right_rel).items():p[n]=H@m
def apply(swordframe):
    p={n:m.copy() for n,m in rest.items()}
    for side in ['l','r']:arm(p,side,swordframe@grips[side])
    p['WPN_root']=swordframe
    for n in ['Blade_Base','Blade_Tip']:p[n]=swordframe@rest['WPN_root'].inverted()@rest[n]
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
clips=[('Idle','Sword_Idle',80/24),('Walk','Sword_Walk',22/24),('Slash1','Sword_Slash1',20/24),('Slash2','Sword_Slash2',20/24),('Equip',None,.55),('Sprint','Sword_Walk',22/24)]
s.render.fps=120;s.render.fps_base=1
for name,donor,duration in clips:
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True;r.animation_data_create();r.animation_data.action=action
    s.frame_start=0;s.frame_end=round(duration*120);previous={}
    for f in range(s.frame_end+1):
        s.frame_set(f);t=f/120
        if donor:
            m=sample(donor,t);delta=C.to_3x3()@(m.translation-idle.translation)*(.48 if name.startswith('Slash') else .70)
            q=C.to_quaternion()@(m.to_quaternion()@idle.to_quaternion().inverted())@C.to_quaternion().inverted()
            q=Quaternion().slerp(q,.72 if name.startswith('Slash') else 1.)
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
        apply(sf)
        for b in r.pose.bones:
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_quaternion=q;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    export('A_RuneSword_'+name+'.fbx',[r],True)
    report[name]={'duration':duration,'fps':120,'frames':s.frame_end+1,'loop':name in ['Idle','Walk','Sprint'],'reference':donor,'contact_window':[.23,.46] if name.startswith('Slash') else None}
    print('AUTHORED',name,flush=True)
r.animation_data.action=bpy.data.actions['A_RuneSword_Idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=400;s.frame_set(0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'clips':report,'grips_cm':{'right_below_guard':9,'left_below_guard':21.5},'source':str(source),'donor':'BigAndCrispy/Unity-First-Person-Melee CC0 (one-handed motion adapted to two hands)','source_triangles':count,'game_triangles':len(canonical.polygons)},indent=2))
