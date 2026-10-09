"""Finish animation derived-data work and save the delivered V03 assets."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V03')
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
assets=[u.load_asset(path) for path in report['saved']]
if any(asset is None for asset in assets):raise RuntimeError('A V03 asset could not be loaded for final save')
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
for asset in assets:
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Could not finalize '+asset.get_path_name())
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
report['initial_commandlet_exit_code']=3
report['initial_exit_error']='After package saves: animation derived-data task still in flight during shutdown'
report['animation_compilation_finished']=True
report['finalization_stage']='saved'
(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESEARCHER_WAIST_V03_FINALIZED '+json.dumps({'saved':len(assets),'runtime_tested':False}),flush=True)
