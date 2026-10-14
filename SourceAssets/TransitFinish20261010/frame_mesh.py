"""Keep long millimetre bevels well conditioned for tangent generation."""
import bmesh,math
def prepare_frame(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    # Remove the long diagonal before partitioning: otherwise each new piece
    # inherits the same nearly-zero acute corner from the original triangle.
    bmesh.ops.dissolve_limit(bm,angle_limit=.01,verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL'})
    for axis,start,end in ((1,-1.5,1.51),(2,.25,3.01)):
        value=start
        while value<=end:
            point=[0,0,0];normal=[0,0,0];point[axis]=value;normal[axis]=1
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                dist=1e-7,plane_co=point,plane_no=normal,clear_inner=False,clear_outer=False)
            value+=.25
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
def localize_uv(mesh):
    uv=mesh.uv_layers.active
    for f in mesh.polygons:
        offset=[math.floor(sum(uv.data[i].uv[k] for i in f.loop_indices)/len(f.loop_indices)) for k in (0,1)]
        for i in f.loop_indices:
            uv.data[i].uv=(uv.data[i].uv.x-offset[0],uv.data[i].uv.y-offset[1])
