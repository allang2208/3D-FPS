import os,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
runpy.run_path(str(ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'),run_name='__main__')
