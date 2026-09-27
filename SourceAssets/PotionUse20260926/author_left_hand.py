"""Editable V7 AKM hand source for the shared native-rig potion pose layer.
The JSON is the runtime authority. This bakes that motion in Blender; no renders.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).parent
cfg = json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text())
times = cfg['times']
C = Matrix(((0,1,0),(1,0,0),(0,0,1)))
bpy.context.preferences.filepaths.save_version = 0

def ease(t):
    t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
def frame(f,n):
    f=f.normalized();z=(n-f*n.dot(f)).normalized()
    return Matrix((f,f.cross(z),z)).transposed()
def xy(f,n):
    f=f.normalized();y=(n-f*n.dot(f)).normalized()
    return Matrix((f,y,f.cross(y))).transposed().to_quaternion()
def ue_rotation(e):
    p,y,r=map(math.radians,e)
    return Quaternion((0,0,1),y)@Quaternion((0,1,0),-p)@Quaternion((1,0,0),-r)
keys=[(k['time'],Vector(k['grip']),ue_rotation(k['rotation'])) for k in cfg['keys']]
def tangent(j):
    if j==0 or j==len(keys)-1:return Vector((0,0,0))
    if (keys[j][1]-keys[j-1][1]).length<.01 or (keys[j][1]-keys[j+1][1]).length<.01:return Vector((0,0,0))
    return (keys[j+1][1]-keys[j-1][1])/(keys[j+1][0]-keys[j-1][0])
def grip(t):
    for i in range(1,len(keys)):
        a,b=keys[i-1],keys[i]
        if t<=b[0]:
            span=b[0]-a[0];u=max(0,min(1,(t-a[0])/span))
            p=a[1]*(2*u**3-3*u*u+1)+tangent(i-1)*span*(u**3-2*u*u+u)+b[1]*(-2*u**3+3*u*u)+tangent(i)*span*(u**3-u*u)
            return p,a[2].slerp(b[2],ease(u))
    return keys[-1][1],keys[-1][2]
upright=Matrix(((1,0,0),(0,0,1),(0,-1,0))).to_quaternion()

# Accepted AKM reload entry supplies the live weapon grip; V7 supplies geometry
# and original bindings. No weapon animation or shared bare-arm asset is edited.
donor=ROOT/'SourceAssets/RifleMagazineGrip20260922/FingerContactV3/AKM/standard/base/A_AKM_reload.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
donor_rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
entry={b.name:b.matrix.copy() for b in donor_rig.pose.bones}

for family in ['hp_potion','mp_potion']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/AKM_BareArmsV7.blend'))
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
    for o in list(scene.objects):
        if o.type not in {'ARMATURE','MESH'}:bpy.data.objects.remove(o,do_unlink=True)
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
    local={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
    source={n:entry.get(n,m).copy() for n,m in rest.items()}
    def left(n):
        if not n.endswith('_l'):return False
        while n:
            if n=='clavicle_l':return True
            n=parents[n]
        return False
    names=[n for n in rest if left(n)]
    rig.animation_data_clear();rig.animation_data_create()
    action=bpy.data.actions.new('PotionDrinkThrow_'+family)
    rig.animation_data.action=action
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION'
        for constraint in list(b.constraints):b.constraints.remove(constraint)
    with bpy.data.libraries.load(str(OUT/(family+'_DrinkParts.blend')),link=False) as (a,b):
        b.objects=[n for n in a.objects if n.startswith('SM_')]
    parts={}
    for o in b.objects:
        if o:
            scene.collection.objects.link(o);parts[o.name.rsplit('_',1)[-1]]=o
    H0=rest['hand_l'].translation
    normal=(rest['pinky_01_l'].translation-H0).cross(rest['index_01_l'].translation-H0).normalized()
    reference=frame(rest['middle_01_l'].translation-H0,normal)
    RU=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
    RL=rest['hand_l'].translation-rest['lowerarm_l'].translation
    family_cfg=cfg[family]
    scene.render.fps=120;scene.frame_start=0;scene.frame_end=round(times['duration']*120)
    for f in range(scene.frame_end+1):
        t=f/120;scene.frame_set(f)
        g,rot=grip(t);palm=rot@upright
        wrist=C@(g-palm@Vector(family_cfg['grip_in_palm']))*.01
        sem=C@palm.to_matrix()
        A=C@Vector(cfg['shoulder'])*.01;reach=wrist-A
        limit=(RU.length+RL.length)*.93
        if reach.length>limit:A+=reach.normalized()*(reach.length-limit)
        axis=(wrist-A).normalized();d=(wrist-A).length
        pole=C@Vector(cfg['elbow_pole'])*.01-A;pole=(pole-axis*pole.dot(axis)).normalized()
        along=(RU.length_squared-RL.length_squared+d*d)/(2*d)
        E=A+axis*along+pole*math.sqrt(max(0,RU.length_squared-along*along))
        LD=(wrist-E).normalized();UD=(E-A).normalized()
        lower_deform=xy(LD,sem.col[1])@xy(RL,reference.col[1]).inverted()
        upper_deform=(lower_deform@RU.normalized()).rotation_difference(UD)@lower_deform
        goal=source.copy()
        closure=ease((t-times['grab']*.42)/(times['grab']*.58))*(1-ease((t-(times['release']-.025))/.08))
        weight=ease(t/times['grab'])*(1-ease((t-times['recover'])/(times['duration']-times['recover'])))
        for n in names:
            if n=='clavicle_l':
                m=source[n].copy();m.translation+=A-source['upperarm_l'].translation
            elif n=='upperarm_l':m=Matrix.LocRotScale(A,upper_deform@rest[n].to_quaternion(),rest[n].to_scale())
            elif n=='lowerarm_l':m=Matrix.LocRotScale(E,lower_deform@rest[n].to_quaternion(),rest[n].to_scale())
            elif n=='hand_l':m=Matrix.LocRotScale(wrist,(sem@reference.inverted()@rest[n].to_3x3()).to_quaternion(),rest[n].to_scale())
            else:
                m=goal[parents[n]]@local[n];bits=n.split('_')
                if len(bits)==3 and bits[0] in family_cfg['digits'] and bits[1].isdigit():
                    digit=family_cfg['digits'][bits[0]];j=int(bits[1])-1
                    nxt=f'{bits[0]}_{j+2:02d}_l'
                    direction=rest[nxt].translation-rest[n].translation if nxt in rest else rest[n].to_quaternion()@(rest[parents[n]].to_quaternion().inverted()@(rest[n].translation-rest[parents[n]].translation))
                    c=closure
                    if bits[0]=='thumb':c*=1-.72*ease((t-.47)/.12)*(1-ease((t-times['uncap'])/.13))
                    flex=math.radians((8+j*4)*(1-c)+digit['flex'][j]*c)
                    spread=math.radians(digit['spread'][j])
                    target=sem@Matrix.Rotation(spread,3,'Z')@Matrix.Rotation(-flex,3,'Y')
                    q=(target@frame(direction,normal).inverted()@rest[n].to_3x3()).to_quaternion()
                    m=Matrix.LocRotScale(m.translation,q,local[n].to_scale())
            goal[n]=m
        output=source.copy()
        for n in names:
            parent=parents[n]
            a=source[parent].inverted()@source[n];b=goal[parent].inverted()@goal[n]
            m=Matrix.LocRotScale(a.translation.lerp(b.translation,weight),a.to_quaternion().slerp(b.to_quaternion(),weight),a.to_scale().lerp(b.to_scale(),weight))
            output[n]=output[parent]@m
        for bone in rig.pose.bones:
            bone.matrix=output[bone.name]
            bone.keyframe_insert('location',frame=f,group=bone.name)
            bone.keyframe_insert('rotation_quaternion',frame=f,group=bone.name)
            bone.keyframe_insert('scale',frame=f,group=bone.name)
        for kind,o in parts.items():
            at=min(t,times['uncap'] if kind=='stopper' else times['release'])
            gp,rp=grip(at);position=gp-rp@Vector((0,0,family_cfg['grip_height']))
            dt=max(0,t-(times['uncap'] if kind=='stopper' else times['release']))
            if dt:
                vel=Vector((80,-140,160)) if kind=='stopper' else Vector((540,-360,190))
                position+=vel*dt+Vector((0,0,-490*dt*dt))
                rp=rp@Quaternion(Vector((-210,360,180)).normalized(),math.radians(420)*dt)
            o.location=C@position*.01;o.rotation_mode='QUATERNION';o.rotation_quaternion=(C@rp.to_matrix()@C).to_quaternion()
            o.scale=(1,1,1)
            if kind=='liquid':o.scale.z=max(.001,1-ease((t-times['drink_start'])/(times['drink_end']-times['drink_start'])))
            o.hide_render=t<times['grab'] or (kind=='liquid' and t>=times['contact'])
            for prop in ['location','rotation_quaternion','scale','hide_render']:o.keyframe_insert(prop,frame=f)
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:point.interpolation='LINEAR'
    for name in ['grab','uncap','contact','release','recover']:
        scene.timeline_markers.new(name,frame=round(times[name]*120))
    scene.frame_set(90)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('AKM_V7_'+family+'_DrinkThrow.blend')))
    print('POTION_HAND_AUTHORED '+family,flush=True)
