from pathlib import Path
p=Path('Tools/HangingBellM09/author_room_v04.py');s=p.read_text(encoding='utf8')
old="""if not u.HangingBellM09.build_physics(mesh,pa):raise RuntimeError('M09 anatomy physics authoring failed')
for asset in [pa,mesh]:
 if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Physics save failed '+asset.get_path_name())"""
new="""if not globals().get('M09_ROOM_ONLY',False):
 if not u.HangingBellM09.build_physics(mesh,pa):raise RuntimeError('M09 anatomy physics authoring failed')
 for asset in [pa,mesh]:
  if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Physics save failed '+asset.get_path_name())"""
s=s.replace(old,new).replace("'auto_spawned_monsters':0","'auto_spawned_monsters':0,'anatomy_physics_saved':not globals().get('M09_ROOM_ONLY',False)")
p.write_text(s,encoding='utf8')
Path('Tools/HangingBellM09/author_room_only_v04.py').write_text("M09_ROOM_ONLY=True\nexec(compile(open('D:/FPS3D/FPSGAME/Tools/HangingBellM09/author_room_v04.py',encoding='utf8').read(),'author_room_v04.py','exec'))\n",encoding='utf8')
