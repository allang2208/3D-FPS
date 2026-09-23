"""Import this batch with the existing pipeline; never rebuild accepted rooms."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parent/'DungeonRoomShells20260922/Scripts/import_rooms.py'
code=source.read_text(encoding='utf-8').replace("BASE='/Game/Dungeons/RoomShells20260922'","BASE='/Game/Dungeons/VentFreight20260922'")
exec(compile(code,str(source),'exec'),dict(__file__=__file__,__name__='__main__',ROOM_IDS=globals().get('ROOM_IDS')))
