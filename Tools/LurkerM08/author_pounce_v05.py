"""M08 V05: hind-leg launch, axial extension, airborne gathering, loaded landing.
Only replaces AttackPounce / TraverseJump. Keeps V04 skin, locomotion and bite.
"""
import bpy, ast, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'PounceV05_20261004';OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
SOURCE=BASE/'BoneheadV04_20261004/M08_Bonehead_Animated_V04.blend'
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

def curve(t,keys):
    """Monotone cubic Hermite: interior motion continues through passing keys.
    Only true extrema, holds, and clip endpoints have zero tangent.
    """
    if t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    d=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(keys,keys[1:])]
    def slope(i):
        if i==0 or i==len(keys)-1 or d[i-1]*d[i]<=0:return 0.
        h0=keys[i][0]-keys[i-1][0];h1=keys[i+1][0]-keys[i][0]
        w0=2*h1+h0;w1=h1+2*h0
        return (w0+w1)/(w0/d[i-1]+w1/d[i])
    for i,((a,av),(b,bv)) in enumerate(zip(keys,keys[1:])):
        if t<=b:
            h=b-a;u=(t-a)/h
            return (2*u**3-3*u*u+1)*av+(u**3-2*u*u+u)*h*slope(i)+(-2*u**3+3*u*u)*bv+(u**3-u*u)*h*slope(i+1)

def axial(t):
    local={n:m.copy() for n,m in LOCAL.items()}
    y=curve(t,[(0,0),(.15,.095),(.24,.045),(.35,-.040),(.54,-.025),(.74,-.055),(.85,-.075),(1.05,-.022),(1.5,0)])
    z=curve(t,[(0,0),(.16,-.105),(.25,-.005),(.36,.030),(.53,.008),(.72,-.025),(.81,-.105),(.97,-.045),(1.13,-.008),(1.5,0)])
    local['pelvis'].translation+=REST['root'].inverted().to_3x3()@Vector((0,y,z))
    hip=curve(t,[(0,0),(.15,.075),(.30,-.22),(.46,-.09),(.60,.14),(.68,.10),(.74,.015),(.82,-.07),(.99,-.035),(1.20,.025),(1.5,0)])
    turn(local,'pelvis',hip)
    # Chest leads extension; lumbar and pelvis follow with delayed peaks.
    for n,delay,gain in [('spine_01',.035,.28),('spine_02',.018,.32),('chest',0,.40)]:
        tt=max(0,t-delay)
        bend=curve(tt,[(0,0),(.14,-.17),(.29,-.11),(.48,.09),(.65,-.025),(.74,.035),(.82,.14),(.99,-.045),(1.18,.025),(1.5,0)])
        turn(local,n,bend*gain)
        stretch=curve(tt,[(0,0),(.15,-.035),(.32,.085),(.47,.045),(.61,-.025),(.78,-.04),(1.02,.025),(1.5,0)])
        move_world(local,n,Vector((0,-stretch*gain,0)))
    head=curve(max(0,t-.045),[(0,0),(.17,-.08),(.31,.09),(.48,-.11),(.67,-.14),(.80,.07),(.93,-.10),(1.08,.035),(1.5,0)])
    turn(local,'neck',head*.40);turn(local,'head',head*.60)
    return local

def arch_lag(local,t):
    w=fk(local);delayed=fk(axial(max(0,t-.065)))
    lag=(delayed['chest'].translation-w['chest'].translation)*.20
    if lag.length>.035:lag=lag.normalized()*.035
    # C1 taper fixes both roots to the torso and flexes only the central span.
    yf=REST['arch_front.L'].translation.y;yr=REST['arch_rear.L'].translation.y
    for n in NAMES:
        if not n.startswith('arch_'):continue
        u=max(0.,min(1.,(REST[n].translation.y-yf)/(yr-yf)))
        weight=math.sin(math.pi*u)**2
        pose=w[n].copy();pose.translation+=lag*weight;world(local,n,pose)

common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
report={'revision':'M08_PounceV05_20261004','source_skin':str(SOURCE),'mesh_asset':prior['mesh_asset'],'bones':spec,
    'clips':{},'runtime_tested':False,'preview_rendered':False,
    'source_takeoff':.24,'source_landing':.74,'motion':'M08 authored hind-leg spring and long-arm catch; continuous Hermite motion'}
for role in ('AttackPounce','TraverseJump'):
    duration=1.5;count=round(duration*120);scene.frame_start=1;scene.frame_end=count+1
    action=bpy.data.actions.new('A_M08_'+role+'_PounceV05');action.use_fake_user=True;rig.animation_data.action=action
    for index in range(count+1):
        t=index/120;local=axial(t)
        jaw=curve(t,[(0,-18),(.20,4),(.54,5),(.67,2),(.72,-32),(.86,-30),(1.05,-21),(1.5,-18)]) if role=='AttackPounce' else -18.
        turn(local,'jaw',math.radians(jaw))
        for side,sign in [('L',1),('R',-1)]:
            delay=0 if side=='L' else .028
            # The two hands leave separately; hind feet push until takeoff.
            for front in (True,False):
                foot=('hand.' if front else 'hindfoot.')+side
                tt=max(0.,t-delay);goal=REST[foot].translation.copy()
                if front:
                    dy=curve(tt,[(0,0),(.19,0),(.33,-.215),(.46,-.075),(.58,-.115),(.74,-.16),(1.08,-.16),(1.24,-.045),(1.43,0),(1.5,0)])
                    dz=curve(tt,[(0,0),(.19,0),(.34,.325),(.49,.245),(.62,.13),(.74,0),(1.09,0),(1.21,.045),(1.38,0),(1.5,0)])
                    swing=curve(tt,[(0,0),(.19,0),(.35,1),(.49,.90),(.66,.25),(.74,0),(1.09,0),(1.21,.45),(1.38,0),(1.5,0)])
                    goal.x+=sign*curve(tt,[(0,0),(.28,.02),(.48,-.06),(.66,.02),(.74,.025),(1.1,.025),(1.5,0)])
                    glide=curve(tt,[(0,0),(.15,.018),(.29,-.05),(.48,.015),(.68,-.045),(.82,.045),(1.02,.01),(1.5,0)])
                    move_world(local,'scapula.'+side,Vector((0,glide,0)))
                else:
                    dy=curve(tt,[(0,0),(.24,0),(.32,.16),(.48,-.24),(.62,-.19),(.74,.02),(.84,.08),(1.10,.08),(1.34,0),(1.5,0)])
                    dz=curve(tt,[(0,0),(.24,0),(.32,.07),(.49,.31),(.66,.20),(.84,0),(1.10,0),(1.22,.035),(1.37,0),(1.5,0)])
                    swing=curve(tt,[(0,0),(.24,0),(.39,1),(.61,.8),(.84,0),(1.10,0),(1.22,.4),(1.37,0),(1.5,0)])
                goal+=Vector((0,dy,dz))
                if front:
                    two_bone(local,['upperarm.'+side,'forearm.'+side,foot],goal,rest_pole('upperarm.'+side,'forearm.'+side,foot))
                else:
                    preferred=(REST[foot].translation-REST['ankle.'+side].translation).normalized()
                    preferred=Quaternion(Vector((1,0,0)),curve(tt,[(0,0),(.24,-.12),(.34,.15),(.51,-.24),(.84,0),(1.5,0)]))@preferred
                    fit_hock(local,side,goal,preferred)
                wrist=math.radians(24 if front else 17)*swing
                orient(local,foot,Quaternion(Vector((1,0,0)),wrist)@REST[foot].to_quaternion())
                if front:
                    for digit in range(1,6):
                        turn(local,f'finger{digit}_01.{side}',math.radians(12)*swing)
                        turn(local,f'finger{digit}_02.{side}',math.radians(22+digit)*swing)
                else:
                    for digit in range(1,4):turn(local,f'toe{digit}.{side}',math.radians(14)*swing)
        support_helpers(local);arch_lag(local,t)
        for n in NAMES:
            pb=rig.pose.bones[n];loc,q,s=(LOCAL[n].inverted()@local[n]).decompose()
            if index>0 and pb.rotation_quaternion.dot(q)<0:q.negate()
            pb.rotation_mode='QUATERNION';pb.location=loc;pb.rotation_quaternion=q;pb.scale=(1,1,1)
            for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=index+1,group=n)
    scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    file=ANIM/(action.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),object_types={'ARMATURE'},bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,**common)
    report['clips'][role]={'file':str(file),'seconds':duration,'frames':count+1,'loop':False,
        'contact':[.70,.88] if role=='AttackPounce' else [-1,-1]}
    (OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M08_POUNCE_V05_ACTION_SAVED',role,flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_Pounce_Animated_V05.blend'))
print('M08_POUNCE_V05_AUTHORING_SAVED',flush=True)
