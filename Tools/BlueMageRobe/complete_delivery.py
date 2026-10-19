"""Publish the saved garment and mark its source production stage accurately."""
import json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018'
runpy.run_path(str(P/'Tools/BlueMageRobe/publish.py'),run_name='__main__')
file=R/'Design/design-brief-v01.json';brief=json.loads(file.read_text(encoding='utf-8'));brief.update(stage='model_assets_saved_and_catalog_published',model_built=True,engine_imported=True,cloth_assets_bound=True,cloth_simulated=False,runtime_tested=False);file.write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLUE_ROBE_DELIVERY_SAVED_RUNTIME_ACCEPTANCE_USER_SIDE')
