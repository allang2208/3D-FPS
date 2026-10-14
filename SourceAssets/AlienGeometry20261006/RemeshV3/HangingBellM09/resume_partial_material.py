"""Finish the one material created by this batch before its naming error."""
import sys,importlib,json
from pathlib import Path
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/MonsterAI')
import install_meshy_remesh_v3 as p
importlib.reload(p)
out=p.ROOT/'HangingBellM09'
report=json.loads((out/'installation.json').read_text(encoding='utf8'))
textures={role:p.load(p.DEST+'/HangingBellM09/Textures/T_HangingBellM09_'+role) for role in ('BaseColor','MetallicRoughness','Normal')}
p.new_material(p.load('/Game/Monsters/HangingBellM09/V04/Materials/M_M09_Body'),textures,p.DEST+'/HangingBellM09/Materials',report)
p.write(out/'installation.json',report)
p.run('HangingBellM09','import')
