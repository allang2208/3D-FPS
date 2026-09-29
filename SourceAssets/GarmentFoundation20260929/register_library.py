import sys
from pathlib import Path
sys.path.insert(0,'Tools/ModularOutfit');from garment_pipeline import *
r=PROJECT/'SourceAssets/GarmentFoundation20260929';saved=read(r/'saved.json');templates={};structural={}
for name,key,kind in [('ue_chainmail_shirt','chainmail','long_thick'),('ue_field_sweater','knit','long_thick'),('ue_field_sweater_charcoal','cotton_short','short_fitted')]:
 receipt=saved[name]
 for lod,ref in receipt['snapshots'].items():
  issues=mesh_issues(read(ref['path']),{'max_rest_edge_cm':[4,6,6][int(lod)]});structural[name+':'+lod]=issues
  if issues:raise RuntimeError((name,lod,issues))
 templates[key]=dict(status='structural_baseline',kind=kind,asset=receipt['asset'],asset_sha256=receipt['asset_sha256'],source=str(r/name/'source.json'),snapshots=receipt['snapshots'],runtime_visual='pending',removed_shoulder_faces=240)
write(r/'library.json',dict(version=1,templates=templates,loose='Requires separate volume/motion authoring; no approved loose template',retired_sources=['ModularOutfit20260924 auto-filled shoulder closures','FittedSleevesV1 shoulder caps'],lod_policy='LOD0 max 4 cm; protected simplified LOD1/2 max 6 cm; actual motion still required'))
write(r/'structural-results.json',structural)
c=read(PROJECT/'Content/ColdSteelData/modular_outfits.json');native=next(k for k,v in c['profiles'].items() if v['rig_profile']=='M4');clips=read(PROJECT/'SourceAssets/ChainmailReloadFit20260929/sources.json')['M4']['clips']
for name,key,kind in [('ue_chainmail_shirt','chainmail','long_thick'),('ue_field_sweater','knit','long_thick'),('ue_field_sweater_charcoal','cotton_short','short_fitted')]:
 path=r/name/'candidate.json';init(path,kind,key,['M4'],name);m=read(path);candidate=dict(saved[name]);candidate['native_source']=native;m['candidates']['M4']=candidate;m['actions']['M4']['reload']=clips
 for group,kinds in [('idle_ads',['idle','aim','aim_fire']),('equip_inspect',['inspect'])]:
  m['actions']['M4'][group]=['/Game/Weapons/M4WrapGripFinal/A_M4_HK416_'+x for x in kinds if asset_file('/Game/Weapons/M4WrapGripFinal/A_M4_HK416_'+x).exists()]
 write(path,m)
print('FOUNDATION_LIBRARY',list(templates),'9 saved LODs pass structure; candidate runtime evidence pending')
