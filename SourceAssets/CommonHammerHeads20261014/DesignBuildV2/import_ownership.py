"""Resolve package ownership before choosing the offline import path."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
paths=['/Game/Weapons/CommonHammerHeads20261014/DesignV2/'+r['mesh'] for r in rows]
paths+=['/Game/ColdSteelData/AttachmentIcons20260913/hammer_heads_'+r['id'] for r in rows]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
result=[{'package':p,'loaded':u.find_object(None,p) is not None or u.find_object(None,p+'.'+p.rsplit('/',1)[-1]) is not None,'dirty':p in dirty} for p in paths]
(P/'import_ownership.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
