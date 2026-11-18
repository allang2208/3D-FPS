"""Import the owned furniture and loft revisions through the existing editor batch mutex."""
import runpy,json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
SCRIPTS=ROOT/'Tools/WorldGeneration/VillageBlacksmith'
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; exit play before asset writes')
for revision in ('ArtPassR2','LoftR3'):
    receipt=OUT/revision/'assets-saved.json'
    data=json.loads(receipt.read_text()) if receipt.exists() else {}
    saved=data.get('meshes',data.get('saved',[]))
    if len(saved)==9 and all(u.EditorAssetLibrary.does_asset_exist(r['path']) for r in saved):continue
    runpy.run_path(str(SCRIPTS/revision/'import_assets.py'),run_name='__main__')
u.log('BLACKSMITH_R2_R3_ASSETS_INSTALLED')
