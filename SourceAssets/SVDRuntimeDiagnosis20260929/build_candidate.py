import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import *
R=P/'SourceAssets/SVDRuntimeDiagnosis20260929'
source=read(R/'paths.json')['paths']['ue_chainmail_shirt_rig_meshes'];asset=u.load_asset(source);dm,data=source_snapshot(asset)
receipt=save_candidate(dm,asset,'/Game/Characters/ModularOutfit20260924/SVDLODRepairCandidate20260929/SK_SVD_Chainmail',R/'candidate')
write(R/'candidate-receipt.json',receipt)
print('CANDIDATE_SAVED',receipt['asset'])
