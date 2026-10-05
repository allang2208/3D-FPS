"""M08 dorsal pressure cannon: planted crouch, arch loading, recoil and recovery.
Own authored animation, pressure ring and synthesized audio; no downloaded art.
"""
import bpy, ast, json, math, random, wave, array
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'AirCannonV06_20261004';OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
SOURCE=BASE/'PounceV05_20261004/M08_Pounce_Animated_V05.blend'
prior=json.loads((BASE/'BoneheadV04_20261004/authoring.json').read_text(encoding='utf-8'))
spec=prior['bones'];by={r['name']:r for r in spec}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
obj=bpy.data.objects['SK_LurkerM08'];rig=bpy.data.objects['Armature'];arm=rig.data
mod=next(m for m in obj.modifiers if m.type=='ARMATURE');mod.show_viewport=False
rig.animation_data_create();rig.animation_data.action=None
NAMES=[b.name for b in arm.bones];PARENT={b.name:b.parent.name if b.parent else None for b in arm.bones}
REST={b.name:b.matrix_local.copy() for b in arm.bones}
LOCAL={n:REST[PARENT[n]].inverted()@REST[n] if PARENT[n] else REST[n].copy() for n in NAMES}
module=ast.parse((PROJECT/'Tools/LurkerM08/author_canine_v03.py').read_text(encoding='utf-8'))
helpers={'fk','world','orient','aim','turn','move_world','ease','two_bone','rest_pole','fit_hock','support_helpers'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<M08 fitted rig adapters>','exec'))
module=ast.parse((PROJECT/'Tools/LurkerM08/author_pounce_v05.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='curve'],type_ignores=[]),'<M08 continuous motion>','exec'))

duration=1.85;count=round(duration*120);scene.frame_start=1;scene.frame_end=count+1
action=bpy.data.actions.new('A_M08_AttackAirCannon_AirV06');action.use_fake_user=True;rig.animation_data.action=action
for index in range(count+1):
    t=index/120;local={n:m.copy() for n,m in LOCAL.items()}
    load=curve(t,[(0,0),(.12,.20),(.34,1),(.82,1),(.92,.86),(1.04,1),(1.30,.55),(1.65,.08),(duration,0)])
    recoil=curve(t,[(0,0),(.92,0),(.98,1),(1.10,-.20),(1.25,.12),(1.45,0),(duration,0)])
    local['pelvis'].translation+=REST['root'].inverted().to_3x3()@Vector((0,.028*load+.045*recoil,-.115*load-.018*recoil))
    turn(local,'pelvis',.055*load-.055*recoil)
    for n,gain,lag in [('spine_01',.28,.035),('spine_02',.32,.018),('chest',.40,0)]:
        wave_recoil=curve(max(0,t-lag),[(0,0),(.92,0),(.98,1),(1.11,-.23),(1.28,.08),(1.5,0),(duration,0)])
        turn(local,n,(.08*load-.12*wave_recoil)*gain)
    turn(local,'neck',.08*load+.025*recoil);turn(local,'head',-.035*load-.045*recoil)
    turn(local,'jaw',math.radians(-18+10*load-4*recoil))
    for side,sign in [('L',1),('R',-1)]:
        move_world(local,'scapula.'+side,Vector((0,.025*load+.012*recoil,-.008*load)))
        # Four existing contact points stay fixed throughout the crouch/recoil.
        foot='hand.'+side
        two_bone(local,['upperarm.'+side,'forearm.'+side,foot],REST[foot].translation,rest_pole('upperarm.'+side,'forearm.'+side,foot))
        orient(local,foot,REST[foot].to_quaternion())
        foot='hindfoot.'+side
        preferred=(REST[foot].translation-REST['ankle.'+side].translation).normalized()
        fit_hock(local,side,REST[foot].translation,preferred)
        orient(local,foot,REST[foot].to_quaternion())
        for digit in range(1,6):
            # Small base-joint tension, no wholesale curling into the support.
            turn(local,f'finger{digit}_01.{side}',math.radians(2.5)*load)
    support_helpers(local)
    w=fk(local);yf=REST['arch_front.L'].translation.y;yr=REST['arch_rear.L'].translation.y
    pressure=curve(t,[(0,0),(.25,.1),(.65,.75),(.90,1),(.965,-.30),(1.10,.20),(1.27,-.07),(1.48,0),(duration,0)])
    for n in NAMES:
        if not n.startswith('arch_'):continue
        u=max(0,min(1,(REST[n].translation.y-yf)/(yr-yf)));taper=math.sin(math.pi*u)**2
        pose=w[n].copy()
        pose.translation+=Vector((REST[n].translation.x*.10*pressure, -.035*recoil, .065*pressure))*taper
        world(local,n,pose)
    for n in NAMES:
        pb=rig.pose.bones[n];loc,q,s=(LOCAL[n].inverted()@local[n]).decompose()
        if index>0 and pb.rotation_quaternion.dot(q)<0:q.negate()
        pb.rotation_mode='QUATERNION';pb.location=loc;pb.rotation_quaternion=q;pb.scale=(1,1,1)
        for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=index+1,group=n)

scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
fbx=ANIM/(action.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_AirCannon_Animated_V06.blend'))

# Ring normal +Z, outer radius 34 cm, matching the swept gameplay sphere.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_torus_add(major_radius=.32,minor_radius=.02,major_segments=48,minor_segments=8)
ring=bpy.context.object;ring.name='SM_M08_PressureRing'
for poly in ring.data.polygons:poly.use_smooth=True
ring_file=OUT/'SM_M08_PressureRing.fbx'
bpy.ops.export_scene.fbx(filepath=str(ring_file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_anim=False)

def audio(name,seconds,charge):
    rng=random.Random(8086 if charge else 8087);rate=44100;data=array.array('h');low=0.;phase=0.
    for i in range(round(seconds*rate)):
        t=i/rate;u=t/seconds;noise=rng.uniform(-1,1);low+=.12*(noise-low)
        if charge:
            env=math.sin(math.pi*min(1,t/.045)/2)*min(1,(seconds-t)/.08)*(u**.65)
            phase+=2*math.pi*(80+u*120)/rate
            v=env*(.23*low+.055*math.sin(phase)+.035*noise)
        else:
            env=min(1,t/.003)*math.exp(-t*10)*min(1,(seconds-t)/.08)
            phase+=2*math.pi*(45+90*math.exp(-t*22))/rate
            v=env*(.55*low+.24*math.sin(phase)+.17*noise)
        data.append(round(max(-.95,min(.95,v))*32767))
    file=OUT/(name+'.wav')
    with wave.open(str(file),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(data.tobytes())
    return str(file)

report={'revision':'M08_AirCannonV06_20261004','source_skin':str(SOURCE),'mesh_asset':prior['mesh_asset'],
    'clips':{'AttackAirCannon':{'file':str(fbx),'seconds':duration,'frames':count+1,'loop':False,'contact':[.92,.92]}},
    'pressure_ring':str(ring_file),'audio':{'charge':audio('S_M08_AirCharge',.92,True),'release':audio('S_M08_AirRelease',.62,False)},
    'fire_source_seconds':.92,'lock_lead_seconds':.10,'runtime_tested':False,'preview_rendered':False,
    'provenance':'Original local animation, ring geometry and deterministic synthesized noise audio. Existing user Meshy skin retained.'}
(OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_AIR_CANNON_V06_AUTHORING_SAVED',flush=True)
