"""M08 contact-locomotion support poses and bespoke alien actions. No donor motion.
V03's fitted skin is retained; root travel remains owned by the gameplay clock.
"""
import bpy, ast, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OLD=BASE/'CanineRigV03_20261004'
OUT=BASE/'BoneheadV04_20261004';OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
SOURCE=OLD/'M08_CanineRig_Skin_V03.blend'
spec=json.loads((OLD/'authoring.json').read_text(encoding='utf-8'))['bones']
by={r['name']:r for r in spec}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
obj=bpy.data.objects['SK_LurkerM08'];rig=bpy.data.objects['Armature'];arm=rig.data
mod=next(m for m in obj.modifiers if m.type=='ARMATURE');mod.show_viewport=False
rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
rig.animation_data_create()
NAMES=[b.name for b in arm.bones];PARENT={b.name:b.parent.name if b.parent else None for b in arm.bones}
REST={b.name:b.matrix_local.copy() for b in arm.bones}
LOCAL={n:REST[PARENT[n]].inverted()@REST[n] if PARENT[n] else REST[n].copy() for n in NAMES}
# Reuse the fitted rig's coordinate/IK adapters only. No canine motion is read.
module=ast.parse((PROJECT/'Tools/LurkerM08/author_canine_v03.py').read_text(encoding='utf-8'))
names={'fk','world','orient','aim','turn','move_world','ease','curve','two_bone','rest_pole','fit_hock','support_helpers'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<M08 fitted rig adapters>','exec'))
common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
clips={'Idle':(3.,True),'IdleAlert':(1.8,True),'Walk':(1.,True),'Run':(.8,True),
       'AttackBite':(.85,False),'AttackPounce':(1.1,False),'TraverseJump':(1.1,False),
       'HitFront':(.55,False),'HitLeft':(.55,False),'HitRight':(.55,False),'Death':(1.4,False)}
report={'revision':'M08_BoneheadV04_20261004','source_skin':str(SOURCE),
        'mesh_asset':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03',
        'reference':{'repository':'https://github.com/WeaverDev/Bonehead','commit':'acc989256fa0fe8bc70dcfd5da29f032b3765fd6',
            'license':'MIT (scripts only)','art_used':False},
        'bones':spec,'clips':{},'locomotion':'runtime contact stepping, neutral support clips; no canine gait',
        'runtime_tested':False,'preview_rendered':False}
for role,(duration,loop) in clips.items():
    count=round(duration*120);scene.frame_start=1;scene.frame_end=count+1
    action=bpy.data.actions.new('A_M08_'+role+'_BoneheadV04');action.use_fake_user=True;rig.animation_data.action=action
    for index in range(count+1):
        t=index/120;p=t/duration;local={n:m.copy() for n,m in LOCAL.items()}
        shift=Vector();pitch=0.;chest_pitch=0.;head_pitch=0.;yaw=0.;jaw=-18.
        if role in ('Idle','IdleAlert','Walk','Run'):
            breath=math.sin(p*math.tau)
            # Subtle breathing only. Runtime contact solver owns foot cycles.
            shift.z=.0035*breath
            chest_pitch=.006*breath;head_pitch=-.004*math.sin(p*math.tau-.3)
            if role=='IdleAlert':head_pitch=-.025+.018*breath
            jaw=-18.+.6*breath
        elif role=='AttackBite':
            shift.y=curve(t,[(0,0),(.13,.045),(.30,-.105),(.42,-.095),(.64,-.025),(.85,0)])
            shift.z=curve(t,[(0,0),(.13,-.036),(.30,-.015),(.42,-.022),(.62,-.01),(.85,0)])
            chest_pitch=curve(t,[(0,0),(.14,-.09),(.30,.09),(.42,.06),(.62,-.02),(.85,0)])
            head_pitch=curve(t,[(0,0),(.19,-.09),(.30,.15),(.41,.10),(.59,-.04),(.85,0)])
            jaw=curve(t,[(0,-18),(.17,5),(.265,2),(.30,-32),(.42,-32),(.59,-23),(.85,-18)])
        elif role in ('AttackPounce','TraverseJump'):
            shift.y=curve(t,[(0,0),(.13,.055),(.28,-.015),(.54,-.035),(.65,-.025),(.89,-.01),(1.1,0)])
            shift.z=curve(t,[(0,0),(.13,-.080),(.26,.018),(.45,.027),(.59,-.075),(.72,-.025),(.94,-.007),(1.1,0)])
            pitch=curve(t,[(0,0),(.14,-.04),(.30,.075),(.48,.055),(.62,.04),(.84,-.012),(1.1,0)])
            chest_pitch=curve(t,[(0,0),(.13,-.09),(.30,-.02),(.48,.06),(.59,.12),(.76,-.025),(1.1,0)])
            head_pitch=curve(t,[(0,0),(.13,-.02),(.32,-.10),(.52,.045),(.65,.02),(.86,-.025),(1.1,0)])
            if role=='AttackPounce':jaw=curve(t,[(0,-18),(.17,3),(.47,3),(.52,-32),(.64,-32),(.84,-22),(1.1,-18)])
        elif role.startswith('Hit'):
            hit=curve(t,[(0,0),(.085,1),(.20,.8),(.38,.23),(.55,0)])
            side=0 if role=='HitFront' else 1 if role=='HitLeft' else -1
            shift=Vector((side*.035*hit,.075*hit,-.023*hit));yaw=side*.085*hit
            chest_pitch=-.09*hit;head_pitch=-.065*hit;jaw=-18+5*hit
        elif role=='Death':
            drop=ease(t/.95);shift=Vector((.17*drop,.025*drop,-.29*drop))
            yaw=.06*drop;chest_pitch=.12*drop;head_pitch=.12*drop;jaw=-18+13*ease(p)
        local['pelvis'].translation+=REST['root'].inverted().to_3x3()@shift
        turn(local,'pelvis',pitch)
        if role=='Death':turn(local,'pelvis',.90*ease(t/.95),(0,1,0))
        turn(local,'spine_01',chest_pitch*.22)
        turn(local,'spine_02',chest_pitch*.33)
        turn(local,'chest',chest_pitch*.45)
        turn(local,'chest',yaw,(0,0,1))
        turn(local,'neck',head_pitch*.4);turn(local,'head',head_pitch*.6)
        turn(local,'jaw',math.radians(jaw))
        for side,sign in [('L',1),('R',-1)]:
            for front in (True,False):
                foot=('hand.' if front else 'hindfoot.')+side
                goal=REST[foot].translation.copy();swing=0.;delay=0 if side=='L' else .028
                tt=max(0,t-delay)
                if role in ('AttackPounce','TraverseJump'):
                    if front:
                        goal.y+=curve(tt,[(0,0),(.15,0),(.28,-.205),(.45,-.165),(.56,-.07),(.76,-.05),(1.1,0)])
                        goal.z+=curve(tt,[(0,0),(.16,0),(.30,.17),(.43,.10),(.54,0),(1.1,0)])
                        swing=curve(tt,[(0,0),(.16,0),(.26,1),(.42,.8),(.54,0),(1.1,0)])
                    else:
                        goal.y+=curve(tt,[(0,0),(.16,0),(.27,.13),(.40,-.11),(.56,-.09),(.68,0),(1.1,0)])
                        goal.z+=curve(tt,[(0,0),(.18,0),(.30,.10),(.44,.16),(.64,0),(1.1,0)])
                        swing=curve(tt,[(0,0),(.18,0),(.31,1),(.50,.8),(.64,0),(1.1,0)])
                elif role=='AttackBite' and front:
                    stagger=.0 if side=='L' else .052;tt=max(0,t-stagger)
                    goal.y+=curve(tt,[(0,0),(.12,0),(.26,-.07),(.46,-.07),(.70,-.02),(.85,0)])
                    goal.z+=curve(tt,[(0,0),(.12,0),(.20,.032),(.275,0),(.85,0)])
                    swing=curve(tt,[(0,0),(.12,0),(.20,1),(.275,0),(.85,0)])
                elif role.startswith('Hit') and front and side==('R' if role=='HitRight' else 'L'):
                    goal.y+=curve(t,[(0,0),(.10,0),(.25,.055),(.39,.04),(.55,0)])
                    goal.z+=curve(t,[(0,0),(.12,0),(.21,.038),(.31,0),(.55,0)])
                    swing=curve(t,[(0,0),(.12,0),(.21,1),(.31,0),(.55,0)])
                elif role=='Death':
                    release=ease((t-(.19 if side=='R' else .37))/.44)
                    goal=goal.lerp(fk(local)[foot].translation,release);swing=release*.25
                if front:
                    glide=max(-.035,min(.035,(goal.y-REST[foot].translation.y)*.15))
                    move_world(local,'scapula.'+side,Vector((0,glide,0)))
                    two_bone(local,['upperarm.'+side,'forearm.'+side,foot],goal,rest_pole('upperarm.'+side,'forearm.'+side,foot))
                else:fit_hock(local,side,goal,(REST[foot].translation-REST['ankle.'+side].translation).normalized())
                orient(local,foot,Quaternion(Vector((1,0,0)),math.radians(9 if front else 6)*swing)@REST[foot].to_quaternion())
                if front:
                    for finger in range(1,6):
                        turn(local,f'finger{finger}_01.{side}',math.radians(5)*swing)
                        turn(local,f'finger{finger}_02.{side}',math.radians(12+finger)*swing)
                else:
                    for toe in range(1,4):turn(local,f'toe{toe}.{side}',math.radians(6)*swing)
        support_helpers(local)
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
    contact=[.30,.42] if role=='AttackBite' else [.52,.64] if role=='AttackPounce' else [-1,-1]
    report['clips'][role]={'file':str(file),'seconds':duration,'frames':count+1,'loop':loop,'contact':contact,
        'source':'M08 authored control poses, no canine donor'}
    (OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M08_BONEHEAD_V04_ACTION_SAVED',role,flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_Bonehead_Animated_V04.blend'))
print('M08_BONEHEAD_V04_AUTHORING_SAVED',flush=True)
