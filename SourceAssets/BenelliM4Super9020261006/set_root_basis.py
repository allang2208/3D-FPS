import json
from pathlib import Path
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006')
f=O/'author_super90.py';t=f.read_text(encoding='utf-8-sig');anchor='# Preserve source UVs, surface slots and exact mechanical weights in normalized centimetre export.'
t=t.replace(anchor,"# Give the semantic gun root a physical up axis without changing its deformation.\nold_main=rest['WPN_root'].copy();rest['WPN_root']=Matrix.Translation(old_main.translation)\nfor rows in rawclips.values():\n for row in rows:row['WPN_root']=row['WPN_root']@old_main.inverted()@rest['WPN_root']\n"+anchor)
t=t.replace('# Author sockets are measured in the original FBX\'s complete gun surface frame.','# Author socket positions are defined in the original FBX complete gun surface frame.')
f.write_text(t,encoding='utf8')
