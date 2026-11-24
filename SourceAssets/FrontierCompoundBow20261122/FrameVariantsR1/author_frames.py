"""Author Frontier's game-only body variants from its R2 rest-space mesh."""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'RigContactR2' / 'FrontierCompoundBow_R2.blend'
MODS = HERE.parent / 'CommonModsR1' / 'Frontier_CommonMods.blend'
EXPORT = HERE / 'Export'
EXPORT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.frame_set(1)
rig = scene.objects['Armature']
rig.data.pose_position = 'REST'
base = scene.objects['Riser']
mechanism = [scene.objects[n] for n in ('UpperLimb', 'LowerLimb', 'UpperCam', 'LowerCam', 'ControlCable1', 'ControlCable2')]
with bpy.data.libraries.load(str(MODS)) as (available, chosen):
    chosen.materials = ['M_FrontierMods_Surface']
atlas = chosen.materials[0]
atlas_uv = 'UVMap'
if base.data.uv_layers.active:
    atlas_uv = base.data.uv_layers.active.name

FRAME_NAMES = {key: row['model'] for key, row in json.loads((HERE / 'frames.json').read_text(encoding='utf8')).items()}
TILES = 'graphite steel bronze cyan recess mark wax weave thin pad thread fast twist soft serving rubber'.split()
BANDS = [(-19.7,-11.7), (20.7,30.65)]

def blend(a, b, t):
    return a + (b-a)*t

def ease(t):
    t = min(1., max(0., t))
    return t*t*(3-2*t)

class OriginalSurface:
    def __init__(self, obj):
        self.obj = obj
        mesh = obj.data
        mesh.calc_loop_triangles()
        self.tris = [tuple(tri.vertices) for tri in mesh.loop_triangles]
        self.tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], self.tris, all_triangles=True)
        self.sections = {}

    def sample(self, x, z, side):
        start = Vector((x,side*12.,z))
        return self.tree.ray_cast(start, Vector((0,-side,0)),24.)

    def spans(self, z):
        if z not in self.sections:
            spans = []
            for i in range(-160,341):
                if self.sample(i/20, z, -1)[0] is None:
                    continue
                if not spans or i > spans[-1][-1]+1:
                    spans.append([i])
                else:
                    spans[-1].append(i)
            self.sections[z] = [(s[0]/20,s[-1]/20) for s in spans if len(s)>4]
        return self.sections[z]

    def weights(self, face, pos):
        vertices = self.obj.data.vertices
        ids = self.tris[face]
        bary = barycentric_transform(pos, *(vertices[i].co for i in ids),
                                     Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1)))
        weights = {}
        for i, factor in zip(ids,bary):
            for group in vertices[i].groups:
                name = self.obj.vertex_groups[group.group].name
                weights[name] = weights.get(name,0.) + max(0.,factor)*group.weight
        total = sum(weights.values())
        return {name:w/total for name,w in weights.items() if w>0.} if total else {}

riser = OriginalSurface(base)
limbs = [OriginalSurface(obj) for obj in mechanism[:2]]

class DetailMesh:
    def __init__(self):
        self.points = []
        self.faces = []
        self.styles = []
        self.weights = []

    def row(self, vertices, weights=None):
        index = len(self.points)
        self.points.extend(vertices)
        self.weights.extend(weights or [{'bow_body_root':1.}]*len(vertices))
        return list(range(index,index+len(vertices)))

    def face(self, indices, tile):
        self.faces.append(indices)
        self.styles.append(tile)

    def sweep(self, rows, finishes, cap='graphite'):
        self.face(list(reversed(rows[0])),cap)
        for start,end in zip(rows,rows[1:]):
            for i,tile in enumerate(finishes):
                j=(i+1)%len(start)
                self.face([start[i],start[j],end[j],end[i]],tile)
        self.face(rows[-1],cap)

    def build(self, name, collection):
        data=bpy.data.meshes.new(name)
        data.from_pydata(self.points,[],self.faces)
        data.materials.append(atlas)
        data.update()
        uv=data.uv_layers.new(name=atlas_uv)
        # Box projection in object space keeps the authored atlas grain aligned along the rails.
        for poly,tile in zip(data.polygons,self.styles):
            row,col=divmod(TILES.index(tile),4)
            normal=poly.normal
            axis=max(range(3),key=lambda i:abs(normal[i]))
            axes=[k for k in range(3) if k!=axis]
            for loop in poly.loop_indices:
                p=data.vertices[data.loops[loop].vertex_index].co
                u=.5+.46*math.sin(.22*p[axes[0]])
                v=.5+.46*math.sin(.067*p[axes[1]])
                uv.data[loop].uv=((col+u)/4,(3-row+v)/4)
        bm=bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
        bmesh.ops.triangulate(bm,faces=bm.faces[:])
        bm.to_mesh(data)
        bm.free()
        obj=bpy.data.objects.new(name,data)
        collection.objects.link(obj)
        obj.parent=rig
        mod=obj.modifiers.new('R2 armature','ARMATURE')
        mod.object=rig
        groups={}
        for i,weights in enumerate(self.weights):
            for key,w in weights.items():
                if key not in groups:
                    groups[key]=obj.vertex_groups.new(name=key)
                groups[key].add([i],w,'REPLACE')
        return obj

def section(z):
    spans=riser.spans(z)
    if len(spans)!=2:
        raise ValueError(f'Expected two rail mouths at {z}: {spans!r}')
    ends=[]
    for a,b in spans:
        c=(a+b)/2
        y1=riser.sample(c,z,-1)[0].y
        y2=riser.sample(c,z,1)[0].y
        ends.append((c,(a-b)*-.5+.035,(y1+y2)*.5,(y2-y1)*.5))
    return ends

def octagon(x,rx,y,ry,z):
    # Broad flats and edge facets stay legible at viewmodel scale.
    return [(x+rx*a,y+ry*b,z) for a,b in
            [(-.75,-1),(.75,-1),(1,-.74),(1,.74),(.75,1),(-.75,1),(-1,.74),(-1,-.74)]]

def cut_windows(obj):
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    for lo,hi in BANDS:
        for z in (lo,hi):
            bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                                   plane_co=(0,0,z),plane_no=(0,0,1),dist=.000001)
        removed=[f for f in bm.faces if lo < f.calc_center_median().z < hi]
        bmesh.ops.delete(bm,geom=removed,context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

def rail_profile(ends,t,kind,which):
    a,b=ends
    start,end=a[which],b[which]
    center,width,y,depth=(blend(start[i],end[i],t) for i in range(4))
    wave=math.sin(math.pi*t)
    if kind=='Swift':
        center+=(-1.48 if which==0 else .56)*wave
        width*=1-(.52 if which==0 else .43)*wave
        depth*=1-.30*wave
    elif kind=='Heavy':
        center+=(-.70 if which==0 else .64)*wave
        width+=(.85 if which==0 else 1.10)*wave
        depth+=.61*wave
    else:
        middle=blend(sum(v[0] for v in a)/2,sum(v[0] for v in b)/2,t)
        separation=(a[1][0]-a[0][0]+b[1][0]-b[0][0])/4
        straight=ease(min(t,1-t)/.23)
        center=blend(center,middle+(-1 if which==0 else 1)*separation*.84,straight)
        width=blend(width,.62,straight)
        depth=blend(depth,1.35,straight)
    return center,width,y,depth

def end_collar(g,p,z):
    x,rx,y,ry=p
    shape=[(-.31,.99),(-.24,1.06),(-.17,1.085),(.16,1.085),(.23,1.055),(.30,.99)]
    rings=[g.row(octagon(x,(rx+.10)*k,y,(ry+.065)*k,z+dz)) for dz,k in shape]
    g.sweep(rings,['graphite','steel','graphite','graphite']*2)

def bridge(g,ends,z,t,kind):
    # Crosspieces sit behind the stepped cheeks, leaving two visible openings.
    rails=[rail_profile(ends,t,kind,i) for i in range(2)]
    rows=[]
    for i in range(13):
        f=i/12
        x=blend(rails[0][0],rails[1][0],f)
        zz=z+.68*(f-.5)
        rows.append(g.row([(x,yy,zz+off) for yy,off in
                           [(-1.47,-.26),(-1.31,-.42),(1.31,-.42),(1.47,-.26),
                            (1.47,.26),(1.31,.42),(-1.31,.42),(-1.47,.26)]]))
    g.sweep(rows,['steel','graphite','steel','graphite']*2)

def frame_band(g,kind,lo,hi):
    ends=section(lo),section(hi)
    for i in (0,1):
        rows=[]
        for n in range(31):
            t=n/30
            x,w,y,d=rail_profile(ends,t,kind,i)
            rows.append(g.row(octagon(x,w,y,d,blend(lo-.12,hi+.12,t))))
        tile='steel' if kind=='Steady' else 'graphite'
        edge='bronze' if kind=='Heavy' else 'steel'
        g.sweep(rows,[tile,edge,'graphite',edge,tile,edge,'graphite',edge])
        for z,p in ((lo,ends[0][i]),(hi,ends[1][i])):
            end_collar(g,p,z)
        for side in (-1,1):
            if kind=='Swift' and i==1:
                continue
            rows=[]
            for j in range(25):
                t=.085+.83*j/24
                x,w,y,d=rail_profile(ends,t,kind,i)
                width={'Heavy':.80,'Swift':.20,'Steady':.34}[kind]*w
                taper=.37+.63*ease(min(j,24-j)/3)
                # Separate outer plates/rails are raised enough to catch light from oblique angles.
                outer=y+side*d
                step={'Heavy':.32,'Swift':.075,'Steady':.13}[kind]*taper
                z=blend(lo-.12,hi+.12,t)
                prof=[(-1,-.04),(1,-.04),(1,.37),(.72,1),(-.72,1),(-1,.37)]
                rows.append(g.row([(x+width*a*taper,outer+side*(step*b),z) for a,b in prof]))
            finish={'Heavy':'graphite','Swift':'recess','Steady':'recess'}[kind]
            g.sweep(rows,['recess','graphite','steel',finish,'steel','graphite'])
    if kind=='Heavy':
        for t in (.28,.73):
            bridge(g,ends,blend(lo,hi,t),t,kind)

def fitted_cheek(g,source,levels,where,width,depth,finish,root=False):
    """Drape a layered cosmetic strip on both faces, transferring real limb weights where needed."""
    for side in (-1,1):
        rows=[]
        for j,z in enumerate(levels):
            spans=source.spans(z)
            if not spans:
                raise ValueError(f'Missing support surface on {source.obj.name} at {z}')
            start,end=spans[0]
            center=where(start,end,z)
            taper=.38+.62*ease(min(j,len(levels)-1-j)/3)
            half=min(width,(end-start)*.43)*taper
            cross=[(-1,-.05),(1,-.05),(1,.20),(.75,.92),(.23,1),(-.57,1),(-.84,.76),(-1,.20)]
            vertices=[]
            weights=[]
            for a,b in cross:
                x=max(start+.03,min(end-.03,center+half*a))
                pos,_,face,_=source.sample(x,z,side)
                if pos is None:
                    raise ValueError(f'Lost contact on {source.obj.name} at {(x,z)}')
                vertices.append((x,pos.y+side*depth*b,z))
                weights.append({'bow_body_root':1.} if root else source.weights(face,pos))
            rows.append(g.row(vertices,weights))
        g.sweep(rows,['graphite','recess','steel',finish,finish,'steel','graphite','recess'])

def linear_levels(a,b,n=33):
    return [blend(a,b,i/(n-1)) for i in range(n)]

def author_details(g,kind):
    if kind!='Strong':
        for lo,hi in BANDS:
            frame_band(g,kind,lo,hi)
    if kind=='Strong':
        # The R2 cutouts continue between the gussets and the pocket.
        for z1,z2 in [(30.9,38.15),(-21.2,-27.65)]:
            fitted_cheek(g,riser,linear_levels(z1,z2),lambda a,b,z:a+min(.65,(b-a)*.50),
                         .65,.39,'graphite',root=True)
        for z1,z2 in [(31.45,36.1),(-21.7,-25.7)]:
            # Follow the outside rail separately across the split near the limb root.
            for side in (-1,1):
                rows=[]
                for j,z in enumerate(linear_levels(z1,z2)):
                    a,b=riser.spans(z)[-1]
                    c=b-min(.64,(b-a)*.5)
                    half=min(.47,(b-a)*.38)*(.28+.72*ease(min(j,32-j)/4))
                    xs=(-half,half,half,.73*half,-.73*half,-half)
                    row=[]
                    for dx,offset in zip(xs,(-.08,-.08,.07,.24,.24,.07)):
                        pt=riser.sample(c+dx,z,side)[0]
                        if pt is None:raise ValueError('Gusset surface missing')
                        row.append((pt.x,pt.y+side*offset,pt.z))
                    rows.append(g.row(row))
                g.sweep(rows,['recess','graphite','steel','graphite','steel','graphite'])
    if kind=='Swift':
        for source,z1,z2 in zip(limbs,(40.6,-30.5),(43.6,-33.25)):
            fitted_cheek(g,source,linear_levels(z1,z2,23),lambda a,b,z:blend(a,b,.50),
                         1.12,.15,'graphite')

def duplicate(obj,collection):
    copy=obj.copy()
    copy.data=obj.data.copy()
    collection.objects.link(copy)
    return copy

def select(objects,active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=active

def export_assembly(name,parts):
    copies=[duplicate(obj,scene.collection) for obj in parts]
    body=copies[0]
    select(copies,body)
    bpy.ops.object.join()
    body.name=name
    select([rig,body],rig)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
                             axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,
                             bake_anim=False,mesh_smooth_type='FACE')
    bpy.data.objects.remove(body,do_unlink=True)

variants=[]
for key,kind in FRAME_NAMES.items():
    coll=bpy.data.collections.new(kind+' frame')
    scene.collection.children.link(coll)
    shell=duplicate(base,coll)
    shell.name=kind+'_Riser'
    if kind!='Strong':
        cut_windows(shell)
    g=DetailMesh()
    author_details(g,kind)
    trim=g.build(kind+'_Panels',coll)
    export_assembly('SK_Frontier_'+kind+'Frame',[shell,*mechanism,trim])
    variants.append(coll)
base.hide_set(True)
base.hide_render=True
for coll in variants[1:]:
    coll.hide_viewport=True
    coll.hide_render=True
rig.data.pose_position='POSE'
scene.frame_set(1)
select([],rig)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Frontier_Frames.blend'),compress=True)
