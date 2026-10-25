"""Freeze the two ST6 item routes and sources for an isolated detail revision."""
import json,hashlib,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024';OLD=P/'SourceAssets/ST6LowerSet20261018'
DEST='/Game/Characters/ModularOutfit20260924/ST6LowerDetail20261024'
KEYS=('ue_st6_tactical_pants','ue_st6_tactical_boots')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
for folder in ('Inputs','Authored','Textures','Exports','Logs','Before'):(R/folder).mkdir(parents=True,exist_ok=True)
if (R/'manifest.json').exists():
    print('ST6_DETAIL_REUSE_FROZEN_INPUTS',flush=True)
    raise SystemExit(0)
c=read(P/'Content/ColdSteelData/modular_outfits.json');inventory=[];mapping={}
for rig,items in [('Jason',c['items']),('Kaitlin',c['body_variants']['kaitlin']['items'])]:
    for key in KEYS:
        recipe=items[key];paths=[recipe['rig_meshes'][rig]]
        paths.extend(v[rig] for v in recipe.get('shoe_fit_meshes',{}).values())
        for path in dict.fromkeys(paths):
            name=path.rsplit('.',1)[-1];out=DEST+'/'+rig+'/'+name
            mapping[path]=out+'.'+name
            kind='boots' if key.endswith('boots') else 'pants'
            suffix=next((s for s in ('_ST6BootsFit','_ShortBootsFit','_HighBootsFit') if s in name),'')
            inventory.append(dict(source=path,target=mapping[path],rig=rig,kind=kind,suffix=suffix,detail=rig+'_'+kind+suffix+'.json'))
    under=items['ue_blue_mage_robe'].get('underlayer_meshes',{})
    for source,inner in under.items():
        if source not in mapping:continue
        name=inner.rsplit('.',1)[-1];out=DEST+'/UnderRobe/'+rig+'/'+name
        mapping[inner]=out+'.'+name
        inventory.append(dict(source=inner,target=mapping[inner],rig=rig,kind='underrobe',detail=None))
source_files=['Jason_ST6Trousers_Garment.json','Jason_ST6Boots_Garment.json','Jason_ST6Trousers.json','Jason_ST6Trousers_ShortBootsFit.json','Jason_ST6Trousers_HighBootsFit.json','Jason_ST6Trousers_ST6BootsFit.json','Jason_ST6Boots.json','native_reference.json','boot_profile.json']
hashes={}
for name in source_files:
    src=OLD/name;shutil.copy2(src,R/'Inputs'/name);hashes[str(src)]=hashlib.sha256(src.read_bytes()).hexdigest()
for name in ('items.json','modular_outfits.json'):
    shutil.copy2(P/'Content/ColdSteelData'/name,R/'Inputs'/name)
(R/'manifest.json').write_text(json.dumps(dict(destination=DEST,items=KEYS,meshes=inventory,path_map=mapping,source_sha256=hashes,interfaces='existing waist, hem and shaft envelopes retained; details append to the current meshes'),indent=2),encoding='utf-8')
print('ST6_DETAIL_INPUTS_PREPARED',len(inventory),flush=True)
