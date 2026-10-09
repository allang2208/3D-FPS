"""Identify whether the existing shoulder defect originates before or after FBX import."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');OUT=BASE/'V09'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V08/Authoring/FacelessSecurity_V08.blend'))
rig=bpy.data.objects['root'];source_bones={b.name:np.array(rig.matrix_world@b.head_local) for b in rig.data.bones}
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='Security_CompleteBody']
positions=[];weights=[];labels=[];normals=[]
for o in objects:
    names={g.index:g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        positions.append(o.matrix_world@v.co);weights.append({names[g.group]:g.weight for g in v.groups});labels.append(o.name);normals.append(o.matrix_world.to_3x3()@v.normal)
positions=np.array(positions);tree=KDTree(len(positions))
for i,p in enumerate(positions):tree.insert(p,i)
tree.balance();report={}
for label,path in [('delivery',BASE/'V08/Delivery/SK_FacelessSecurity_V08.fbx'),('ue',OUT/'Inputs/UE_Active_V08.fbx')]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');common=[b for b in rig.data.bones if b.name in source_bones]
    a=np.array([rig.matrix_world@b.head_local for b in common]);b=np.array([source_bones[x.name] for x in common]);am=a.mean(axis=0);bm=b.mean(axis=0)
    u,s,vt=np.linalg.svd((a-am).T@(b-bm));rot=u@vt;scale=np.sum(s)/np.sum((a-am)**2)
    errors=[];werrors=[];by_name={};count=0;tris=0
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        tris+=sum(len(p.vertices)-2 for p in o.data.polygons);names={g.index:g.name for g in o.vertex_groups}
        for v in o.data.vertices:
            p=(np.array(o.matrix_world@v.co)-am)@rot*scale+bm
            _,i,d=tree.find(p);errors.append(d);w={names[g.group]:g.weight for g in v.groups};src=weights[i]
            wd=sum(abs(w.get(n,0)-src.get(n,0)) for n in set(w)|set(src));werrors.append(wd)
            r=by_name.setdefault(labels[i],{'count':0,'max_pos':0.,'max_weights':0.});r['count']+=1;r['max_pos']=max(r['max_pos'],d);r['max_weights']=max(r['max_weights'],wd)
    report[label]={'vertices':len(errors),'triangles':tris,'scale':float(scale),'rotation':rot.tolist(),'bone_error':float(np.max(np.linalg.norm((a-am)@rot*scale+bm-b,axis=1))),
      'position_error':{'max':max(errors),'p99':float(np.quantile(errors,.99))},'weights_error_p99':float(np.quantile(werrors,.99)),
      'objects':{n:r for n,r in by_name.items() if 'Shirt' in n or 'Cuff' in n or 'Body' in n or r['max_pos']>.001}}
(OUT/'export_geometry_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
