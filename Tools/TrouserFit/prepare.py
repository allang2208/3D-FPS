"""Inspect every active Jason trouser path; tailor only the oversized authored waists.

The original family JSONs remain immutable production inputs. This entry is the
current waist finishing stage, after the original family/cuff authoring stages.
"""
import json,sys,copy,hashlib
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TrouserFit20261018'
sys.path.insert(0,str(P/'Tools/SmokeGreyCapri'));import waist_fit as field
REV='TrouserNativeWaist20261018'
NATIVE='/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004/SK_Jason_Base.SK_Jason_Base'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def source_for(item,path):
    stem=path.split('.')[-1].removeprefix('SK_')
    if item=='ue_st6_tactical_pants':return P/'SourceAssets/ST6LowerSet20261018'/(stem+'.json')
    if item=='ue_smoke_grey_capri':return P/'SourceAssets/SmokeGreyCapri20261004'/('Jason_SmokeGreyCapri'+('_HighBootsFit' if 'HighBootsFit' in stem else '')+'.json')
    if item=='ue_leather_pants':return P/'SourceAssets/BrownLeatherSet20261004'/(stem+'.json')
    if item=='ue_chainmail_pants':return P/'SourceAssets'/('ArmoredBoots20261004' if 'ArmoredBootsFit' in stem else 'ChainmailPants20261004/ArmorRefineV2')/(stem+'.json')
    folder='ArmoredBoots20261004' if 'ArmoredBootsFit' in stem else 'BootsEquipment20261004' if 'BootsFit' in stem else 'LowerBodyEquipment20261003'
    return P/'SourceAssets'/folder/('jeans_fitted.json' if item=='ue_jeans' else 'cargo_fitted.json')
def shell_points(d):
    points=np.array(d['positions']);parts=[p for p in d.get('parts',[]) if 'WaistAndSeat' in p['name'] or 'ContinuousWaistSeatAndLegs' in p['name']]
    return np.concatenate([points[p['first_vertex']:p['first_vertex']+p['vertices']] for p in parts]) if parts else points
def metrics(d):
    v=shell_points(d);out={}
    for label,a,b in [('upper_hip',86,90),('lower_waist',90,94),('waist_transition',94,97),('waist_opening',97,101)]:
        q=v[(v[:,2]>=a)&(v[:,2]<b)];_,cy=field.sample(q[:,2],np.zeros(len(q)));theta=np.arctan2(q[:,0],q[:,1]-cy);radius,_=field.sample(q[:,2],theta)
        gap=np.hypot(q[:,0],q[:,1]-cy)-radius
        out[label]=dict(samples=len(q),radial_gap_cm=dict(zip(['min','p10','median','p90','max'],np.percentile(gap,[0,10,50,90,100]).round(5).tolist())))
    return out
def warp(points,ease=.55,lining=False):
    q=np.asarray(points,float);z=q[:,2];t=np.arctan2(q[:,0],q[:,1]-.8);radius,cy=field.sample(z,t)
    if lining:
        # Match the outer shell at the rolled lip; turn inward underneath it.
        # Keep the original radial degree of freedom so normals have a full
        # invertible deformation gradient rather than a surface projection.
        inset=np.interp(z,[97,98.7,99.85,100.08,100.2],[.3,.3,.28,.18,0])
        old=1/np.sqrt((np.sin(t)/17.1)**2+(np.cos(t)/12.7)**2)-inset
        r=np.hypot(q[:,0],q[:,1]-.8)+radius+ease-np.minimum(inset,ease-.28)-old
        return np.column_stack((r*np.sin(t),cy+r*np.cos(t),z))
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1]);ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])
    old=1/np.sqrt((np.sin(t)/rx)**2+(np.cos(t)/ry)**2);blend=np.clip((z-85)/11,0,1);blend=blend*blend*(3-2*blend)
    out=q.copy();out[:,0]+=(radius+ease-old)*np.sin(t)*blend;out[:,1]+=((radius+ease-old)*np.cos(t)+cy-.8)*blend
    return out
def jacobian(q,ease,lining=False):
    out=np.empty((len(q),3,3));eps=.002
    for a in range(3):
        delta=np.zeros(3);delta[a]=eps;out[:,:,a]=(warp(q+delta,ease,lining)-warp(q-delta,ease,lining))/(2*eps)
    return out
def repair(d,item):
    if REV in d.get('contract',''):return d
    original=np.array(d['positions']);q=original.copy();normals=np.array(d['normals']);faces=np.array(d['triangles']);ease=.7 if item=='ue_chainmail_pants' else .55;fi=0
    for part in d['parts']:
        first=part['first_vertex'];last=first+part['vertices'];end=fi+part['triangles'];v=original[first:last];name=part['name']
        if v[:,2].max()<=85:fi=end;continue
        rigid=any(s in name.lower() for s in ('rivet','buckle','clasp','latch'))
        if rigid:
            center=v.mean(0);j=jacobian(center[None,:],ease)[0];u,_,vh=np.linalg.svd(j);rot=u@vh
            q[first:last]=(v-center)@rot.T+warp(center[None,:],ease)[0];normals[fi:end]=normals[fi:end]@rot.T
        else:
            lining=name=='Lining_Waist';q[first:last]=warp(v,ease,lining);j=jacobian(v,ease,lining)
            nmat=np.transpose(np.linalg.inv(j),(0,2,1));normals[fi:end]=np.einsum('fcij,fcj->fci',nmat[faces[fi:end]-first],normals[fi:end])
        fi=end
    normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-12)
    d['positions']=q.tolist();d['normals']=normals.tolist();d['source']=NATIVE
    d['contract']=d.get('contract','')+'; '+REV+': native asymmetric waist, blended above 85cm; fitted facing; rigid closures; original UV/weights/cuffs'
    return d
def main():
    R.mkdir(parents=True,exist_ok=True);config=read(P/'Content/ColdSteelData/modular_outfits.json');manifest=[]
    for item,recipe in config['items'].items():
        if recipe.get('slot')!=15:continue
        by_path={recipe['rig_meshes']['Jason']:['standard']}
        for shoe,rigs in recipe.get('shoe_fit_meshes',{}).items():by_path.setdefault(rigs['Jason'],[]).append(shoe)
        for asset,uses in by_path.items():
            source=source_for(item,asset);raw=source.read_bytes();data=json.loads(raw);before=metrics(data)
            row=dict(item=item,active_asset=asset,uses=uses,source=str(source),input_sha256=hashlib.sha256(raw).hexdigest(),before=before)
            if item in ('ue_leather_pants','ue_chainmail_pants'):
                target=R/(asset.split('.')[-1].removeprefix('SK_')+'.json');fixed=repair(copy.deepcopy(data),item)
                target.write_text(json.dumps(fixed,separators=(',',':')),encoding='utf-8');row.update(action='tailored',output=str(target),after=metrics(fixed))
                backup=R/'Inputs'/source.relative_to(P/'SourceAssets');backup.parent.mkdir(parents=True,exist_ok=True)
                if not backup.exists():backup.write_bytes(raw)
                old=np.array(data['positions']);new=np.array(fixed['positions']);low=old[:,2]<=85
                row['preserved']=dict(below_85cm=np.array_equal(old[low],new[low]),triangles=data['triangles']==fixed['triangles'],uv=data['uv']==fixed['uv'],weights=data['weights']==fixed['weights'])
            else:row['action']='retain_existing_fit'
            manifest.append(row);print(item,uses,row['action'],before['waist_opening']['radial_gap_cm'],flush=True)
    write(R/'fit_inventory.json',dict(native_reference=str(field.FIELD),method='Offline native cross-section radial clearance. Authored shells exclude armor/lining; imported garments retain folds. No runtime test.',paths=manifest))
if __name__=='__main__':main()
