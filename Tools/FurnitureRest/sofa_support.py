"""Three scoped sofa clips: staggered hand placement, planted support and release."""
from pathlib import Path
import json,math
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
ROOT=Path(__file__).resolve().parents[2]
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,rot,ik,handrot,ease,ix,bind=[ns[n] for n in ('fk','rot','ik','handrot','ease','ix','bind')]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/SofaSupportV3';OUT.mkdir(parents=True,exist_ok=True)
base=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/RefineV2/authored.json').read_text())
config=json.loads((ROOT/'Content/ColdSteelData/furniture_rest.json').read_text(encoding='utf-8'))
result={k:base[k] for k in ('mesh','skeleton','names','parents','reference')};result['clips']={}
rest_world=fk(np.array(base['clips']['Rest.Sofa.Idle']['frames'][0]));contact_errors=[]
for kind,outer in [('Sofa',None),('SofaLeft','r'),('SofaRight','l')]:
 for phase in ('Enter','Idle','Exit'):
  role='Rest.'+kind+'.'+phase;take=base['clips']['Rest.Sofa.'+phase];frames=[];cameras=[]
  for j,original in enumerate(take['frames']):
   t=j/30;f=np.array(original);old=fk(f)
   body=float(ease((t-.25)/1.05)) if phase=='Enter' else 1. if phase=='Idle' else float(1-ease((t-.65)/1.15))
   # A supported recline compresses through the lumbar/thoracic chain. The
   # original pelvis, legs and planted feet remain bit-for-bit unchanged.
   for bone,factor in [('spine_01',.35),('spine_02',.7),('spine_03',1),('spine_04',1),('spine_05',1),('neck_01',.45),('neck_02',.3),('head',.15)]:
    if bone in ix:
     target=R.from_euler('x',32*factor,degrees=True).as_matrix()@(old if phase=='Idle' else rest_world)[ix[bone],:3,:3]
     q=Slerp([0,1],R.from_matrix(np.array([old[ix[bone],:3,:3],target])))(body).as_matrix()
     rot(f,ix[bone],q)
   for side,sign in [('l',1),('r',-1)]:
    contact=float(ease((t-(.3 if side=='l' else .45))/1.12)) if phase=='Enter' else 1. if phase=='Idle' else float(1-ease((t-(.65 if side=='l' else .5))/.85))
    w=fk(f);cl=ix['clavicle_'+side]
    rot(f,cl,R.from_euler('y',sign*7*body,degrees=True).as_matrix()@w[cl,:3,:3])
    target=np.array([sign*(37 if side==outer else 24),-18 if side=='l' else -15,91.8 if side==outer else 69.1])
    hand=old[ix['hand_'+side],:3,3]*(1-contact)+target*contact
    hand+=np.array([sign*9,0,12])*math.sin(math.pi*contact)
    pole=fk(f)[ix['upperarm_'+side],:3,3]+np.array([sign*32,-7,-23])
    ik(f,side,('upperarm','lowerarm','hand'),hand,pole)
    if contact>.999:contact_errors.append(float(np.linalg.norm(fk(f)[ix['hand_'+side],:3,3]-target)))
    handrot(f,side,np.array([sign*.14,1.,-.04]),np.array([0.,0.,-1.]))
    q=fk(f)[ix['hand_'+side],:3,:3]
    q=Slerp([0,1],R.from_matrix(np.array([old[ix['hand_'+side],:3,:3],q])))(contact).as_matrix()
    rot(f,ix['hand_'+side],q)
    axis=np.array([1.,-sign*.14,0]);axis/=np.linalg.norm(axis)
    for digit in ('thumb','index','middle','ring','pinky'):
     bone=ix[digit+'_01_'+side];w=fk(f)
     angle=(30 if digit=='thumb' else 15)*contact
     rot(f,bone,R.from_rotvec(axis*math.radians(angle)).as_matrix()@w[bone,:3,:3])
   w=fk(f);head=w[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
   chest=w[ix['spine_03'],:3,3]-w[ix['pelvis'],:3,3];pitch=math.degrees(math.atan2(np.linalg.norm(chest[:2]),max(.01,chest[2])))
   forward=head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,1,0])
   cameras.append([*eye.tolist(),pitch*.72,math.degrees(math.atan2(-forward[0],forward[1]))]);frames.append(f.tolist())
  result['clips'][role]={'rate':30,'duration':take['duration'],'frames':frames}
  config['clips'][role]={'duration':take['duration'],'camera':cameras}
 config['types'][kind]=dict(config['types']['Sofa'])
for profile in config['furniture']:
 if profile['slots'][0]['kind']=='Sofa':
  for slot in profile['slots']:
   slot['kind']='SofaLeft' if slot['seat'][0]<0 else 'SofaRight' if slot['seat'][0]>0 else 'Sofa'
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
(OUT/'furniture_rest.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('SOFA_SUPPORT_AUTHORED',len(result['clips']))
print('MAX_PLANTED_WRIST_ERROR_CM',max(contact_errors))
