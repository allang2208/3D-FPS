import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import *
R=P/'SourceAssets/GarmentFoundation20260929';c=read(P/'Content/ColdSteelData/modular_outfits.json')
paths={k:c['items'][k]['rig_meshes']['M4'] for k in ['ue_chainmail_shirt','ue_field_sweater','ue_field_sweater_charcoal']}
native,profile=next((k,v) for k,v in c['profiles'].items() if v['rig_profile']=='M4');paths['bare']=profile['native_bare_skin']
for key,path in paths.items():write(R/(key+'.json'),source_snapshot(u.load_asset(path))[1])
write(R/'sources.json',paths)
