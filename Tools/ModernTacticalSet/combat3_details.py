"""Lower the native fitted yoke into a crew neckline and sew the settled cloth."""
import sys,copy,ast,numpy as np
from pathlib import Path
from mathutils import Vector,kdtree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,subset,merge,smooth_transport,unit
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3'
code=(P/'Tools/ModernTacticalSet/combat2_details.py').read_text(encoding='utf-8').replace('CombatShirtR2','CombatShirtR3');ns={'__file__':str(P/'Tools/ModernTacticalSet/combat2_details.py'),'__name__':'r3_sewing'};exec(compile(code,'r3_sewing','exec'),ns)
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
for rig in ['Jason','Kaitlin']:
    d=read(R/'Authored'/f'shirt_cloth_{rig}.json');ns['sew'](d);raw=read(S/'CombatShirtR2/Authored'/f'shirt_cloth_{rig}.json');p=np.array(raw['positions']);f=np.array(raw['triangles']);count=len(p)//2;f=f[(f<count).all(1)];edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1);edges,c=np.unique(edges,axis=0,return_counts=True);ids=np.unique(edges[c==1]);ids=ids[p[ids,2]>125];kd=kdtree.KDTree(len(ids))
    for i,vi in enumerate(ids):kd.insert(Vector(p[vi]),i)
    kd.balance();cfg=read(S/'CombatShirtR1/Inputs/modular_outfits.json');cfg=cfg if rig=='Jason' else cfg['body_variants']['kaitlin'];path=cfg['items']['ue_st6_sleeves']['owner_body_meshes'][rig];row=next(row for row in read(S/'CombatShirtR1/plan.json')['rows'] if row['source']==path);guide=read(S/'CombatShirtR1/Inputs'/row['file']);gp=np.array(guide['positions']);gf=np.array(guide['triangles']);guide=subset(guide,gp[gf,2].mean(1)>120);old=np.array(guide['positions']);new=old.copy();bones={b['name']:b for b in d['bones']};clav=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5;neck=np.array(bones['neck_01']['position']);top=float(old[:,2].max());main_drop=top-(clav+3.2);blend=np.array([smooth(kd.find(Vector(q))[2]/7.5) for q in old]);radial=old-neck;radial[:,2]=0;rr=np.linalg.norm(radial,axis=1);direction=radial/np.maximum(rr[:,None],1e-8);new[:,2]-=(main_drop+1.6*direction[:,1])*blend;new[:,:2]+=direction[:,:2]*(1.2*blend)[:,None]
    guide['positions']=new.tolist();smooth_transport(guide,old);guide['materials']=[DEST+'/Materials/M_CombatStretch',DEST+'/Materials/M_CombatCuff'];guide['material_slots']=['CombatNeckYoke','CombatCrewBinding'];guide['triangle_materials']=[1 if old[face,2].mean()>top-1.25 else 0 for face in guide['triangles']]
    guide_bones={b['name']:b['index'] for b in guide['bones']}
    for i,w in enumerate(blend):
        if w<=0:continue
        weights={bi:weight*(1-.78*w) for bi,weight in guide['weights'][i]};weights[guide_bones['spine_05']]=weights.get(guide_bones['spine_05'],0)+.62*w;weights[guide_bones['neck_01']]=weights.get(guide_bones['neck_01'],0)+.16*w;guide['weights'][i]=[[bi,value] for bi,value in sorted(weights.items(),key=lambda item:-item[1])[:8]];total=sum(value for _,value in guide['weights'][i]);guide['weights'][i]=[[bi,value/total] for bi,value in guide['weights'][i]]
    guide['uv']=[]
    for face,nn in zip(guide['triangles'],guide['normals']):
        axes=[axis for axis in range(3) if axis!=int(np.argmax(np.abs(np.mean(nn,0))))];guide['uv'].append((new[face][:,axes]/8).tolist())
    merge(d,guide);d['neckline']=dict(style='low crew',old_max_cm=top,new_max_cm=float(new[:,2].max()),front_drop_cm=main_drop+1.6,back_drop_cm=main_drop-1.6);write(R/'Authored'/f'shirt_detail_{rig}.json',d)
    native=read(R/'Inputs'/f'Body_{rig}.json');patch=subset(native,[m==3 and max(native['positions'][i][2] for i in face)>clav-7 for face,m in zip(native['triangles'],native['triangle_materials'])]);patch['materials']=[native['materials'][3]];patch['material_slots']=['NATIVE:'+native['materials'][3]];patch['triangle_materials']=[0]*len(patch['triangles']);write(R/'Authored'/f'neck_skin_{rig}.json',patch)
    print('LOW_CREW_NECK',rig,d['neckline'],flush=True)
