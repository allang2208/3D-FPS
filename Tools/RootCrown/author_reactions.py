"""Directional recoil, stun sway, airborne/landing/get-up and death lead-in."""
import ast,bpy,json,math,wave
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
OUT=ROOT/'Exports/ReactionsV01';OUT.mkdir(exist_ok=True)
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

def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def curve(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*ease((t-a)/(b-a))
    return keys[-1][1]
def rotate(n,axis,degrees):
    return Quaternion(rest[n].to_quaternion().inverted()@Vector(axis),math.radians(degrees)).to_matrix().to_4x4()
def envelope(t):return curve(t,[(0,0),(.07,.65),(.18,1),(.33,-.18),(.48,.06),(.65,0)])
def pose(role,t):
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    pitch=roll=down=air=relax=fan=0.;settle=-.03
    if role.startswith('Hit'):
        hit=envelope(t);direction={'HitFront':(-1,0),'HitRight':(0,1),'HitBack':(1,0),'HitLeft':(0,-1)}[role]
        pitch=18*hit*direction[0];roll=16*hit*direction[1];settle-=.014*abs(hit);fan=hit*.5
    elif role=='Stun':
        a=t*math.tau/2.4;pitch=8+5*math.sin(a);roll=8*math.sin(a+.5);settle-=.025+.008*math.sin(a*2);fan=.35+.2*math.sin(a-.3)
    elif role=='Air':
        air=ease(t/.25);a=max(0,t-.25)*math.tau/.8
        pitch=-22*air+2*math.sin(a)*air;roll=3*math.sin(a)*air;settle+=.035*air;fan=-.8*air
    elif role=='Land':
        air=1.-ease(t/.23);down=ease(t/.4);impact=math.exp(-((t-.16)/.085)**2)
        pitch=-22*air+24*down+4*impact;roll=3*down;settle+=.035*air-.105*down-.02*impact;fan=.7*down
    elif role=='GetUp':
        down=1.-curve(t,[(0,0),(.18,.02),(.55,.23),(.90,.78),(1.3,1)])
        pitch=24*down;roll=3*down;settle-=.105*down;fan=.7*down
    elif role=='Death':
        pitch=curve(t,[(0,0),(.18,10),(.42,30),(.65,55),(1.05,82),(1.6,87)])
        roll=curve(t,[(0,0),(.4,-8),(1.,-16),(1.6,-14)])
        relax=ease((t-.18)/.9);settle-=.17*ease(t/1.0);fan=1.5*ease(t/.8)
    pivot=head['Bone_000']
    body=Matrix.Translation(Vector((0,0,settle)))@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(pitch*.12),4,'X')@Matrix.Rotation(math.radians(roll*.12),4,'Y')@Matrix.Translation(-pivot)
    desired={'Root':rest['Root'].copy(),'Bone_000':body@rest['Bone_000'],'Bone_001':body@rest['Bone_001']}
    for chain,center in zip(chains,centers):
        anchor=center.copy();anchor.x*=1.-.32*air+.12*down;anchor.y*=1.-.32*air+.12*down;anchor.z+=.23*air
        if role=='Death':anchor=anchor.lerp(body@center+Vector((0,0,.045)),relax)
        solve(chain,body,anchor,Quaternion(),desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:desired[n]=desired[parent]@rest[parent].inverted()@rest[n] if parent else rest[n].copy()
        if n in ('Stem_Lower','Stem_Upper','Crown_Base'):
            share={'Stem_Lower':.24,'Stem_Upper':.44,'Crown_Base':.32}[n]
            desired[n]=desired[n]@rotate(n,(1,0,0),pitch*.88*share)@rotate(n,(0,1,0),roll*.88*share)
        elif n.startswith('Crown_') and n!='Crown_Base':
            _,number,part=n.split('_');i=int(number);theta=math.radians(-25+25*(i-1))
            lag={'Base':0.,'Flex':.018,'Rim':.04}[part]
            amount={'Base':1.7,'Flex':3.5,'Rim':6.}[part]
            bend=fan
            if role.startswith('Hit'):bend=.5*envelope(max(0,t-lag))
            if role=='Stun':bend+=.15*math.sin(t*math.tau/2.4-i*.38-lag)
            desired[n]=desired[n]@rotate(n,(-math.sin(theta),0,math.cos(theta)),amount*bend)
        pb.matrix_basis=rest[n].inverted()@rest[parent]@desired[parent].inverted()@desired[n] if parent else rest[n].inverted()@desired[n]
    bpy.context.view_layer.update()

clips=[]
for role,duration in [('HitFront',.65),('HitRight',.65),('HitBack',.65),('HitLeft',.65),('Stun',2.4),('Air',1.05),('Land',.65),('GetUp',1.3),('Death',1.6)]:
    name='A_RootCrown_'+role+'_V01';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    frames=round(duration*60);scene.frame_start=1;scene.frame_end=frames+1
    for f in range(frames+1):
        scene.frame_set(f+1);pose(role,f/60.)
        for pb in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=f+1,group=pb.name)
    for o in scene.objects:o.select_set(False)
    rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips.append(dict(role=role,name=name,seconds=duration,loop=role=='Stun'))
scene.frame_set(1);pose('Death',0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_ReactionsV01.blend'))
audio=ROOT/'Audio/ReactionsV01';audio.mkdir(parents=True,exist_ok=True)
rate=48000;rng=np.random.default_rng(141028)
for role,duration,freq,decay in [('Hit',.4,95,12),('Land',.65,55,8),('Death',1.8,39,2.2)]:
    t=np.arange(round(duration*rate))/rate;noise=rng.normal(size=len(t));smooth=np.convolve(noise,np.ones(45)/45,mode='same')
    y=(smooth*.6+noise*.04+np.sin(2*np.pi*(freq*t-3*t*t))*.10)*np.exp(-t*decay)*np.minimum(1,t/.008)
    y=y/max(1e-6,float(np.max(np.abs(y))))*.52
    with wave.open(str(audio/('RootCrown_'+role+'.wav')),'wb') as out:
        out.setparams((1,2,rate,len(y),'NONE','not compressed'));out.writeframes((y*32767).astype('<i2').tobytes())
(ROOT/'Reports/reactions_authoring.json').write_text(json.dumps(dict(clips=clips,air_loop=[.25,1.05],death_soft_handoff=.65,body_mesh_and_weights='preserved',rendered=False,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_REACTIONS_AUTHORED',flush=True)
