"""Improve the copied concrete triangulation without changing its silhouette."""
import bmesh

def prepare_concrete(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    # The approved source includes long, almost collinear triangle fans.
    # Rotate only internal coplanar edges within a material region.
    edges=[e for e in bm.edges if len(e.link_faces)==2
        and all(len(f.verts)==3 for f in e.link_faces)
        and e.link_faces[0].material_index==e.link_faces[1].material_index
        and e.link_faces[0].normal.dot(e.link_faces[1].normal)>.999999]
    bmesh.ops.beautify_fill(bm,faces=list(bm.faces),edges=edges,method='AREA')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free();mesh.update()

def project_uv(mesh):
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        axes=[k for k in range(3) if k!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]],p[axes[1]])
