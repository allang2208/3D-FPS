"""One authored motion mask for all layers; retain V2 geometry and weights."""
import json,math
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/ChainmailInterlace20260929'
R=P/'SourceAssets/ChainmailSharedSway20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def main():
    config_path=P/'Content/ColdSteelData/modular_outfits.json';config=read(config_path);recipe=config['items']['ue_chainmail_shirt']
    if recipe.get('appearance_family') not in ['ChainmailCloth20260929','ChainmailInterlace20260929','ChainmailSharedSway20260929']:
        raise RuntimeError('Chainmail appearance changed; preserve current recipe')
    if not (R/'before.json').exists():write(R/'before.json',dict(recipe=recipe))
    master=read(BASE/'Authored/M4.json');positions=np.asarray(master['positions']);colors=np.zeros((len(positions),4));colors[:,3]=1
    master_sides=np.where(positions[:,0]<0,0,1)
    for index,side in enumerate(['l','r']):
        wrist=np.asarray(master['bones']['hand_'+side]['position']);elbow=np.asarray(master['bones']['lowerarm_'+side]['position'])
        axis=(wrist-elbow)/np.linalg.norm(wrist-elbow);axial=(positions-wrist)@axis
        # V2 native cuff tip. Inner and outer surfaces at the same axial station
        # deliberately use the same value, independent of material or radius.
        mail_ids=np.unique(np.asarray([f for f,m in zip(master['triangles'],master['triangle_materials']) if m==0]))
        ids=mail_ids[(master_sides[mail_ids]==index)&(axial[mail_ids]>-10)&(axial[mail_ids]<0)]
        end=float(axial[ids].max())
        a=np.clip((axial-(end-5.5))/4.5,0,1);weight=a*a*(3-2*a)
        colors[:,index]=np.where(master_sides==index,weight,0)
    records=[]
    for old in read(BASE/'manifest.json'):
        name=old['profile']
        if name=='Body':continue
        target=read(BASE/'Authored'/(name+'.json'))
        sides={s for s in ['l','r'] if any(sum(v for k,v in w.items() if k.endswith('_'+s))>.7 for w in target['weights'])}
        keep=[i for i,p in enumerate(positions) if len(sides)==2 or (p[0]<0 if 'l' in sides else p[0]>0)]
        if len(keep)!=len(target['positions']):raise RuntimeError('Native V2 vertex order changed '+name)
        write(R/'Masks'/(name+'.json'),dict(profile=name,colors=colors[keep].tolist()))
        records.append(dict(profile=name,source=str(BASE/'Authored'/(name+'.json')),vertices=len(keep),triangles=len(target['triangles'])))
    write(R/'manifest.json',records)
    write(R/'production.json',dict(family=R.name,profiles=len(records),max_offset_cm=.12,
        shared_layers=['mail','lining','binding','links'],spring_states_per_double_arm_rig=2,
        cloth_particles=0,cloth_collisions=0,new_animations=0,geometry_preserved=True,runtime_tested=False))
    # Keep a stable V2 basis for both fresh production and later rebuilds. The
    # archived Chaos family is never an input to the current production chain.
    stable=read(BASE/'published.json')['recipe']
    interim=dict(recipe)
    interim.update(appearance_family=stable['appearance_family'],rig_meshes=stable['rig_meshes'],material=stable['material'])
    interim.pop('secondary_motion',None)
    write(R/'interim.json',dict(recipe=interim,reason='Ordinary V2 basis for shared-sway publication'))
    # Disable the rejected family only; do not roll back an active shared-sway
    # recipe merely because masks are being regenerated.
    if recipe.get('appearance_family')=='ChainmailCloth20260929':
        config['items']['ue_chainmail_shirt']=interim
        config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CHAINMAIL_SHARED_MASKS_AUTHORED',len(records),'profiles; stable V2 publication basis saved',flush=True)
if __name__=='__main__':main()
