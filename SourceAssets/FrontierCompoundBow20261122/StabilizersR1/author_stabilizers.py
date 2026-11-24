"""Author the two Frontier viewmodel props against the existing R2 attachment."""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
OUT=HERE/'Export'
OUT.mkdir(exist_ok=True)
options=json.loads((HERE/'options.json').read_text(encoding='utf8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.01
with bpy.data.libraries.load(str(HERE.parent/'RigContactR2/FrontierCompoundBow_R2.blend')) as (_,loaded):
    loaded.objects=['Stabilizer']
factory=loaded.objects[0]
scene.collection.objects.link(factory)
with bpy.data.libraries.load(str(HERE.parent/'CommonModsR1/Frontier_CommonMods.blend')) as (_,loaded):
    loaded.materials=['M_FrontierMods_Surface']
atlas=loaded.materials[0]
TILES='graphite steel bronze cyan recess mark wax weave thin pad thread fast twist soft serving rubber'.split()
xs=[v.co.x for v in factory.data.vertices]
span=max(xs)-min(xs)
cut=min(xs)+span*.09

# Use the actual intersection of the native surface to keep its author coordinates and UVs at the base.
bm=bmesh.new()
bm.from_mesh(factory.data)
bisect=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],dist=.00001,
                              plane_co=(cut,0,0),plane_no=(1,0,0),clear_outer=True)
border=[edge for edge in bisect['geom_cut'] if isinstance(edge,bmesh.types.BMEdge) and edge.is_valid and edge.is_boundary]
if not border:raise RuntimeError('The source stabilizer no longer crosses its saved mount section')
verts={v for edge in border for v in edge.verts}
def limits(axis):
    points=[v.co[axis] for v in verts]
    return (max(points)+min(points))*.5,(max(points)-min(points))*.5
cy,ry=limits(1)
cz,rz=limits(2)
radius=(ry+rz)*.5
bmesh.ops.holes_fill(bm,edges=border,sides=0)
mount=factory.copy()
mount.data=factory.data.copy()
mount.name='Shared factory mount'
bm.to_mesh(mount.data)
bm.free()
mount.data.update()
scene.collection.objects.link(mount)
factory.hide_set(True)
factory.hide_render=True

def point(axial,r,angle):
    return (cut+span*axial, cy+radius*r*math.cos(angle), cz+radius*r*math.sin(angle))

class Skin:
    def __init__(self):
        self.vertices=[]
        self.faces=[]
        self.attrs=[]

    def ring(self,points):
        start=len(self.vertices)
        self.vertices.extend(points)
        return list(range(start,len(self.vertices)))

    def face(self,ids,tile,uv,smooth):
        self.faces.append(ids)
        self.attrs.append((tile,uv,smooth))

    def band(self,a,b,tile,v0,v1,smooth=True):
        n=len(a)
        for i in range(n):
            j=(i+1)%n
            self.face([a[i],a[j],b[j],b[i]],tile,[(i/n,v0),((i+1)/n,v0),((i+1)/n,v1),(i/n,v1)],smooth)

    def cap(self,ids,tile):
        self.face(ids,tile,[(.5+.46*math.cos(i*math.tau/len(ids)),.5+.46*math.sin(i*math.tau/len(ids))) for i in range(len(ids))],False)

    def lathe(self,profile,n=64,flutes=0):
        rows=[]
        for t,r,depth,tile in profile:
            row=[]
            for i in range(n):
                a=math.tau*i/n
                ridge=(.5+.5*math.cos(a*flutes))**2 if flutes else 0.
                row.append(point(t,r*(1-depth*ridge),a))
            rows.append(self.ring(row))
        self.cap(rows[0],profile[0][3])
        for i,(a,b) in enumerate(zip(rows,rows[1:])):
            self.band(a,b,profile[i][3],i/(len(rows)-1),(i+1)/(len(rows)-1))
        self.cap(rows[-1],profile[-1][3])

    def cage_rail(self,phase):
        rows=[]
        for t,r,arc in [(.085,1.02,.63),(.10,1.10,.58),(.13,1.15,.48),(.19,1.19,.31),
                        (.26,1.17,.25),(.33,1.13,.27),(.40,1.07,.40),(.435,1.03,.58),(.45,.97,.62)]:
            # Each blade has its own bevels, rear face and open negative space on either side.
            section=[(-.82,0),(.82,0),(1,-.08),(1,-.23),(.72,-.30),(-.72,-.30),(-1,-.23),(-1,-.08)]
            skew=.24*math.sin(math.pi*(t-.085)/.365)
            rows.append(self.ring([point(t,r+dr,phase+skew+da*arc) for da,dr in section]))
        self.cap(rows[0],'graphite')
        for i,(a,b) in enumerate(zip(rows,rows[1:])):
            n=len(a)
            for j,tile in enumerate(['graphite','steel','graphite','recess','recess','recess','graphite','steel']):
                k=(j+1)%n
                self.face([a[j],a[k],b[k],b[j]],tile,[(0,i/8),(1,i/8),(1,(i+1)/8),(0,(i+1)/8)],True)
        self.cap(rows[-1],'graphite')

    def emit(self,name):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices,[],self.faces)
        mesh.update()
        mesh.materials.append(atlas)
        uv=mesh.uv_layers.new(name=factory.data.uv_layers.active.name)
        for poly,(tile,coords,smooth) in zip(mesh.polygons,self.attrs):
            poly.use_smooth=smooth
            row,col=divmod(TILES.index(tile),4)
            for loop,(u,v) in zip(poly.loop_indices,coords):
                uv.data[loop].uv=((col+.025+.95*u)/4,(3-row+.025+.95*v)/4)
        bm=bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
        bmesh.ops.triangulate(bm,faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
        obj=bpy.data.objects.new(name,mesh)
        scene.collection.objects.link(obj)
        return obj

def shade():
    s=Skin()
    s.lathe([(-.011,.99,0,'graphite'),(0,1.06,0,'steel'),(.016,1.095,0,'graphite'),
             (.06,1.10,.035,'graphite'),(.083,1.02,0,'steel'),(.098,.84,0,'recess'),
             (.108,.65,0,'rubber'),(.416,.65,.10,'rubber'),(.435,.95,0,'graphite'),
             (.455,1.10,.045,'steel'),(.466,1.105,0,'cyan'),(.479,1.105,0,'graphite'),
             (.492,1.08,0,'graphite'),(.512,.91,0,'steel'),(.516,.82,0,'recess'),
             (.506,.68,0,'rubber'),(.506,.14,0,'rubber')],72,12)
    for phase in range(3):s.cage_rail(phase*math.tau/3+.29)
    for t in (.14,.195,.25,.305,.36,.405):
        s.lathe([(t,.65,0,'rubber'),(t+.004,.70,0,'graphite'),(t+.011,.71,0,'rubber'),(t+.015,.65,0,'rubber')],48)
    return s

def ridge():
    s=Skin()
    s.lathe([(-.012,.985,0,'graphite'),(0,1.055,0,'steel'),(.012,1.08,0,'graphite'),
             (.048,1.08,.04,'steel'),(.065,.95,0,'recess'),(.078,.88,0,'graphite'),
             (.10,.89,0,'steel'),(.115,.72,0,'weave'),(.81,.65,0,'weave'),
             (.827,.74,0,'steel'),(.843,.87,0,'graphite'),(.895,.88,0,'recess'),
             (1.12,.88,0,'graphite'),(1.126,.73,0,'recess')],72,12)
    # Three distinct segmented end masses reveal an uninterrupted dark spine between them.
    for index,(t,length,r) in enumerate([(.865,.070,1.19),(.949,.069,1.30),(1.033,.101,1.34)]):
        accent='bronze' if index==2 else 'graphite'
        s.lathe([(t,.87,0,'graphite'),(t+.007,r*.93,.03,'steel'),(t+.013,r,.06,'graphite'),
                 (t+length*.48,r,.085,'graphite'),(t+length*.55,r,.045,accent),
                 (t+length*.66,r,.045,'graphite'),(t+length-.01,r,.06,'steel'),
                 (t+length-.004,r*.94,0,'graphite'),(t+length,.87,0,'recess')],80,10)
    s.lathe([(1.131,.85,0,'graphite'),(1.137,.89,0,'steel'),(1.145,.78,0,'rubber'),
             (1.146,.56,0,'rubber'),(1.14,.49,0,'recess'),(1.14,.11,0,'graphite')],64)
    return s

def export(pieces,name):
    copies=[]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in pieces:
        clone=obj.copy()
        clone.data=obj.data.copy()
        scene.collection.objects.link(clone)
        clone.select_set(True)
        copies.append(clone)
    merged=copies[0]
    bpy.context.view_layer.objects.active=merged
    bpy.ops.object.join()
    merged.name=name
    tri=merged.modifiers.new('Export caps','TRIANGULATE')
    tri.min_vertices=5
    bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                             bake_anim=False,apply_unit_scale=True,use_tspace=True,mesh_smooth_type='FACE')
    bpy.data.objects.remove(merged,do_unlink=True)

builders={'shade_compact':shade,'far_ridge':ridge}
for key,spec in options.items():
    obj=builders[key]().emit(key)
    export([mount,obj],spec['mesh'])
    if key=='far_ridge':
        obj.hide_set(True)
        obj.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Frontier_Stabilizers.blend'),compress=True)
