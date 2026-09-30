import bpy,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
src=(O/'inspect_front.py').read_text()
src=src.replace("S/'ReferenceRepair38/LMG201_ReferenceRepair38.blend'","O/'LMG201_HardSurface39.blend'")
src=src.replace("keep=['Barrel'","keep=['BipodBase_H39','Barrel'")
src=src.replace("O/(ob.name+'.npz')","O/(ob.name+'_after.npz')")
src=src.replace('xf=root.inverted()@ob.matrix_world','xf=ob.matrix_world if ob.name==\'BipodBase_H39\' else root.inverted()@ob.matrix_world')
src=src.split("shot('front_ownership'")[0]
exec(compile(src,str(O/'inspect_after.py'),'exec'),globals())
# Add unchanged leg sources at the exact existing C++ component pivots.
for key,pivot in [('BipodLegA',(.01356,-.46498,-.01398)),('BipodLegB',(-.01196,-.46498,-.01398))]:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False)
 ob=next(q for q in bpy.data.objects if q not in old and q.type=='MESH');ob.location+=Vector(pivot)
 for q in list(bpy.data.objects):
  if q not in old and q.name.startswith(('UCX_','UBX_','USP_','UCP_')):bpy.data.objects.remove(q,do_unlink=True)
shade.color_type='SINGLE';shade.single_color=(.35,.36,.39)
shot('front_after',(1,-.5,.13),(0,-.5,-.045),.43)
shot('front_under_after',(1,-.5,-.27),(0,-.5,.022),.33)
shot('receiver_after',(-.5,-.16,.17),(0,-.14,.043),.31)
shot('receiver_other_after',(1,-.06,.23),(0,-.10,.04),.32)
