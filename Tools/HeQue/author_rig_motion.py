"""Refine the supplied HeQue mesh, local iron chain and anatomical rig; bake basic motion."""
import bpy,bmesh,json,math,struct
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RigV01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/HeQue_source.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rig.name='HeQueRig';body.name='HeQueBody'
original_triangles=sum(len(p.vertices)-2 for p in body.data.polygons)
data=np.load(ROOT/'Records/surface_map.npz');points=data['points'];colors=data['colors']
# The generated chain is welded through its links and into the limb. Remove
# only its narrow hanging track; keep the original cuff and upper attachment.
chain_track=np.array([[-.543,.043,.585],[-.547,.043,.52],[-.546,.051,.47],[-.555,.049,.42],[-.560,.058,.37],[-.562,.059,.32],[-.569,.059,.27],[-.570,.070,.22],[-.585,.073,.17],[-.593,.082,.12],[-.612,.086,.065],[-.627,.088,.035]])
distance=np.full(len(points),100.)
for a,b in zip(chain_track[:-1],chain_track[1:]):
    t=np.clip((points-a)@(b-a)/np.dot(b-a,b-a),0,1);distance=np.minimum(distance,np.linalg.norm(points-(a+t[:,None]*(b-a)),axis=1))
remove=(distance<.032)&(points[:,2]<.592)&(points[:,2]>.035)
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
faces=[f for f in bm.faces if any(remove[v.index] for v in f.verts)]
removed_faces=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(body.data);bm.free();body.data.update()
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');eb=rig.data.edit_bones
def bone(name,head,tail,parent=None):
    b=eb.new(name);b.head=head;b.tail=tail;b.use_connect=False
    if parent:b.parent=eb[parent]
    b.align_roll(Vector((0,-1,0)));return b
bone('HQ_Root',(0,0,0),(0,0,.12))
bone('HQ_Arch',(0,-.083,1.53),(0,-.083,1.69),'HQ_Root')
bone('HQ_CoreSwing',(-.01,-.083,1.47),(-.01,-.083,1.20),'HQ_Arch')
eb['Bone_000'].parent=eb['HQ_CoreSwing']
for n in ('Bone_010','Bone_017'):eb[n].parent=eb['HQ_Arch']
sides={'R':dict(upper='Bone_008',lower='Bone_007',foot='Bone_006',toe='Bone_005',tip='Bone_004',arch=['Bone_010','Bone_009'],x=-.335),
       'L':dict(upper='Bone_015',lower='Bone_014',foot='Bone_013',toe='Bone_012',tip='Bone_011',arch=['Bone_017','Bone_016'],x=.345)}
for side,s in sides.items():
    x=s['x'];hip=eb[s['upper']].head.copy();knee=Vector((x,-.14,.79));ankle=Vector((x,-.015,.14))
    eb[s['upper']].tail=knee;eb[s['lower']].head=knee;eb[s['lower']].tail=ankle
    eb[s['foot']].head=ankle;eb[s['foot']].tail=(x,-.18,.085)
    eb[s['toe']].head=(x,-.18,.085);eb[s['toe']].tail=(x,-.30,.055)
    eb[s['tip']].head=(x,-.30,.055);eb[s['tip']].tail=(x,-.35,.04)
    z=.63 if side=='R' else .43
    bone('HQ_Cuff_'+side,(x,0,z),(x,0,z+.07),s['lower'])
    bone('HQ_Flank_'+side,(x,-.06,1.04),(x,-.06,1.20),s['upper'])
    s['hip']=list(hip);s['knee']=list(knee);s['ankle']=list(ankle)
anchor=Vector((-.548,.05,.592));step=Vector((-.006,.002,-.0355));links=15
for i in range(links):
    top=anchor+step*i
    bone(f'HQ_Chain_{i:02d}',top,top+step,'HQ_Cuff_R' if i==0 else f'HQ_Chain_{i-1:02d}')
bpy.ops.object.mode_set(mode='OBJECT')
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
# Reweight the actual anatomy, preserving source mesh/UV/corner normals. A
# shared coordinate key prevents skin seams from receiving different weights.
p=np.array([v.co[:] for v in body.data.vertices]);groups={b.name:None for b in rig.data.bones}
body.vertex_groups.clear();groups={n:body.vertex_groups.new(name=n) for n in groups}
def smooth(x):x=max(0.,min(1.,float(x)));return x*x*(3-2*x)
def weighted_axis(z,centres,names):
    if z<=centres[0]:return {names[0]:1.}
    if z>=centres[-1]:return {names[-1]:1.}
    k=int(np.searchsorted(centres,z)-1);t=smooth((z-centres[k])/(centres[k+1]-centres[k]));return {names[k]:1-t,names[k+1]:t}
def mix(a,b,t):
    r={n:w*(1-t) for n,w in a.items()}
    for n,w in b.items():r[n]=r.get(n,0.)+w*t
    return r
seams={};cuff_counts={};core_count=0
for i,v in enumerate(p):
    x,y,z=v;key=tuple(np.round(v,6))
    if key in seams:w=seams[key]
    else:
        side='R' if x<0 else 'L';s=sides[side]
        w=weighted_axis(z,[.13,.46,1.02,1.40,1.56],[s['foot'],s['lower'],s['upper'],s['arch'][1],s['arch'][0]])
        if z<.13 and y<-.13:w=mix(w,{s['toe']:1.},smooth((-.13-y)/.16)*.6)
        # Root of the arch remains continuous across the centre.
        arch=smooth((z-1.42)/.16)*(1-smooth((abs(x)-.06)/.25))
        w=mix(w,{'HQ_Arch':1.},arch)
        # Only central suspended tissue belongs to the core chain.
        if abs(x+.01)<.105 and .93<z<1.49:
            core_count+=1;attach=smooth((z-1.37)/.12)
            w={'HQ_CoreSwing':1-attach,'HQ_Arch':attach}
        else:
            # Cuff positions are oblique in the supplied model; whole bands
            # are rigid, with a smooth tissue transition on either side.
            plane=(.63-.13*(x+.335)+.018*y) if side=='R' else (.43+.11*(x-.345)+.018*y)
            d=abs(z-plane);blend=1-smooth((d-.025)/.032)
            if blend>0:
                w=mix(w,{'HQ_Cuff_'+side:1.},blend)
                if blend>.999:cuff_counts[side]=cuff_counts.get(side,0)+1
        w=dict(sorted(((n,a) for n,a in w.items() if a>1e-5),key=lambda it:-it[1])[:4]);total=sum(w.values());w={n:a/total for n,a in w.items()};seams[key]=w
    for n,a in w.items():groups[n].add([i],a,'REPLACE')
for mod in body.modifiers:
    if mod.type=='ARMATURE':mod.use_deform_preserve_volume=False
# Individually closed, interleaved oval iron links. One rigid transform per
# entire ring; no interpolation across adjacent links.
metal=bpy.data.materials.new('HeQueChainIron');metal.diffuse_color=(.09,.065,.04,1);metal.use_nodes=True
pbs=next(n for n in metal.node_tree.nodes if n.type=='BSDF_PRINCIPLED');pbs.inputs['Base Color'].default_value=(.09,.065,.04,1);pbs.inputs['Metallic'].default_value=.8;pbs.inputs['Roughness'].default_value=.72
cv=[];cf=[];link_indices=[]
axis=step.normalized();axis1=Vector((0,1,0));axis2=axis.cross(axis1).normalized()
for i in range(links):
    centre=anchor+step*(i+.5);wide=axis1 if i%2==0 else axis2;normal=axis.cross(wide).normalized();start=len(cv)
    for j in range(40):
        angle=math.tau*j/40
        c=centre+axis*(.028*math.cos(angle))+wide*(.014*math.sin(angle))
        radial=(axis*(math.cos(angle)/.028)+wide*(math.sin(angle)/.014)).normalized()
        for k in range(8):cv.append(tuple(c+.004*(radial*math.cos(math.tau*k/8)+normal*math.sin(math.tau*k/8))))
    for j in range(40):
        for k in range(8):cf.append((start+j*8+k,start+((j+1)%40)*8+k,start+((j+1)%40)*8+(k+1)%8,start+j*8+(k+1)%8))
    link_indices.append(list(range(start,len(cv))))
cm=bpy.data.meshes.new('HeQueIndividualLinks');cm.from_pydata(cv,[],cf);cm.update()
chain=bpy.data.objects.new('HeQueRigidChain',cm);bpy.context.collection.objects.link(chain);cm.materials.append(metal)
for f in cm.polygons:f.use_smooth=True
for i,idx in enumerate(link_indices):chain.vertex_groups.new(name=f'HQ_Chain_{i:02d}').add(idx,1.,'REPLACE')
mod=chain.modifiers.new('HeQueRig','ARMATURE');mod.object=rig;chain.parent=rig
# A simple valid UV chart for the independent metal surface.
uv=cm.uv_layers.new(name='UVMap')
for poly in cm.polygons:
    for li in poly.loop_indices:
        vi=cm.loops[li].vertex_index%320;uv.data[li].uv=((vi//8)/40,(vi%8)/8)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones};tails={b.name:b.tail_local.copy() for b in rig.data.bones}
desired={};bone_order=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive))
def clear():
    desired.clear()
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
def at(name,head,tail):
    q=(tails[name]-heads[name]).rotation_difference(tail-head)
    desired[name]=Matrix.Translation(head)@q.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def transform(name,mat):desired[name]=mat@rest[name]
def solve_two(hip,ankle,s):
    l1=(heads[s['lower']]-heads[s['upper']]).length;l2=(heads[s['foot']]-heads[s['lower']]).length
    v=ankle-hip;d=min(v.length,l1+l2-.001);direction=v.normalized()
    pole=Vector((0,-1,0));pole=(pole-direction*direction.dot(pole)).normalized()
    a=(l1*l1-l2*l2+d*d)/(2*d);h=math.sqrt(max(0.,l1*l1-a*a));return hip+direction*a+pole*h
def frame_pose(role,t,duration):
    clear();u=t/duration;phase=math.tau*u;bob=0.;shift=Vector();roll=0.;lean=0.;collapse=0.;pulse=0.
    if role=='Idle':bob=.005*math.sin(phase);roll=.4*math.sin(phase);pulse=math.sin(phase)
    elif role in ('Move','TurnLeft','TurnRight'):bob=-.025+.009*math.cos(phase*2);shift.x=.015*math.sin(phase);roll=1.8*math.sin(phase)
    elif role.startswith('Hit'):
        pulse=(smooth(t/.12) if t<.12 else (1-smooth((t-.12)/(duration-.12))))
        lean=(1 if role=='HitFront' else -1 if role=='HitBack' else 0)*8*pulse
        roll=(1 if role=='HitRight' else -1 if role=='HitLeft' else 0)*7*pulse;bob=-.018*pulse
    elif role=='Stun':roll=3.5*math.sin(phase);lean=2.8*math.sin(phase+.8);bob=-.022+.008*math.cos(2*phase);pulse=math.sin(phase-.5)
    elif role=='Air':collapse=12*smooth(t/.25);roll=3*math.sin(phase);bob=-.03
    elif role in ('Land','GetUp'):
        f=smooth(u);collapse=12+53*f if role=='Land' else 65*(1-f);bob=-.04 if role=='Land' else -.04*(1-f)
    elif role=='Death':collapse=82*smooth(u);bob=-.04*smooth(u);roll=4*math.sin(math.pi*u)
    top=heads['HQ_Arch'];delta=Vector((shift.x,shift.y,bob))
    global_mat=Matrix.Rotation(math.radians(collapse),4,'X')
    if collapse:
        a=math.radians(collapse);floor=float(np.min(p[:,1]*math.sin(a)+p[:,2]*math.cos(a)))
        global_mat.translation=Vector((0,0,max(0.,-floor)+.006))
    arch_mat=Matrix.Translation(top+delta)@Matrix.Rotation(math.radians(roll),4,'Y')@Matrix.Rotation(math.radians(lean),4,'X')@Matrix.Translation(-top)
    transform('HQ_Arch',global_mat@arch_mat)
    for side,s in sides.items():
        for name in s['arch']:transform(name,global_mat@arch_mat)
        hip=arch_mat@heads[s['upper']];foot=heads[s['foot']].copy();offset=0.
        if role in ('Move','TurnLeft','TurnRight'):
            q=(u+(0. if side=='R' else .5))%1.;stance=.62
            if q<stance:y=-.15+.30*q/stance;lift=0.
            else:
                a=(q-stance)/(1-stance);y=.15-.30*smooth(a);lift=.065*math.sin(math.pi*a)**1.4
            if role=='Move':foot.y+=y
            else:foot.y+=y*(1 if (role=='TurnLeft')==(side=='R') else -1)*.65
            foot.z+=lift
        elif role=='Air':foot.y+=.06*smooth(t/.25);foot.z+=.09*smooth(t/.25)
        knee=solve_two(hip,foot,s)
        at(s['upper'],global_mat@hip,global_mat@knee);at(s['lower'],global_mat@knee,global_mat@foot)
        foot_delta=Matrix.Translation(foot-heads[s['foot']]);transform(s['foot'],global_mat@foot_delta)
        for n in (s['toe'],s['tip']):transform(n,global_mat@foot_delta)
        cuff='HQ_Cuff_'+side
        # Follow the lower anatomical segment rigidly, never squash the metal.
        lower_delta=desired[s['lower']]@rest[s['lower']].inverted()
        transform(cuff,lower_delta)
        upper_delta=desired[s['upper']]@rest[s['upper']].inverted();transform('HQ_Flank_'+side,upper_delta)
    # Continuous core pendulum, lagging behind the arch instead of dragging it.
    core_angle=2.8*math.sin(phase-.45) if role in ('Idle','Move','Stun','TurnLeft','TurnRight') else 5*pulse
    pivot=heads['HQ_CoreSwing'];core=global_mat@arch_mat@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(core_angle),4,'X')@Matrix.Translation(-pivot)
    transform('HQ_CoreSwing',core)
    for n in ('Bone_000','Bone_001','Bone_003','Bone_002'):transform(n,core)
    cuff_delta=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted()
    current=cuff_delta@anchor
    # Bake a short articulated chain. Every link is rigid; floor-limited link
    # centres prevent the hanging end from entering the floor in authored poses.
    for i in range(links):
        sway=(math.sin(phase-i*.16)*.08 if role in ('Move','TurnLeft','TurnRight') else math.sin(phase-i*.12)*.025 if role in ('Idle','Stun') else pulse*.08)
        direction=Vector((-.006+sway*.10,.002+sway*.25,-.0355)).normalized()
        if current.z<.045:direction=Vector((-.8,.35,max(0.,.025-current.z)*10)).normalized()
        target=current+direction*step.length
        if target.z<.018:
            direction.z=max(-.25,direction.z);direction.normalize();target=current+direction*step.length
        at(f'HQ_Chain_{i:02d}',current,target);current=target
    # Resolve local matrices from explicit desired component transforms. This
    # avoids stale evaluated parent matrices accumulating along the iron chain.
    for b in bone_order:
        base=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=base
        rig.pose.bones[b.name].matrix_basis=base.inverted()@desired[b.name]
    bpy.context.view_layer.update()
clips=[('Idle',4.,True),('Move',2.,True),('TurnLeft',2.,True),('TurnRight',2.,True),
       ('HitFront',.75,False),('HitRight',.75,False),('HitBack',.75,False),('HitLeft',.75,False),
       ('Stun',2.6,True),('Air',1.,False),('Land',.65,False),('GetUp',1.8,False),('Death',2.2,False)]
scene=bpy.context.scene;scene.render.fps=60;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.animation_data_create();fbx=dict(use_selection=True,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);body.select_set(True);chain.select_set(True);bpy.context.view_layer.objects.active=rig
clear();bpy.context.view_layer.update()
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SK_HeQue.fbx'),object_types={'MESH','ARMATURE'},bake_anim=False,**fbx)
report={'source_triangles':original_triangles,'removed_chain_faces':removed_faces,'body_triangles':sum(len(f.vertices)-2 for f in body.data.polygons),
        'chain_triangles':sum(len(f.vertices)-2 for f in cm.polygons),'rig_bones':len(rig.data.bones),'rigid_links':links,'cuff_core_counts':cuff_counts,
        'sides':sides,'game_height_cm':450,'authored_height_cm':170,'stride_cm':.30/.62*450/1.7,'clips':[],'runtime_tested':False}
for role,duration,loop in clips:
    action=bpy.data.actions.new('A_HeQue_'+role);action.use_fake_user=True;rig.animation_data.action=action
    count=round(duration*60);scene.frame_start=1;scene.frame_end=count+1
    for f in range(count+1):
        scene.frame_set(f+1);frame_pose(role,f/60,duration)
        for b in rig.pose.bones:
            b.keyframe_insert('location',frame=f+1,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name);b.keyframe_insert('scale',frame=f+1,group=b.name)
    body.select_set(False);chain.select_set(False)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/('A_HeQue_'+role+'.fbx')),object_types={'ARMATURE'},bake_anim=True,**fbx)
    report['clips'].append(dict(role=role,name='A_HeQue_'+role,duration=duration,loop=loop))
rig.animation_data.action=None;clear();bpy.context.view_layer.update()
body.select_set(True);chain.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_refined_rig_motion_v01.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Export/HeQue_refined_rig_motion_v01.glb'),export_format='GLB',use_selection=True,export_animations=False)
# Extract original embedded PBR bytes directly, preserving input UV and channels.
raw=(ROOT/'Inputs/HeQue_user_rig.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+length]);offset=20+length+8
mat=gltf['materials'][0];roles={'BaseColor':mat['pbrMetallicRoughness']['baseColorTexture']['index'],'Normal':mat['normalTexture']['index'],'MetallicRoughness':mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index']}
for role,tex in roles.items():
    img=gltf['images'][gltf['textures'][tex]['source']];view=gltf['bufferViews'][img['bufferView']];start=offset+view.get('byteOffset',0)
    (ROOT/'Textures'/('T_HeQue_'+role+'.png')).write_bytes(raw[start:start+view['byteLength']])
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
np.savez_compressed(ROOT/'Records/chain_hardware.npz',points=np.array(cv),link_ids=np.repeat(np.arange(links),320))
print('HEQUE_AUTHORED '+json.dumps({k:v for k,v in report.items() if k not in ('sides','clips')}),flush=True)
