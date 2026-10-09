import bpy,json,numpy as np
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V08/Authoring/FacelessSecurity_V08.blend'))
rig=bpy.data.objects['root'];out={'bones':{n:list(rig.matrix_world@rig.data.bones[n].head_local) for n in ['spine_03','spine_04','spine_05','clavicle_l','upperarm_l','lowerarm_l','hand_l','neck_01','neck_02']},'objects':{}}
for o in bpy.context.scene.objects:
    if o.type!='MESH' or not any(t in o.name for t in ['Shirt_Armholes','Collar','Epau','RankBar']):continue
    normals=np.array([n.vector for n in o.data.corner_normals]);dots=[];bad=[]
    for f in o.data.polygons:
        d=normals[list(f.loop_indices)]@np.array(f.normal);dots.extend(d)
        if min(d)<0:bad.append({'face':f.index,'center':list(f.center),'dot':float(min(d))})
    out['objects'][o.name]={'verts':len(o.data.vertices),'custom_normals':o.data.has_custom_normals,'negative_corners':int(np.sum(np.array(dots)<0)),
      'dot_quantiles':np.quantile(dots,[0,.01,.1,.5]).tolist(),'bad':bad[:5]}
shirt=bpy.data.objects['Security_Shirt_Armholes_V08'];v=shirt.data.vertices
out['cap_meridians']={str(i):[list(v[4774+k*72+i].co) for k in range(16)] for i in [0,18,36,54]}
(BASE/'V09/cap_normals_source.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2),flush=True)
