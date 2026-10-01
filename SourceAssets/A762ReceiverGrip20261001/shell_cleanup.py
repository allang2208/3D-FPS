"""Remove microscopic internal slivers left by the Phantom donor's thin skins."""
import bmesh
def close_slivers(bm):
    bad=[e for e in bm.edges if not e.is_manifold]
    if not bad:return
    verts=list({v for e in bad for v in e.verts})
    bmesh.ops.remove_doubles(bm,verts=verts,dist=.00001)
    overlap=list({f for e in bm.edges if len(e.link_faces)>2 for f in e.link_faces})
    if overlap:bmesh.ops.delete(bm,geom=overlap,context='FACES_ONLY')
    wire=[e for e in bm.edges if not e.link_faces]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
