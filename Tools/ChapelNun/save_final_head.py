"""Write the original neck continuation and rebuild existing owned groom bindings."""
from pathlib import Path
original='/Game/Characters/ChapelNun20261115/OriginalMeshyFaceR3/Materials/M_Nun_OriginalMeshy'
state={'SURFACE_FILE':'head.json','SURFACE_NAME':'SK_Nun_OriginalMeshyFace_Final','SURFACE_MATS':[original]*3}
script=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_final_collar.py')
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),state)
u=state['u'];save=state['save'];load=state['load'];DEST=state['DEST']
for part in ('Core','Loose'):
 binding=load(DEST+'/Grooms/Nun_LowBun_'+part+'_Final_Binding')
 binding.build(u.OnGroomBindingAssetBuildComplete());save(binding)
print('ORIGINAL_NECK_AND_BINDINGS_SAVED',flush=True)
