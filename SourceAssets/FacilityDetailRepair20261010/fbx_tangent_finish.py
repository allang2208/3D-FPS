"""Repair zero angle-weighted corner tangents when writing this task's FBXs.

The fallback is the double-precision UV derivative projected into the authored
corner normal. It only handles zero vectors; ordinary MikkTSpace corners retain
their original basis. Blender's installed exporter is never edited.
"""
import inspect,numpy as np
def repair(mesh,flat,bitangent):
    array=flat.reshape(-1,3);bad=np.linalg.norm(array.astype(np.float64),axis=1)<1.e-6
    if not bad.any():return
    verts=np.empty(len(mesh.vertices)*3,dtype=np.float64);mesh.vertices.foreach_get('co',verts);verts=verts.reshape(-1,3)
    uv=mesh.uv_layers.active
    for face in mesh.polygons:
        indices=list(face.loop_indices)
        if len(indices)!=3 or not any(bad[i] for i in indices):continue
        p=[verts[mesh.loops[i].vertex_index] for i in indices];q=[np.array(uv.data[i].uv,dtype=np.float64) for i in indices]
        e1,e2=p[1]-p[0],p[2]-p[0];d1,d2=q[1]-q[0],q[2]-q[0];det=d1[0]*d2[1]-d1[1]*d2[0]
        if abs(det)<1.e-15:raise RuntimeError('Unresolved equipment UV '+mesh.name)
        tangent=(e1*d2[1]-e2*d1[1])/det;bi=(e2*d1[0]-e1*d2[0])/det
        for i in indices:
            if not bad[i]:continue
            normal=np.array(mesh.corner_normals[i].vector,dtype=np.float64);normal/=np.linalg.norm(normal)
            t=tangent-normal*np.dot(tangent,normal);t/=np.linalg.norm(t)
            b=np.cross(normal,t)
            if np.dot(b,bi)<0:b=-b
            array[i]=b if bitangent else t
    print('FBX_UV_DERIVATIVE_FALLBACK',mesh.name,'binormals' if bitangent else 'tangents',int(bad.sum()),flush=True)
def install():
    from io_scene_fbx import export_fbx_bin as exporter
    if hasattr(exporter,'_facility_tangent_repair'):return
    exporter._facility_tangent_repair=repair
    source=inspect.getsource(exporter.fbx_data_mesh_elements)
    for field,flag in (('bitangent','True'),('tangent','False')):
        line='me.loops.foreach_get("'+field+'", t_ln)'
        source=source.replace(line,line+'\n                        _facility_tangent_repair(me, t_ln, '+flag+')')
    exec(compile(source,'facility_fbx_tangent_export','exec'),exporter.__dict__)
