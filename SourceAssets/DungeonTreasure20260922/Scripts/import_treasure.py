from pathlib import Path
source=Path(__file__).resolve().parents[2]/'DungeonRoomShells20260922/Scripts/import_rooms.py'
code=source.read_text(encoding='utf-8').replace("BASE='/Game/Dungeons/RoomShells20260922'","BASE='/Game/Dungeons/Treasure20260922'")
exec(compile(code,str(source),'exec'),globals())
