"""Author the Frontier workbench rest heads on the original game prop's local frame."""
from pathlib import Path
import json
import math

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
R2 = HERE.parent / 'RigContactR2'
MODS = HERE.parent / 'CommonModsR1'
EXPORT = HERE / 'Export'
EXPORT.mkdir(exist_ok=True)
specs = json.loads((HERE/'rests.json').read_text(encoding='utf8'))
anchors = json.loads((R2/'anchors.json').read_text(encoding='utf8'))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01

def author_space(key):
    x,y,z = anchors[key]
    return Vector((x,-y,z))

seat = author_space('rest')
forward = seat - author_space('brace').lerp(author_space('draw'),.5)
forward.z = 0
forward.normalize()
side = Vector((-forward.y,forward.x,0))
up = Vector((0,0,1))

def point(f,l,h):
    return seat + f*forward + l*side + h*up

with bpy.data.libraries.load(str(R2/'FrontierCompoundBow_R2.blend')) as (_,assets):
    assets.objects = ['Rest']
mount = assets.objects[0]
scene.collection.objects.link(mount)
mount.name = 'R2 shared side mount and arm'
# Remove only the connected cradle head. The textured R2 bracket and its arm are shared by all three.
bm = bmesh.new()
bm.from_mesh(mount.data)
outboard = max(bm.verts,key=lambda v:v.co.y)
head = {outboard}
todo = [outboard]
while todo:
    vert = todo.pop()
    for edge in vert.link_edges:
        other = edge.other_vert(vert)
        if other not in head:
            head.add(other)
            todo.append(other)
if min(v.co.y for v in head) < seat.y-1.1 or len(head)==len(bm.verts):
    raise ValueError('The R2 cradle is no longer a separate mesh island')
bmesh.ops.delete(bm,geom=list(head),context='VERTS')
bm.to_mesh(mount.data)
bm.free()
mount.data.update()
uv_name = mount.data.uv_layers.active.name
with bpy.data.libraries.load(str(MODS/'Frontier_CommonMods.blend')) as (_,assets):
    assets.materials = ['M_FrontierMods_Surface']
atlas = assets.materials[0]
TILES = 'graphite steel bronze cyan recess mark wax weave thin pad thread fast twist soft serving rubber'.split()

class Part:
    def __init__(self):
        self.verts=[]
        self.faces=[]
        self.finishes=[]

    def ring(self,coords):
        indices=[]
        for co in coords:
            indices.append(len(self.verts))
            self.verts.append(co)
        return indices

    def face(self,ids,tile,uv,smooth=False):
        self.faces.append(ids)
        self.finishes.append((tile,uv,smooth))

    def bridge(self,a,b,tile,uv0,uv1,smooth=False,loop=True):
        n=len(a) if loop else len(a)-1
        for j in range(n):
            k=(j+1)%len(a)
            self.face((a[j],a[k],b[k],b[j]),tile[j] if isinstance(tile,list) else tile,
                      [(j/n,uv0),((j+1)/n,uv0),((j+1)/n,uv1),(j/n,uv1)],smooth)

    def cap(self,ids,tile):
        n=len(ids)
        coords=[(.5+.45*math.cos(math.tau*j/n),.5+.45*math.sin(math.tau*j/n)) for j in range(n)]
        self.face(ids,tile,coords)

    def emit(self,name,collection):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts,[],self.faces)
        mesh.update()
        mesh.materials.append(atlas)
        uv=mesh.uv_layers.new(name=uv_name)
        for poly,(tile,coords,smooth) in zip(mesh.polygons,self.finishes):
            poly.use_smooth=smooth
            row,col=divmod(TILES.index(tile),4)
            for loop,(u,v) in zip(poly.loop_indices,coords):
                uv.data[loop].uv=((col+.025+.95*u)/4,(3-row+.025+.95*v)/4)
        bm=bmesh.new()
        bm.from_mesh(mesh)
        loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
        bmesh.ops.triangulate(bm,faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
        obj=bpy.data.objects.new(name,mesh)
        collection.objects.link(obj)
        return obj

def edge_block(part,stations,tile,edges=None):
    # A clipped rectangular profile swept along the transverse axis of the viewmodel.
    profiles=[]
    for l,f,h,w,d in stations:
        profiles.append(part.ring([point(f+x*w,l,h+z*d) for x,z in
                             [(-.78,-1),(.78,-1),(1,-.65),(1,.65),(.78,1),(-.78,1),(-1,.65),(-1,-.65)]]))
    part.cap(profiles[0],tile)
    for index,(a,b) in enumerate(zip(profiles,profiles[1:])):
        part.bridge(a,b,edges or tile,index/(len(profiles)-1),(index+1)/(len(profiles)-1))
    part.cap(profiles[-1],tile)

def face_button(part,f,l,h,r,metal):
    # Concentric relief and a recessed six-sided inset, all part of the single render mesh.
    loops=[]
    profile=[(0,1),(.018,1),(.048,.82),(.048,.39),(.028,.33)]
    for height,radius in profile:
        loops.append(part.ring([point(f-height,l+r*radius*math.cos(j*math.tau/24),
                                      h+r*radius*math.sin(j*math.tau/24)) for j in range(24)]))
    for i,(a,b) in enumerate(zip(loops,loops[1:])):
        part.bridge(a,b,['recess',metal,'graphite','recess'][i],i/4,(i+1)/4,smooth=i==0)
    part.cap(loops[-1],'recess')
    hexagon=part.ring([point(f-.033,l+r*.29*math.cos(j*math.tau/6),h+r*.29*math.sin(j*math.tau/6)) for j in range(6)])
    part.cap(hexagon,'rubber')

def saddle_point(kind,t,deg,offset):
    theta=math.radians(deg)
    # The authored contact sits on the R2 rest center, with extra clearance at the fore/aft lips.
    rise=max(0.,1-math.cos(theta))
    if kind=='lined':
        radius=.30+.38*rise**1.55
        length=1.05-.12*rise
        drop=.14*t*t
    elif kind=='quick':
        radius=.30+.29*rise**1.55
        length=.63-.12*rise
        drop=.10*t*t
    else:
        radius=.30+.65*max(0.,rise-.40)**1.7
        length=.48-.16*min(1.,rise)
        drop=.10*t*t
    r=radius+offset
    return point(length*t,r*math.sin(theta),-r*math.cos(theta)-drop)

def curved_panel(part,kind,lo,hi,thickness,base_offset,tile,edge_tile,trim=0.,t_scale=1.):
    # Nested contours model the roundover at both ends and both lips, without a second material slot.
    bevel=min(.035,thickness*.27)
    sections=[(bevel,.026,0),(0,0,bevel),(0,0,thickness-bevel),(bevel,.026,thickness)]
    shells=[]
    steps=32 if kind!='fork' else 22
    along=12
    for margin,end_trim,radial in sections:
        surface=[]
        angular_inset=math.degrees(margin/.60)
        for i in range(along+1):
            t=(2*i/along-1)*(1-end_trim)*t_scale
            # The tips are relieved in silhouette; the central part of the saddle carries the insert.
            corner=trim*abs(t)**4
            first,last=lo+angular_inset+corner,hi-angular_inset-corner
            coords=[saddle_point(kind,t,first+(last-first)*j/steps,base_offset+radial) for j in range(steps+1)]
            surface.append(part.ring(coords))
        shells.append(surface)
    for k,faces in ((0,tile),(3,'graphite' if tile in ('graphite','steel') else edge_tile)):
        for i in range(along):
            part.bridge(shells[k][i],shells[k][i+1],faces,i/along,(i+1)/along,smooth=True,loop=False)
    def border(s):
        return s[0]+[row[-1] for row in s[1:]]+list(reversed(s[-1][:-1]))+[row[0] for row in reversed(s[1:-1])]
    for k in range(3):
        part.bridge(border(shells[k]),border(shells[k+1]),edge_tile,k/3,(k+1)/3,smooth=True)

def lined(collection):
    carrier=Part()
    edge_block(carrier,[(-1.12,0,-.83,.21,.12),(-.73,0,-.74,.36,.15),
                        (-.36,0,-.61,.63,.15),(0,0,-.53,.74,.17),(.38,0,-.53,.57,.14)],
               'graphite',['graphite','steel','graphite','graphite','graphite','graphite','graphite','steel'])
    curved_panel(carrier,'lined',-100,100,.19,.085,'graphite','steel',trim=10)
    face_button(carrier,-.64,-.30,-.61,.072,'steel')
    facing=Part()
    curved_panel(facing,'lined',-93,93,.097,0,'thin','pad',trim=10,t_scale=.91)
    return [carrier.emit('Lined - graphite carrier',collection),facing.emit('Lined - leather insert',collection)]

def quick(collection):
    carrier=Part()
    edge_block(carrier,[(-1.13,.02,-.83,.19,.13),(-.78,.02,-.79,.25,.14),
                        (-.39,0,-.65,.38,.18),(-.10,.01,-.55,.47,.17),
                        (.20,.08,-.47,.30,.12)],'graphite')
    curved_panel(carrier,'quick',-103,45,.17,.067,'graphite','graphite',trim=7)
    facing=Part()
    curved_panel(facing,'quick',-93,36,.08,0,'steel','recess',trim=6,t_scale=.87)
    # Inlaid family accent kept entirely below the exposed sliding face.
    for t0,t1 in [(-.91,-.22),(-.13,.09)]:
        rings=[]
        for i in range(7):
            t=t0+(t1-t0)*i/6
            rings.append(facing.ring([saddle_point('quick',t,angle,radial) for angle,radial in
                                      [(-81,.231),(-76,.231),(-76.6,.247),(-80.4,.247)]]))
        for i in range(6):
            facing.bridge(rings[i],rings[i+1],'cyan',i/6,(i+1)/6)
        facing.cap(rings[0],'cyan')
        facing.cap(rings[-1],'cyan')
    return [carrier.emit('Quick - low carrier',collection),facing.emit('Quick - slide and inlay',collection)]

def fork(collection):
    yoke=Part()
    edge_block(yoke,[(-1.12,0,-.83,.20,.13),(-.68,0,-.83,.29,.14),
                     (-.26,0,-.68,.39,.16),(0,0,-.67,.43,.13),
                     (.26,0,-.68,.39,.16)],'graphite')
    wings=[]
    for sign,label in [(-1,'inboard'),(1,'outboard')]:
        wing=Part()
        edge_block(wing,[(sign*.10,0,-.70,.32,.12),(sign*.22,0,-.57,.39,.15),
                         (sign*.29,0,-.43,.40,.14)],'graphite')
        lo,hi=sorted((sign*24,sign*109))
        curved_panel(wing,'fork',lo,hi,.21,.055,'graphite','steel',trim=4)
        first,last=sorted((sign*30,sign*102))
        curved_panel(wing,'fork',first,last,.067,0,'rubber','recess',trim=5,t_scale=.79)
        wings.append(wing.emit('Fork - '+label+' wing',collection))
    face_button(yoke,-.285,-.68,-.83,.077,'bronze')
    return [yoke.emit('Fork - lower yoke',collection),*wings]

def export_mesh(name,pieces):
    copies=[]
    for obj in pieces:
        clone=obj.copy()
        clone.data=obj.data.copy()
        scene.collection.objects.link(clone)
        copies.append(clone)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies:obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    mesh=copies[0]
    mesh.name=name
    triangulate=mesh.modifiers.new('FBX tangent faces','TRIANGULATE')
    triangulate.min_vertices=5
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                             axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,
                             use_tspace=True,mesh_smooth_type='FACE')
    bpy.data.objects.remove(mesh,do_unlink=True)

builders={'lined_rest':lined,'open_quick_rest':quick,'fork_guide_rest':fork}
collections=[]
for key,design in specs.items():
    collection=bpy.data.collections.new(key)
    scene.collection.children.link(collection)
    collections.append(collection)
    pieces=builders[key](collection)
    export_mesh(design['mesh'],[mount,*pieces])
for collection in collections[1:]:
    collection.hide_viewport=True
    collection.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Frontier_ArrowRests.blend'),compress=True)
