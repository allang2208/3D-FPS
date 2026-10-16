import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'inputs.json').read_text())
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
state={key:{'loaded':bool(u.find_object(None,row['path']+'.'+row['path'].rsplit('/',1)[1])),'dirty':row['path'] in dirty} for key,row in C['assets'].items()}
(O/'editor_asset_state.json').write_text(json.dumps(state,indent=2))
print(json.dumps(state))
