"""Deferred editor import; run only through the existing project MCP batch bridge."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
materials=ROOT/'Scripts/import_materials.py'
exec(compile(materials.read_text(encoding='utf-8'),str(materials),'exec'),dict(__file__=str(materials),__name__='__main__'))
source=ROOT.parent/'DungeonRoomShells20260922/Scripts/import_rooms.py'
code=source.read_text(encoding='utf-8').replace("BASE='/Game/Dungeons/RoomShells20260922'","BASE='/Game/Dungeons/BossHall20260922'")
exec(compile(code,str(source),'exec'),dict(__file__=__file__,__name__='__main__',ROOM_IDS=['BossPumpHall']))
