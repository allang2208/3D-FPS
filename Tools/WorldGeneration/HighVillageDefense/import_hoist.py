"""Author the four cosmetic hoist parts in UE centimetres; wheel axle is local X."""
from math import cos, pi, radians, sin, sqrt
import unreal as u

DEST = "/Game/WorldGeneration/TemperateHills/HighVillageDefense/Hoist"
IRON = "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron"
OWNER = "HighVillagePortcullisHoist"
editor = u.EditorAssetLibrary


def norm(v):
    length = sqrt(sum(a*a for a in v))
    return tuple(a/length for a in v)


class Geometry:
    def __init__(self):
        self.mesh = u.DynamicMesh()
        self.vertices, self.normals, self.uv, self.faces = [], [], [], []

    def surface(self, rows):
        # Each point has its position, outward normal and metric UV.
        cols = len(rows[0])
        offset = len(self.vertices)
        for row in rows:
            for pos, normal, uv in row:
                self.vertices.append(u.Vector(*pos))
                self.normals.append(u.Vector(*normal))
                self.uv.append(u.Vector2D(*uv))
        for i in range(len(rows)-1):
            for j in range(cols-1):
                a = offset+i*cols+j
                for tri in ((a,a+cols,a+cols+1),(a,a+cols+1,a+1)):
                    p,q,r = (self.vertices[k] for k in tri)
                    cross = (q-p).cross(r-p)
                    if cross.dot(self.normals[tri[0]]) > 0:
                        tri = (tri[0],tri[2],tri[1])
                    self.faces.append(u.IntVector(*tri))

    def link(self, center=(0,0,0), across=False):
        # Round-bar oval, with straight flanks and semicircular crowns.
        path = []
        radius, half_straight, bar = 3.5, 3.25, 1.3
        for s,angle in ((1,0),(-1,pi)):
            for j in range(9):
                a = angle + j*pi/8
                path.append((radius*cos(a),s*half_straight+radius*sin(a),cos(a),sin(a)))
        rows=[]
        for i,(v,z,ny,nz) in enumerate(path+[path[0]]):
            ring=[]
            for j in range(9):
                a=2*pi*j/8
                n=(sin(a),cos(a)*ny,cos(a)*nz)
                pos=(bar*n[0],v+bar*n[1],z+bar*n[2])
                if across:
                    pos=(-pos[1],pos[0],pos[2])
                    n=(-n[1],n[0],n[2])
                ring.append((tuple(p+c for p,c in zip(pos,center)),n,(i/len(path),j/8)))
            rows.append(ring)
        self.surface(rows)

    def rim(self, profile, n=36):
        # A closed machined radial section with two lips and a chain groove.
        for (x0,r0),(x1,r1) in zip(profile,profile[1:]+profile[:1]):
            nx,nr=norm((r0-r1,x1-x0))
            rows=[]
            for x,r in ((x0,r0),(x1,r1)):
                row=[]
                for i in range(n+1):
                    a=2*pi*i/n
                    row.append(((x,r*cos(a),r*sin(a)),(nx,nr*cos(a),nr*sin(a)),(i/n,x*.04+r*.04)))
                rows.append(row)
            self.surface(rows)

    def box(self,center,size,roll=0):
        tr=u.Transform(location=center,rotation=u.Rotator(roll=roll),scale=(1,1,1))
        u.GeometryScript_Primitives.append_box(self.mesh,u.GeometryScriptPrimitiveOptions(),
            tr,*size,origin=u.GeometryScriptPrimitiveOriginMode.CENTER)

    def pin(self,center,radius,length,sides,along_x):
        tr=u.Transform(location=center,rotation=u.Rotator(pitch=90 if along_x else 0),scale=(1,1,1))
        u.GeometryScript_Primitives.append_cylinder(self.mesh,u.GeometryScriptPrimitiveOptions(),
            tr,radius,length,radial_steps=sides,origin=u.GeometryScriptPrimitiveOriginMode.CENTER)

    def save(self,name,mat):
        if self.vertices:
            buf=u.GeometryScriptSimpleMeshBuffers(vertices=self.vertices,normals=self.normals,
                                                  uv0=self.uv,triangles=self.faces)
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(self.mesh,buf)
        path=DEST+"/"+name
        obj=editor.load_asset(path) if editor.does_asset_exist(path) else None
        if obj and str(editor.get_metadata_tag(obj,"VillageHoistOwner"))!=OWNER:
            raise RuntimeError("Another asset occupies "+path)
        if not obj:
            obj,result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(self.mesh,path,
                u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                    enable_recompute_tangents=True,enable_collision=False,enable_nanite=False))
            if not obj or result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
        opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            replace_materials=True,new_materials=[mat],new_material_slot_names=["ForgedIron"])
        _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(self.mesh,obj,opts,u.GeometryScriptMeshWriteLOD())
        editor.set_metadata_tag(obj,"VillageHoistOwner",OWNER)
        if result!=u.GeometryScriptOutcomePins.SUCCESS or not editor.save_loaded_asset(obj,False):
            raise RuntimeError("Failed to save "+path)
        u.log("HOIST_SAVED "+path)


material=u.load_asset(IRON)
if not material: raise RuntimeError(IRON)
editor.make_directory(DEST)
link=Geometry()
link.link()
link.save("SM_HoistLink",material)

wheel=Geometry()
wheel.rim([(-4.6,12),(-4.6,16.8),(-3.8,17.6),(-2.6,17.6),(-1.3,14.9),
           (1.3,14.9),(2.6,17.6),(3.8,17.6),(4.6,16.8),(4.6,12)])
for i in range(6):
    a=2*pi*i/6
    wheel.box((0,8.1*cos(a),8.1*sin(a)),(4.6,10.,2.8),-i*60.)
wheel.pin((0,0,0),5.8,13,16,True)
wheel.pin((0,0,0),2.9,30,12,True)
for side in (-1,1):
    wheel.pin((15*side,0,0),3.8,2,6,True)
wheel.save("SM_HoistSheave",material)

frame=Geometry()
# Both bearing standards stand on one pair of iron straps. The courtyard
# bearing is supported by a cantilever which returns to the stone coping.
for x in (-10.,10.):
    frame.box((x,75,-17.7),(6,183,3.4))
    for y in (16.,153.):
        frame.box((x,y,-9.0),(4.5,12,16))
        frame.pin((x,y,0),6.1,4.5,16,True)
        frame.box((x,y,-2.5),(5.,15.,2.2))
    for y in (5,29,75,109,123):
        frame.pin((x,y,-15.4),2.,2.,6,False)
for y in (8,109,123,164):
    frame.box((0,y,-19),(25,4,3))
frame.box((0,131,-34),(23,4,28))
for x in (-10.,10.):
    frame.box((x,148,-31.8),(4,44,4),-38.)
frame.save("SM_HoistBearing",material)

weight=Geometry()
weight.link((0,0,-9.4),across=True)
for z,w,d,h in ((-18,20,12,5),(-24,25,14,8),(-29,21,12,3)):
    weight.box((0,0,z),(w,d,h))
for x in (-7,7):
    weight.box((x,0,-24),(2.2,15,14))
weight.save("SM_HoistWeight",material)
