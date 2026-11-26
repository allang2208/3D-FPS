from pathlib import Path
import json,runpy
P=Path('D:/FPS3D/FPSGAME')
revision=P/'SourceAssets/ChapelNun20261115/BootFinishR8/saved_assets.json'
if revision.exists() and json.loads(revision.read_text(encoding='utf-8-sig')).get('completed'):
    # A later character reimport must retain the currently published boot finish.
    runpy.run_path(str(P/'Tools/ChapelNun/save_boot_finish_r8.py'))
else:
    R=P/'SourceAssets/ChapelNun20261115/RefinementR4'
    d=json.loads((R/'Inputs/current_boots.json').read_text(encoding='utf-8-sig'))
    state={'SURFACE_FILE':'boots.json','SURFACE_NAME':'SK_Nun_Boots','SURFACE_MATS':[m['asset'] for m in d['materials']]+['/Game/Characters/ChapelNun20261115/RefinementR4/Materials/M_Nun_BlackStockings']}
    p=P/'Tools/ChapelNun/save_final_collar.py';exec(compile(p.read_text(),str(p),'exec'),state)
