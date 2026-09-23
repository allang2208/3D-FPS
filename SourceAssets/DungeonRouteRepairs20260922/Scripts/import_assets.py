from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT.parent/'DungeonRoomShells20260922/Scripts/import_rooms.py'
source=script.read_text(encoding='utf-8').replace("ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/RoomShells20260922'",f"ROOT=Path({str(ROOT)!r});BASE='/Game/Dungeons/RouteRepairs20260922'")
exec(compile(source,str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
