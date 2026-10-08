from pathlib import Path
import bpy, numpy as np
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BoundCongregate_RigV3.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data.action=bpy.data.actions['A_BoundCongregate_WalkV2'];bpy.context.scene.frame_set(13)
body=bpy.data.objects['BC_Flesh'];ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);ev.to_mesh_clear()
for name in ('BC_RightLining','BC_RightLining_SimulationProxy'):
    ob=bpy.data.objects[name];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    for i in (585,585+len(bpy.data.objects['BC_RightLining_SimulationProxy'].data.vertices)):
        if i>=len(mesh.vertices):continue
        p=mesh.vertices[i].co;hit,n,_,_=bvh.find_nearest(p)
        v=ob.data.vertices[i];q=np.zeros(4);q0=np.r_[v.co[:],1]
        for g in v.groups:
            bone=ob.vertex_groups[g.group].name;q+=g.weight*np.array(rig.pose.bones[bone].matrix@rig.data.bones[bone].matrix_local.inverted())@q0
        print('CLOTH_DETAIL',name,i,'gap',100*(p-hit).dot(n),'pose',p[:],'manual',q,'rest',v.co[:],'weights',[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups])
    ev.to_mesh_clear()
