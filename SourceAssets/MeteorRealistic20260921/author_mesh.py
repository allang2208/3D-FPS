import sys,importlib
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
import build_meteor_realistic
importlib.reload(build_meteor_realistic)
build_meteor_realistic.run('mesh')
