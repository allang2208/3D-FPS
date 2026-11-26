import bpy,json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/ChapelNun20261115/HeadQualityR2/Authored'
sys.path.insert(0,str(P/'Tools/ChapelNun'))
from lip_continuity import refine
old=json.loads((P/'SourceAssets/ChapelNun20261115/ProductionR1/Authored/head.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
me=bpy.data.objects['SK_NunHead'].data;count=refine(me,old);me.calc_loop_triangles()
d=json.loads((O/'head.json').read_text());d['positions']=[list(v.co) for v in me.vertices];d['normals']=[]
for t in me.loop_triangles:d['normals'].append([list(me.corner_normals[k].vector) for k in list(t.loops)[::-1]])
(O/'head.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
print('COINCIDENT_LIP_VERTICES_REFINED',count,flush=True)
