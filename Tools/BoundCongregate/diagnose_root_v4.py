"""Compare authored and UE-exported root positions/skin weights at the real seam."""
from pathlib import Path
import bpy,bmesh,json,math,numpy as np
from mathutils.kdtree import KDTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'TentacleWhipV4'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TentacleWhipV3/BoundCongregate_TentacleV3.blend'))
reports={}
def inspect(label):
    data=[];summary=[]
    bone_frames={}
    for ob in bpy.context.scene.objects:
        if ob.type=='ARMATURE':
            for b in ob.data.bones:bone_frames[b.name]=[list(row) for row in ob.matrix_world@b.matrix_local]
    (OUT/(label+'_bones.json')).write_text(json.dumps(bone_frames))
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        points=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices])
        # Blender metres, broad shoulder centered on original (.377,.063,.220).
        near=(points[:,0]>.44)&(points[:,2]>1.59)&(points[:,2]<1.80)
        ids=np.flatnonzero(near)
        if not len(ids):continue
        weights=[]
        for i in ids:
            v=ob.data.vertices[int(i)]
            w={ob.vertex_groups[g.group].name:round(g.weight,7) for g in v.groups if g.weight>1e-6}
            weights.append(w)
            data.append({'object':ob.name,'id':int(i),'p':points[i].tolist(),'w':w})
        mat_counts={}
        for p in ob.data.polygons:
            if any(near[i] for i in p.vertices):
                n=ob.data.materials[p.material_index].name
                mat_counts[n]=mat_counts.get(n,0)+1
        seam=ob.data.attributes.get('BCRootJoin')
        summary.append({'object':ob.name,'vertices':len(ob.data.vertices),'near_root':len(ids),'materials':mat_counts,
            'root_group_count':sum(bool(x.value) for x in seam.data) if seam else None,
            'weight_names':sorted(set(n for w in weights for n in w))})
    (OUT/(label+'_root_vertices.json')).write_text(json.dumps(data))
    reports[label]=summary
    print(label,json.dumps(summary),flush=True)
inspect('source_v3')
print('actions',[(a.name,a.frame_range[:]) for a in bpy.data.actions],flush=True)
fbx=OUT/'UE_imported_V3.fbx'
if fbx.exists():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=False)
    inspect('import_v3')
(OUT/'root_diagnosis.json').write_text(json.dumps(reports,indent=2))
