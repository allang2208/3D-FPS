import sys,json
from pathlib import Path
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/ModularOutfit')
import garment_ue as g
import unreal as u
u.SystemLibrary.execute_console_command(None,'r.FreeSkeletalMeshBuffers 0')
r=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929')
c=json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
native,profile=next((k,v) for k,v in c['profiles'].items() if v['rig_profile']=='SVD')
paths={}
for key,v in c['items'].items():
 for family in ['rig_meshes','skin_meshes']:
  if v.get(family,{}).get('SVD'):paths[key+'_'+family]=v[family]['SVD']
(r/'paths.json').write_text(json.dumps({'paths':paths,'profile':profile},indent=2))
for key,path in paths.items():
 a=u.load_asset(path)
 for lod in range(u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(a)):
  g.write(r/(key+'_LOD'+str(lod)+'.json'),g.snapshot(a,lod))
  print('SNAPSHOT',key,lod,flush=True)
