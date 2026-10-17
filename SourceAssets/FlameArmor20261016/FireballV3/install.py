import sys
import importlib
sys.path.insert(0, 'D:/FPS3D/FPSGAME/Tools/Fluids')
import author_flame_armor_fireball_v3 as author
importlib.reload(author)
for stage in ('materials', 'body', 'weapon', 'arrow'):
    author.run(stage)
