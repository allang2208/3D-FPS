"""Three independently pressurised crown sectors and an original bone projectile."""
import ast,bpy,json,math,wave,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
UPPER='--upper-fan' in sys.argv
VERSION='V02' if UPPER else 'V01'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/RootCrown_LocomotionV01.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};head={n:m.translation.copy() for n,m in rest.items()}
chains=[['Bone_004','Bone_003','Bone_002'],['Bone_008','Bone_007','Bone_006','Bone_005'],['Bone_012','Bone_011','Bone_010','Bone_009']]
centers=[Vector((.085,.365,head['Bone_002'].z)),Vector((-.54,-.04,head['Bone_005'].z)),Vector((.365,-.39,head['Bone_009'].z))]
tree=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/author_locomotion.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve'],type_ignores=[]),'tripod_ik','exec'))
scene=bpy.context.scene;scene.render.fps=60;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.animation_data_create()
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
shots=[1.4,1.7,2.0]
sectors=(4,6,7) if UPPER else (3,6,9)
def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def pressure(t,shot):
    return ease((t-(shot-.75))/.65)*(1.-ease((t-shot)/.08))
def recoil(t,shot):
    if t<shot:return 0.
    return ease((t-shot)/.06)*(1.-ease((t-shot-.06)/.22))
def turn(n,axis,degrees):
    return Quaternion(rest[n].to_quaternion().inverted()@Vector(axis),math.radians(degrees)).to_matrix().to_4x4()
def pose(t):
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    ready=ease(t/.75)*(1.-ease((t-2.1)/.7));kick=sum(recoil(t,s) for s in shots)
    body=Matrix.Translation(Vector((0,.013*ready+(.024 if UPPER else .012)*kick,-.03-.012*ready)))
    desired={'Root':rest['Root'].copy(),'Bone_000':body@rest['Bone_000'],'Bone_001':body@rest['Bone_001']}
    for chain,center in zip(chains,centers):solve(chain,body,center,Quaternion(),desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:desired[n]=desired[parent]@rest[parent].inverted()@rest[n] if parent else rest[n].copy()
        if n in ('Stem_Lower','Stem_Upper','Crown_Base'):
            share={'Stem_Lower':.25,'Stem_Upper':.45,'Crown_Base':.3}[n]
            desired[n]=desired[n]@turn(n,(1,0,0),share*((-11. if UPPER else -7.)*ready-(5. if UPPER else 2.2)*kick))
            if UPPER:
                # Broad side-to-side sway, followed by an alternating damped
                # shake. The support feet still use the original IK targets.
                shake=sum(((-1.)**j)*math.sin(max(0.,t-s)*math.tau*3.3)*math.exp(-max(0.,t-s)*5.5) for j,s in enumerate(shots) if t>=s)
                settle=1.-ease((t-2.2)/.6)
                desired[n]=desired[n]@turn(n,(0,1,0),share*(6.*math.sin(t*math.tau*.85)*ready+10.*shake*settle))
                desired[n]=desired[n]@turn(n,(0,0,1),share*4.*math.sin(t*math.tau*.65)*ready)
        elif n.startswith('Crown_') and n!='Crown_Base':
            _,number,part=n.split('_');i=int(number);theta=math.radians(-25+25*(i-1))
            lag={'Base':0.,'Flex':.012,'Rim':.025}[part] if UPPER else 0.
            load=sum(math.exp(-.5*((i-center)/1.3)**2)*pressure(t-lag,s) for center,s in zip(sectors,shots))
            snap=sum(math.exp(-.5*((i-center)/1.3)**2)*recoil(t-lag,s) for center,s in zip(sectors,shots))
            amount=({'Base':4.,'Flex':10.,'Rim':17.} if UPPER else {'Base':1.5,'Flex':4.5,'Rim':6.5})[part]
            ripple=0.
            if UPPER:
                for center,s in zip(sectors,shots):
                    age=t-s-lag
                    if age>0.:ripple+=math.exp(-.5*((i-center)/1.7)**2)*math.sin(age*math.tau*4.)*math.exp(-age*6.)
                ripple*=1.-ease((t-2.2)/.6)
            desired[n]=desired[n]@turn(n,(-math.sin(theta),0,math.cos(theta)),-amount*(.2*ready+load)+amount*(.75 if UPPER else .35)*snap+amount*.3*ripple)
        pb.matrix_basis=rest[n].inverted()@rest[parent]@desired[parent].inverted()@desired[n] if parent else rest[n].inverted()@desired[n]
    bpy.context.view_layer.update()

exports=ROOT/('Exports/Needles'+VERSION);exports.mkdir(exist_ok=True)
action=bpy.data.actions.new('A_RootCrown_NeedleFan_'+VERSION);action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=1;scene.frame_end=169
for f in range(169):
    scene.frame_set(f+1);pose(f/60.)
    for pb in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=f+1,group=pb.name)
for o in scene.objects:o.select_set(False)
rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(exports/('A_RootCrown_NeedleFan_'+VERSION+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
if UPPER:
    # Select three real front-surface points near the upper blade ends. Store
    # mesh-space reference points; UE derives bone-local offsets from its own
    # reference skeleton, so FBX bone-axis and unit conversion stay explicit.
    vertices=np.array([v.co[:] for v in mesh.data.vertices])
    hub=np.array([.18,.015,.67]);radius=np.linalg.norm(vertices[:,[0,2]]-hub[[0,2]],axis=1)
    angles=np.arctan2(vertices[:,2]-hub[2],vertices[:,0]-hub[0])
    outlets=[]
    for sector in sectors:
        theta=math.radians(-25+25*(sector-1));bone=f'Crown_{sector:02d}_Rim'
        ids=np.where((np.abs(angles-theta)<math.radians(5.))&(vertices[:,2]>1.))[0]
        outer=float(np.percentile(radius[ids],98))
        ids=ids[(radius[ids]>.84*outer)&(radius[ids]<.96*outer)]
        front=ids[vertices[ids,1]<=np.percentile(vertices[ids,1],25)]
        target=np.median(vertices[front],axis=0)
        selected=int(front[np.argmin(np.sum((vertices[front]-target)**2,axis=1))])
        p=vertices[selected];outlets.append(dict(bone=bone,vertex=selected,mesh_cm=[float(p[0]*100),float(-p[1]*100),float(p[2]*100)]))
    manifest=dict(clip=action.name,seconds=2.8,shots=shots,sectors=list(sectors),outlets=outlets,blade_rotation_degrees={'Base':4.,'Flex':10.,'Rim':17.},body_mesh_and_weights='preserved',rendered=False,tested=False)
    (exports/'outlets.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    lines=['// Generated by Tools/RootCrown/author_needles.py --upper-fan.','#pragma once','namespace RootCrownNeedleOutlets','{','    struct FOutlet {const TCHAR* Bone; FVector MeshPoint;};','    inline const FOutlet Points[] = {']
    for outlet in outlets:
        xyz=','.join(f'{v:.7f}' for v in outlet['mesh_cm'])
        lines.append('        {TEXT("'+outlet['bone']+'"),FVector('+xyz+')},')
    lines+=['    };','}']
    Path('D:/FPS3D/FPSGAME/Source/FPSGAME/Monsters/RootCrownNeedleOutlets.h').write_text('\n'.join(lines)+'\n',encoding='utf8')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_NeedleFanV02.blend'))
    (ROOT/'Reports/needle_v2_authoring.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('ROOT_CROWN_UPPER_NEEDLES_AUTHORED',flush=True)
    sys.exit(0)

vertices=[];faces=[];rings=[(-.18,.004),(-.145,.014),(-.105,.010),(-.04,.009),(.04,.0065),(.12,.0035),(.18,.00025)]
sides=10
for k,(x,r) in enumerate(rings):
    for j in range(sides):
        a=math.tau*j/sides+.10*k;vertices.append((x,r*math.cos(a),r*.8*math.sin(a)))
for k in range(len(rings)-1):
    for j in range(sides):faces.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
faces.append(tuple(reversed(range(sides))));faces.append(tuple((len(rings)-1)*sides+j for j in range(sides)))
data=bpy.data.meshes.new('RootCrownBoneNeedle');data.from_pydata(vertices,[],faces);data.update()
needle=bpy.data.objects.new('SM_RootCrownNeedle',data);scene.collection.objects.link(needle)
colors=data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for polygon in data.polygons:
    polygon.use_smooth=True
    for loop in polygon.loop_indices:
        v=vertices[data.loops[loop].vertex_index];factor=.58+.42*max(0.,min(1.,(v[0]+.18)/.10))
        colors.data[loop].color=(.56*factor,.48*factor,.34*factor,1.)
for o in scene.objects:o.select_set(False)
needle.select_set(True);bpy.context.view_layer.objects.active=needle
bpy.ops.export_scene.fbx(filepath=str(exports/'SM_RootCrownNeedle.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',bake_anim=False)
needle.location=(3,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_NeedleFanV01.blend'))

audio=ROOT/'Audio/NeedlesV01';audio.mkdir(parents=True,exist_ok=True)
rate=48000;rng=np.random.default_rng(271014)
def noise(n,width):return np.convolve(rng.normal(size=n),np.ones(width)/width,mode='same')
def save(name,y):
    y=y/max(1e-6,float(np.max(np.abs(y))))*.62
    with wave.open(str(audio/name),'wb') as out:
        out.setparams((1,2,rate,len(y),'NONE','not compressed'));out.writeframes((y*32767).astype('<i2').tobytes())
t=np.arange(round(2.8*rate))/rate
load=np.clip(t/.9,0,1)*np.clip((2.15-t)/.22,0,1)
y=(noise(len(t),65)*.28+np.sin(2*np.pi*(58*t+4*t*t))*.035)*load
for s in shots:
    age=np.maximum(0,t-s);env=(t>=s)*np.exp(-age*32)*np.minimum(1,age/.002)
    y+=env*(noise(len(t),3)*.65+noise(len(t),35)*.55+np.sin(2*np.pi*170*age)*.15)
save('RootCrown_NeedleGesture.wav',y)
t=np.arange(round(.16*rate))/rate
save('RootCrown_NeedleImpact.wav',(noise(len(t),4)*.55+np.sin(2*np.pi*310*t)*.22)*np.exp(-t*40)*np.minimum(1,t/.0015))
(ROOT/'Reports/needle_authoring.json').write_text(json.dumps(dict(clip='A_RootCrown_NeedleFan_V01',seconds=2.8,shots=shots,sectors=['left','middle','right'],pins_per_wave=5,projectile_forward='+X',projectile_length_cm=36,body_mesh_and_weights='preserved',audio_source='original deterministic synthesis',rendered=False,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_NEEDLES_AUTHORED',flush=True)
