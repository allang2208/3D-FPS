"""Rebuild only the treasure connector with the room-owned portal reveal contract."""
import copy
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parent/'DungeonTreasure20260922'
config=json.loads((source/'Config/rooms.json').read_text(encoding='utf-8'))
config['rooms']=[];config['links']=[copy.deepcopy(x) for x in config['links'] if x['id']=='TreasureLink']
for folder in ('Config','Authored','Sources','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
(ROOT/'Config/rooms.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
lib=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
exec(compile(lib.read_text(encoding='utf-8'),str(lib),'exec'),{'__file__':str(lib),'__name__':'__main__'})
