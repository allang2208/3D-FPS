from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/CyberpunkApartmentPlayable20261021')
MAP = '/Game/GameMaps/L_CyberpunkApartment'
DEST = '/Game/Props/CyberpunkApartmentPlayable20261021'
SCALE = 1.25
COMPLEX = {
    'S_plate', 'S_walls', 'S_ceiling', 'S_facade', 'S_glazing', 'S_doors',
    'S_balcony', 'S_trim', 'S_entry_landing', 'LIV_furniture',
    'KIT_run', 'KIT_dining', 'B2_room', 'B3_room', 'MST_room',
    'BA1_room', 'BA2_room', 'UTL_room', 'FOY_room', 'BAL_furniture',
}
# Thin finish, pipes, decals, cloth, foliage and small table clutter do not
# become player blockers. Walls/furniture retain their real shape, never a
# convex hull enclosing an entire room. Floors and railing use authored boxes.
ROOMS = {
    'foyer': (876,1128,-1088,-684), 'living': (396,1128,-540,-12),
    'master': (12,384,-540,-12), 'bed2': (1140,1588,-540,-12),
    'bed3': (1140,1588,-1088,-552), 'corridor': (12,1128,-672,-552),
    'utility_west': (12,272,-808,-684), 'utility_east': (284,468,-808,-684),
    'bath2': (12,272,-1088,-820), 'bath1': (284,468,-1088,-820),
    'kitchen': (480,864,-1088,-684), 'balcony': (406,1122,0,270),
    'entry_landing': (850,1134,-1360,-1090),
}
SPAWN_XY = (992, 1000)  # Blender positive Y; UE negates Y.
