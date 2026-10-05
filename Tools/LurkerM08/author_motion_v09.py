"""M08 V09: supported oral clearance and less synchronized attack motion.
Reuses the retained fitted rig and V05/V06 authoring helpers, never edits skin.
"""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUTPUT=BASE/'MotionV09_20261005'
OUTPUT.mkdir(exist_ok=True)

def prepare_mouth(ns):
    obj=ns['obj']; rig=ns['rig']; rest=ns['REST']
    coords=np.empty(len(obj.data.vertices)*3,dtype=np.float64)
    obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    old=json.loads((BASE/'ProductionV01_20261004/authoring.json').read_text(encoding='utf-8'))
    pelvis=next(b for b in old['bones'] if b['name']=='pelvis')
    offset=np.array(pelvis['head'])/old['scale']-np.array((0,.52,-.055))
    raw=coords/old['scale']-offset
    ids=np.flatnonzero((raw[:,1]<-.60)&(np.abs(raw[:,0])<.25)&(raw[:,2]<-.12))
    if not len(ids):raise RuntimeError('M08 lower oral surface is missing')
    # Three lateral columns by four front/back bands retain the actual bottom
    # lip/teeth surface, rather than inventing a jaw-centre offset.
    rows=[]
    xs=np.linspace(raw[ids,0].min()-1e-6,raw[ids,0].max()+1e-6,4)
    ys=np.linspace(raw[ids,1].min()-1e-6,raw[ids,1].max()+1e-6,5)
    for x in range(3):
        for y in range(4):
            subset=ids[(raw[ids,0]>=xs[x])&(raw[ids,0]<xs[x+1])&(raw[ids,1]>=ys[y])&(raw[ids,1]<ys[y+1])]
            if not len(subset):continue
            vi=int(subset[np.argmin(coords[subset,2])]);v=obj.data.vertices[vi]
            weights=[{'bone':obj.vertex_groups[g.group].name,'weight':float(g.weight)} for g in v.groups
                if obj.vertex_groups[g.group].name in rest and g.weight>1e-6]
            total=sum(w['weight'] for w in weights)
            if total<=0:raise RuntimeError('Unbound oral sample')
            for w in weights:w['weight']/=total
            rows.append({'vertex':vi,'position_m':list(v.co),'weights':weights})
    binding={'mesh_asset':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03','landmarks':rows,
        'calibration_bones':{n:list(rig.data.bones[n].head_local) for n in ('pelvis','chest','hand.L','hand.R','arch_crown')},
        'purpose':'Lower mouth surface support samples, original skin weights',
        'runtime_tested':False,'rendered':False}
    (OUTPUT/'mouth_binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
    samples=[[(w['bone'],rest[w['bone']].inverted()@Vector(r['position_m']),w['weight']) for w in r['weights']] for r in rows]
    def under(bone,ancestor):
        while bone:
            if bone==ancestor:return True
            bone=ns['PARENT'][bone]
        return False
    def clearance(local):
        pose=ns['fk'](local);lift=0.
        for row in samples:
            point=sum(((pose[n]@p)*weight for n,p,weight in row),Vector())
            response=sum(weight*(.65*under(n,'chest')+.35*under(n,'neck')) for n,p,weight in row)
            if response>.1:lift=max(lift,(.035-point.z)/response)
        if lift>0:
            ns['move_world'](local,'chest',Vector((0,0,lift*.65)))
            ns['move_world'](local,'neck',Vector((0,0,lift*.35)))
    return clearance

air=(PROJECT/'Tools/LurkerM08/author_air_cannon_v06.py').read_text(encoding='utf-8').split('# Ring normal +Z')[0]
air=air.replace("OUT=BASE/'AirCannonV06_20261004'","OUT=BASE/'MotionV09_20261005'")
air=air.replace('A_M08_AttackAirCannon_AirV06','A_M08_AttackAirCannon_MotionV09')
air=air.replace('M08_AirCannon_Animated_V06.blend','M08_AirCannon_MotionV09.blend')
air=air.replace('duration=1.85;',"clear_mouth=prepare_mouth(globals())\nduration=1.85;")
air=air.replace('-.115*load-.018*recoil','-.055*load-.010*recoil')
air=air.replace("turn(local,'neck',.08*load+.025*recoil);turn(local,'head',-.035*load-.045*recoil)",
    "turn(local,'neck',-.025*load+.020*recoil);turn(local,'head',-.045*load-.035*recoil)")
air=air.replace("    for side,sign in [('L',1),('R',-1)]:", "    clear_mouth(local)\n    for side,sign in [('L',1),('R',-1)]:")
# A slow, small pressure rise keeps the hold alive without shaking the feet.
air=air.replace('(.34,1),(.82,1)', '(.34,.88),(.66,.96),(.82,1)')
air=air.replace('(.98,1),(1.10,-.20),(1.25,.12),(1.45,0)', '(.965,1),(1.09,-.16),(1.30,.065),(1.60,0)')
ns={'__name__':'__m08_air_v09__','prepare_mouth':prepare_mouth}
exec(compile(air,'<M08 V09 air-cannon authoring>','exec'),ns)
clips={'AttackAirCannon':{'file':str(ns['fbx']),'seconds':1.85,'frames':223,'loop':False,'contact':[.92,.92]}}

pounce=(PROJECT/'Tools/LurkerM08/author_pounce_v05.py').read_text(encoding='utf-8')
pounce=pounce.replace("OUT=BASE/'PounceV05_20261004'","OUT=BASE/'MotionV09_20261005'")
pounce=pounce.replace("SOURCE=BASE/'BoneheadV04_20261004/M08_Bonehead_Animated_V04.blend'", "SOURCE=BASE/'MotionV09_20261005/M08_AirCannon_MotionV09.blend'")
pounce=pounce.replace("for role in ('AttackPounce','TraverseJump'):","clear_mouth=prepare_mouth(globals())\nfor role in ('AttackPounce',):")
pounce=pounce.replace("+'_PounceV05'","+'_MotionV09'").replace('M08_Pounce_Animated_V05.blend','M08_Attacks_MotionV09.blend')
# Load remains 0.24 s; a sharper launch unfolds front-to-back. Retain the
# .24/.74 source-time anchors consumed by path, prediction and hit windows.
pounce=pounce.replace('(.16,-.105)', '(.16,-.080)').replace('(.81,-.105)', '(.81,-.080)')
pounce=pounce.replace('(.30,-.22),(.46,-.09),(.60,.14)', '(.31,-.25),(.44,-.07),(.58,.16)')
pounce=pounce.replace("[('spine_01',.035,.28),('spine_02',.018,.32),('chest',0,.40)]", "[('spine_01',.055,.28),('spine_02',.028,.32),('chest',0,.40)]")
pounce=pounce.replace('(.32,.085),(.47,.045)', '(.30,.105),(.46,.035)')
pounce=pounce.replace("        jaw=curve(t,", "        if t<.24 or t>=.74:clear_mouth(local)\n        jaw=curve(t,")
# Jaw participates in the mouth envelope, so solve the clamp after its angle.
pounce=pounce.replace("        if t<.24 or t>=.74:clear_mouth(local)\n",'')
pounce=pounce.replace("        turn(local,'jaw',math.radians(jaw))", "        turn(local,'jaw',math.radians(jaw))\n        if t<.24 or t>=.74:clear_mouth(local)")
pounce=pounce.replace("delay=0 if side=='L' else .028", "delay=0 if side=='L' else .036")
pounce=pounce.replace('(.33,-.215),(.46,-.075)', '(.31,-.235),(.44,-.060)')
pounce=pounce.replace('(.32,.16),(.48,-.24)', '(.34,.18),(.50,-.26)')
ns={'__name__':'__m08_pounce_v09__','prepare_mouth':prepare_mouth}
exec(compile(pounce,'<M08 V09 pounce authoring>','exec'),ns)
clips.update(ns['report']['clips'])
report={'revision':'M08_MotionV09_20261005','mesh_asset':ns['prior']['mesh_asset'],'clips':clips,
    'authoring_source':str(OUTPUT/'M08_Attacks_MotionV09.blend'),'mouth_binding':str(OUTPUT/'mouth_binding.json'),
    'air_crouch_cm':5.5,'air_source_release':.92,'source_takeoff':.24,'source_landing':.74,
    'pounce_flight_speed_multiplier':3.,'runtime_tested':False,'preview_rendered':False,
    'provenance':'Own local animation revision of retained M08 rig; original mesh and skin weights unchanged.'}
(OUTPUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_MOTION_V09_AUTHORING_SAVED',flush=True)
