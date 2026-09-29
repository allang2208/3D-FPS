import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import *
R=P/'SourceAssets/GarmentFoundation20260929';lib=read(R/'library.json');c=read(P/'Content/ColdSteelData/modular_outfits.json');receipts={}
for profile,template in [('M16','chainmail'),('ASH12','cotton_short')]:
 native=next(k for k,v in c['profiles'].items() if v['rig_profile']==profile)
 receipt=derive_bound(lib['templates'][template]['asset'],native,'/Game/Characters/ModularOutfit20260924/GarmentFoundation20260929/NativeProbe/SK_'+profile+'_'+template,R/'NativeProbe'/profile)
 receipts[profile]=receipt;write(R/'native-probe-saved.json',receipts);print('NATIVE_CANDIDATE_SAVED',profile,flush=True)
