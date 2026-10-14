"""Root enclosure: planted tripod animation, fleshy knot geometry and original audio."""
import ast,bpy,json,math,wave
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
exports=ROOT/'Exports/RootsV01';exports.mkdir(exist_ok=True)
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
shots=[2.,2.35,2.7]

def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def curve(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*ease((t-a)/(b-a))
    return keys[-1][1]
def rotate(n,axis,degrees):
    return Quaternion(rest[n].to_quaternion().inverted()@Vector(axis),math.radians(degrees)).to_matrix().to_4x4()
def pose(t):
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    plant=curve(t,[(0,0),(.15,0),(.65,1),(2.85,1),(3.35,.8),(4.2,0)])
    pressure=curve(t,[(0,0),(.6,.25),(1.7,1),(1.95,1),(2.08,.6),(2.8,.35),(4.2,0)])
    kick=sum(math.exp(-((t-s-.055)/.075)**2) for s in shots)
    body=Matrix.Translation(Vector((0,.02*pressure,-.03-.055*plant-.018*kick)))
    desired={'Root':rest['Root'].copy(),'Bone_000':body@rest['Bone_000'],'Bone_001':body@rest['Bone_001']}
    for i,(chain,center) in enumerate(zip(chains,centers)):
        # Spread and press each existing broad foot in sequence, then recover.
        anchor=center.copy();radial=Vector((center.x,center.y,0)).normalized()
        foot=ease((t-.12-i*.12)/.25)*(1.-ease((t-3.25)/.95))
        anchor+=radial*.018*foot;anchor.z-=.007*foot
        solve(chain,body,anchor,Quaternion(),desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:desired[n]=desired[parent]@rest[parent].inverted()@rest[n] if parent else rest[n].copy()
        if n in ('Stem_Lower','Stem_Upper','Crown_Base'):
            share={'Stem_Lower':.25,'Stem_Upper':.45,'Crown_Base':.30}[n]
            desired[n]=desired[n]@rotate(n,(1,0,0),share*(13.*plant-8.*pressure+7.*kick))
            desired[n]=desired[n]@rotate(n,(0,1,0),share*3.*math.sin(t*7.)*pressure)
        elif n.startswith('Crown_') and n!='Crown_Base':
            _,number,part=n.split('_');i=int(number);theta=math.radians(-25+25*(i-1))
            lag={'Base':0.,'Flex':.025,'Rim':.055}[part]
            pulse=sum(math.exp(-((t-s-lag-.055)/.10)**2)*math.cos(i*.6-j) for j,s in enumerate(shots))
            amount={'Base':2.5,'Flex':5.,'Rim':8.}[part]
            desired[n]=desired[n]@rotate(n,(-math.sin(theta),0,math.cos(theta)),-amount*pressure+amount*.65*pulse)
        pb.matrix_basis=rest[n].inverted()@rest[parent]@desired[parent].inverted()@desired[n] if parent else rest[n].inverted()@desired[n]
    bpy.context.view_layer.update()

action=bpy.data.actions.new('A_RootCrown_RootEnclosure_V01');action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=1;scene.frame_end=253
for f in range(253):
    scene.frame_set(f+1);pose(f/60.)
    for pb in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=f+1,group=pb.name)
for o in scene.objects:o.select_set(False)
rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
common=dict(use_selection=True,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE')
bpy.ops.export_scene.fbx(filepath=str(exports/'A_RootCrown_RootEnclosure_V01.fbx'),object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_tspace=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.,**common)

# Lobulated living organ, with raised blue-red vessels; no wooden root texture.
parts=[]
for j,(location,scale) in enumerate([((0,0,.22),(.22,.20,.22)),((-.13,.025,.15),(.12,.14,.15)),((.12,-.025,.14),(.13,.14,.14))]):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=1,location=location)
    part=bpy.context.object;part.scale=scale
    for v in part.data.vertices:
        p=v.co;variation=1.+.04*math.sin(p.x*17+j)*math.sin(p.z*13+p.y*8)
        v.co*=variation
    parts.append(part)
for j in range(7):
    theta=j*math.tau/7
    data=bpy.data.curves.new('KnotVessel','CURVE');data.dimensions='3D';data.resolution_u=2
    data.bevel_depth=.008 if j%2 else .012;data.bevel_resolution=2
    spline=data.splines.new('POLY');spline.points.add(14)
    for i,p in enumerate(spline.points):
        a=.12+(math.pi-.3)*i/14;r=.222
        angle=theta+.1*math.sin(a*4+j)
        p.co=(r*math.sin(a)*math.cos(angle),r*.92*math.sin(a)*math.sin(angle),.22+r*math.cos(a),1)
    obj=bpy.data.objects.new('BlueFleshVein',data);scene.collection.objects.link(obj)
    for o in scene.objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH');parts.append(bpy.context.object)
for j,part in enumerate(parts):
    colors=part.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for face in part.data.polygons:
        face.use_smooth=True
        for loop in face.loop_indices:colors.data[loop].color=(.72,.47,.43,1) if j<3 else (.24,.28,.35,1)
for o in scene.objects:o.select_set(False)
for p in parts:p.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();knot=bpy.context.object;knot.name='SM_RootCrownKnot'
scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.export_scene.fbx(filepath=str(exports/'SM_RootCrownKnot.fbx'),object_types={'MESH'},bake_anim=False,**common)
knot.location=(3,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_RootEnclosureV01.blend'))

audio=ROOT/'Audio/RootsV01';audio.mkdir(parents=True,exist_ok=True)
rate=48000;rng=np.random.default_rng(141026)
def noise(n,width):return np.convolve(rng.normal(size=n),np.ones(width)/width,mode='same')
def save_wave(name,y):
    y=y/max(1e-6,float(np.max(np.abs(y))))*.65
    with wave.open(str(audio/name),'wb') as out:
        out.setparams((1,2,rate,len(y),'NONE','not compressed'));out.writeframes((y*32767).astype('<i2').tobytes())
t=np.arange(round(4.2*rate))/rate;load=np.clip(t/.7,0,1)*np.clip((3.8-t)/.6,0,1)
y=(noise(len(t),90)*.3+np.sin(2*np.pi*(42*t+2*t*t))*.045)*load
for s in shots:
    a=np.maximum(0,t-s);env=(t>=s)*np.exp(-a*13)*np.minimum(1,a/.004)
    y+=env*(noise(len(t),8)*.7+noise(len(t),50)*.45+np.sin(2*np.pi*74*a)*.18)
save_wave('RootCrown_RootGesture.wav',y)
t=np.arange(round(.35*rate))/rate
save_wave('RootCrown_KnotBreak.wav',(noise(len(t),5)*.8+noise(len(t),50)*.4+np.sin(2*np.pi*95*t)*.15)*np.exp(-t*18)*np.minimum(1,t/.002))
(ROOT/'Reports/root_authoring.json').write_text(json.dumps(dict(clip=action.name,seconds=4.2,release_times=shots,knot_mesh=knot.name,body_mesh_and_weights='preserved',audio_source='original synthesis',rendered=False,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_ROOT_ENCLOSURE_AUTHORED',flush=True)
