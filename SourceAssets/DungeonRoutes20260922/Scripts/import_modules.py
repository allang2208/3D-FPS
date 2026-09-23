from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parent/'DungeonRoomShells20260922/Scripts/import_rooms.py'
code=source.read_text(encoding='utf-8').replace("BASE='/Game/Dungeons/RoomShells20260922'","BASE='/Game/Dungeons/Routes20260922'")
exec(compile(code,str(source),'exec'),globals())
