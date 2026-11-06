"""Install only the two world-body sweep roles after native asset saves."""
import json
from pathlib import Path
import sys

P=Path(__file__).resolve().parent
root=P.parents[1]
sys.path.insert(0,str(root/'Tools/PlayerBody'))
from config_transaction import commit

saved=json.loads((P/'saved-body.json').read_text())
path=root/'Content/ColdSteelData/player_body.json'
before=path.read_bytes()
cfg=json.loads(before.decode('utf-8-sig'))
role='Melee.FullBody.HighlandBreakSweep'
cfg['clips'][role]=saved['Jason']
cfg['body_variants']['kaitlin']['clips'][role]=saved['Kaitlin']
receipt=commit(path,before,cfg,owned_paths=[('clips',role),('body_variants','kaitlin','clips',role)],
               producer='HighlandBroadbladeSweep20261104')
print(receipt['status'])
