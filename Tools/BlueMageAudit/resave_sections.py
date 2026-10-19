"""Persist UE's loaded section-index normalization for the audited mage assets."""
import json,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageSetAudit20261019';before=json.loads((R/'saved-render-audit.json').read_text());done=[];references=[]
for path in before['meshes']:
    if not path.startswith('/Game/Characters/ModularOutfit20260924/BlueMage'):
        references.append(path);continue
    mesh=u.load_asset(path)
    # PostLoad has already remapped old OriginalDataSectionIndex/UserSectionsData.
    # Save those corrections without rebuilding topology or changing clothing.
    if not mesh or not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save normalized sections '+path)
    done.append(path);print('MAGE_SECTIONS_SAVED',path.rsplit('/',1)[-1],flush=True);del mesh;gc.collect();u.SystemLibrary.collect_garbage()
(R/'sections-resaved.json').write_text(json.dumps(dict(completed=True,assets=done,reference_assets_read_only=references),indent=2),encoding='utf-8')
