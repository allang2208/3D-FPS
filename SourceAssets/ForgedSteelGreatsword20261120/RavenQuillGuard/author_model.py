"""Model both equipped versions from the approved front silhouette and the sword's actual fittings."""
import json
import math
import runpy
import sys
import numpy as np
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import relief_profile as P

FINISH = HERE/'Art'/'ReliefV3'
ART = HERE/'Art'/'NestedV4'
ART.mkdir(exist_ok=True)
SWORD = HERE.parent
BASE_NAME = 'SM_ForgedSteelGreatsword_RavenQuillGuard'
STOCK_SLOT = 'M_ForgedSteelGreatsword_Surface_V1'
WING_SLOT = 'M_RavenQuill_ForgedMetal'
BP = runpy.run_path(str(SWORD/'GuardSeatFinish/seat_profile.py'))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.context.preferences.filepaths.save_version = 0
def collection(name):
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c
master = collection('Editable metalwork')
exports = collection('Assembled game meshes')
def load_guard(file,name):
    with bpy.data.libraries.load(str(file),link=False) as (_, data):
        data.objects=[name]
    return data.objects[0]
stock = load_guard(SWORD/'Integration/ForgedSteelGreatsword_Modular_Editable.blend','SM_ForgedSteelGreatsword_Guard_V1')
wide = load_guard(SWORD/'ExecutionerBlade/GuardSeats/ExecutionerGuardSeats.blend','SM_ForgedSteelGreatsword_Guard_factory_ExecutionerSeat')
seat_material=stock.data.materials[0]
steel=bpy.data.materials.new(WING_SLOT)
steel.use_nodes=True
nodes=steel.node_tree.nodes
link=steel.node_tree.links.new
bs=nodes.get('Principled BSDF')
def tex(tag, raw):
    img=bpy.data.images.load(str(FINISH/('T_RavenQuill_'+tag+'.png')))
    if raw: img.colorspace_settings.name='Non-Color'
    t=nodes.new('ShaderNodeTexImage');t.image=img
    return t
link(tex('BaseColor',False).outputs['Color'],bs.inputs['Base Color'])
channels=nodes.new('ShaderNodeSeparateColor')
link(tex('ORM',True).outputs['Color'],channels.inputs['Color'])
link(channels.outputs['Green'],bs.inputs['Roughness'])
link(channels.outputs['Blue'],bs.inputs['Metallic'])
bump=nodes.new('ShaderNodeNormalMap')
link(tex('Normal',True).outputs['Color'],bump.inputs['Color'])
link(bump.outputs['Normal'],bs.inputs['Normal'])

def make_metal(name, points, faces, tiles, reference_rows=None):
    """Coordinates authored in cm. UV tiles identify blue steel, polish, recess and shield."""
    m=bpy.data.meshes.new(name)
    m.from_pydata([tuple(c*.01 for c in p) for p in points],[],faces)
    m.materials.append(steel);m.update()
    bm=bmesh.new();bm.from_mesh(m)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(m);bm.free();m.update()
    uv=m.uv_layers.new(name='UVMap')
    for poly,tile in zip(m.polygons,tiles):
        poly.use_smooth=True
        nx,ny,nz=map(abs,poly.normal)
        for idx in poly.loop_indices:
            vertex=m.loops[idx].vertex_index
            x,y,z=m.vertices[vertex].co*100
            if tile in (0,3):
                chart=P.FIELD if tile==0 else P.MEDAL
                py=reference_rows[vertex] if reference_rows is not None else P.image_y(z)
                coords=P.registered_uv(chart,P.image_x(x),py)
            else:
                if ny>=nx and ny>=nz: a,b=x,z
                elif nx>=nz: a,b=y,z
                else: a,b=x,y
                col={1:1,2:2,4:3}[tile]
                coords=((col+.5+a/48)*.25, .1875+b/48*.375)
            uv.data[idx].uv=coords
    m.set_sharp_from_angle(angle=math.radians(33))
    obj=bpy.data.objects.new(name,m);master.objects.link(obj)
    return obj

def sample(keys, pos, column):
    """Shape-preserving cubic interpolation for the hand-drawn wing profiles."""
    def slope(i):
        if i==0: return (keys[1][column]-keys[0][column])/(keys[1][0]-keys[0][0])
        if i==len(keys)-1: return (keys[i][column]-keys[i-1][column])/(keys[i][0]-keys[i-1][0])
        a=(keys[i][column]-keys[i-1][column])/(keys[i][0]-keys[i-1][0])
        b=(keys[i+1][column]-keys[i][column])/(keys[i+1][0]-keys[i][0])
        return 2*a*b/(a+b) if a*b>0 else 0.
    i=next((j for j in range(len(keys)-1) if pos<=keys[j+1][0]),len(keys)-2)
    w=keys[i+1][0]-keys[i][0]; t=(pos-keys[i][0])/w
    return (2*t**3-3*t*t+1)*keys[i][column]+(t**3-2*t*t+t)*w*slope(i)+(-2*t**3+3*t*t)*keys[i+1][column]+(t**3-t*t)*w*slope(i+1)

levels = sorted({0.,.018,.045,.075,.93,.969,.985,1.} | {i/29 for i in range(3,27)})
hammer_depth = np.load(FINISH/'HammerDepthCm.npy')
def indentation(px,py):
    ix=int(px); iy=int(py)
    a=px-ix; b=py-iy
    return ((1-a)*(1-b)*hammer_depth[iy,ix]+a*(1-b)*hammer_depth[iy,ix+1]
            +(1-a)*b*hammer_depth[iy+1,ix]+a*b*hammer_depth[iy+1,ix+1])

def smooth_step(x):
    x=max(0.,min(1.,x))
    return x*x*(3.-2.*x)

def fitted_edges(layer,side,offset):
    """Nest each lower face against the actual underside of its fitted neighbour."""
    parent_bottom=None
    for course,trace in enumerate(P.VANES[:layer+1]):
        dx=max(trace[0][0],min(offset,trace[-1][0]))
        t=(dx-trace[0][0])/(trace[-1][0]-trace[0][0])
        lean=(4.,1.,.8,-.5)[course]*t*t if side<0 else 0.
        top=sample(trace,dx,1)+lean
        bottom=sample(trace,dx,2)+lean
        lift=lap=0.
        if parent_bottom is not None:
            # Tailor the visible face and tuck a narrower metal lip beneath the upper
            # vane. Both sides share a solid mid-plane through the full overlap.
            tip=smooth_step((t-.86)/.14)
            lift=max(3.6*course*smooth_step((dx-48.)/72.),
                     top-parent_bottom-(1.1-2.3*tip))
            lap=max(.75,top-lift-parent_bottom+5.5-3.5*tip)
        parent_bottom=bottom-lift
    return top,bottom,lift,lap

def vane(layer,side,wide_seat=False):
    trace=P.VANES[layer]
    points=[];faces=[];tiles=[];reference_rows=[]
    # The last two vertices at the upper edge form the inset tongue of each lower vane.
    rows=levels+([2.] if layer else [])
    section=[(v,1) for v in rows]+[(v,-1) for v in reversed(rows)]
    # One rung per ~1.4 original pixels; round individual marks without faceting their floors.
    count=round((trace[-1][0]-trace[0][0])/1.4); width=len(section)
    for i in range(count+1):
        t=i/count
        offset=trace[0][0]+t*(trace[-1][0]-trace[0][0])
        top,bottom,lift,lap=fitted_edges(layer,side,offset)
        if wide_seat and layer==0:
            top-=10.5*math.exp(-((offset-91)/39)**2)
        x=P.physical_x(side*offset)
        px=P.CENTER+side*offset
        body=(1.32-.18*layer)*(1-.59*t)*min(1.,.13+13*(1-t))
        for level,surface in section:
            if level>1.:
                reference_rows.append(top)
                points.append((x,surface*.047*body,P.physical_z(top-lift-lap)))
                continue
            py=bottom+(top-bottom)*level
            land=min(1.,level/.135,(1.-level)/.080)
            bevel=1-(1-land)**1.65
            crown=.16*(1-abs(2*level-1))+.070*level
            depth=body*(.085+bevel*(.73+crown))
            depth+=land*min(1.,(1-t)*14)*float(indentation(px,py))
            reference_rows.append(py)
            points.append((x,surface*depth,P.physical_z(py-lift)))
        if i:
            for j,(level,surface) in enumerate(section):
                m=(j+1)%width
                a=(i-1)*width+j; b=(i-1)*width+m
                faces.append((a,b,b+width,a+width))
                mid=(level+section[m][0])*.5
                tiles.append(2 if mid>1. or surface!=section[m][1] else 1 if mid<.042 or mid>.979 else 0)
    faces.extend([tuple(reversed(range(width))),tuple(count*width+j for j in range(width))])
    tiles.extend([2,1])
    return make_metal(('Wide ' if wide_seat else '')+('Right ' if side>0 else 'Left ')+
                      ('lower return' if layer==3 else 'quill '+str(layer+1)),points,faces,tiles,reference_rows)

def engraved_distance(dx,py,start,end):
    ax,ay=start; ex,ey=end[0]-ax,end[1]-ay
    t=max(0.,min(1.,((dx-ax)*ex+(py-ay)*ey)/(ex*ex+ey*ey)))
    return math.hypot(dx-ax-t*ex,py-ay-t*ey)

def plate(name,trace,columns,rows,depth_fn,tile):
    points=[];faces=[];tiles=[]
    stride=rows+1; block=(columns+1)*stride
    for side in (-1,1):
        for i in range(columns+1):
            dx=(2*i/columns-1)*trace[-1][0]
            top=sample(trace,abs(dx),1); bottom=sample(trace,abs(dx),2)
            for j in range(rows+1):
                t=j/rows; py=top+t*(bottom-top)
                depth=depth_fn(abs(dx),py,t,top,bottom)
                points.append((P.physical_x(dx),side*depth,P.physical_z(py)))
        start=0 if side<0 else block
        for i in range(columns):
            for j in range(rows):
                a=start+i*stride+j
                faces.append((a,a+stride,a+stride+1,a+1))
                tiles.append(1 if j==0 or (j==rows-1 and tile==3) else tile)
    outline=[i*stride for i in range(columns+1)]+[columns*stride+j for j in range(1,stride)]
    outline += [i*stride+rows for i in range(columns-1,-1,-1)]+list(range(rows-1,0,-1))
    for i,a in enumerate(outline):
        b=outline[(i+1)%len(outline)]
        faces.append((a,b,b+block,a+block)); tiles.append(2)
    return make_metal(name,points,faces,tiles)

def crest():
    def depth(dx,py,t,top,bottom):
        # The faceted shield stands proud of the mounting shoe; the central quill
        # rises between two incisions. Rounded groove floors catch moving light.
        faceted=2.08+.42*(1-dx/72)+.09*math.sin(t*math.pi)
        near_edge=min((py-top)*.74,(bottom-py)*.74,72-dx)
        faceted-=.18*max(0.,1-near_edge/4.7)
        spine=engraved_distance(dx,py,(2.35,334),(2.35,481))
        d=min([spine]+[engraved_distance(dx,py,a,b) for a,b in P.VEINS])
        groove=.087*math.exp(-(d/1.35)**2)+.037*math.exp(-(d/2.75)**2)
        return faceted-groove+.032*math.exp(-((d-2.45)/.93)**2)
    return plate('Engraved feather escutcheon',P.CREST,140,134,depth,3)

def shoe():
    outline=[(0,319,501),(26,304,501),(35,299,501),(39,308,499),
             (47,329,494),(57,343,477),(72,357,458),(90,365,440),
             (110,369,424),(129,370,416),(144,369,409)]
    def depth(dx,py,t,top,bottom):
        # Recess the supporting web as it meets the overlapping sheet-like vanes.
        u=max(0.,min(1.,(dx-44)/100))
        return (1.96-1.24*u+.035*math.sin(math.pi*t)
                -.16*max(0.,1-(py-top)/5)-.10*max(0.,(py-480)/21))
    return plate('Forged socket and wing roots',outline,108,36,depth,4)

def ferrule():
    # Fit the two highlights and their dark separation within the donor grip joint.
    ring=[(-5.00,1.88,1.88),(-4.94,1.98,1.96),(-4.88,2.035,2.005),
          (-4.64,2.035,2.005),(-4.59,2.00,1.98),(-4.55,1.91,1.90),
          (-4.50,1.91,1.90),(-4.46,2.01,1.99),(-4.41,2.055,2.01),
          (-4.10,2.055,2.01),(-4.035,2.01,1.98),(-3.975,1.93,1.90)]
    n=96;points=[];faces=[];tiles=[]
    strips=[1,1,4,1,2,2,2,1,4,1,1]
    for i,(z,x,y) in enumerate(ring):
        z=-5.0+(z+5.0)*(P.physical_z(498)+5.0)/1.025
        for j in range(n):
            angle=j*2*math.pi/n
            points.append((x*math.cos(angle),y*math.sin(angle),z))
        if i:
            for j in range(n):
                a=(i-1)*n+j;b=(i-1)*n+(j+1)%n
                faces.append((a,b,b+n,a+n));tiles.append(strips[i-1])
    faces.extend([tuple(range(n)),tuple((len(ring)-1)*n+j for j in range(n))]);tiles.extend([2,4])
    return make_metal('Double-lipped ferrule',points,faces,tiles)

def crop_donor(source,name,is_collar=False):
    mesh=source.data;mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data; normals=mesh.corner_normals
    coords=[];faces=[];uvs=[];ns=[]
    def clip(poly,dist):
        clipped=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da,db=dist(a[0]),dist(b[0])
            if da>=0:clipped.append(a)
            if da*db<0:
                k=da/(da-db);clipped.append(tuple(x.lerp(y,k) for x,y in zip(a,b)))
        return clipped
    def rim(p):
        x=abs(p.x)*100
        return p.z*100-(BP['EDGE_HEIGHT']+BP['CENTER_RISE']*max(0,1-x/BP['HALF_WIDTH'])**BP['CURVE_POWER']-.24)
    cuts=[lambda p:-4.39-p.z*100] if is_collar else [lambda p:.0292-p.x,lambda p:.0292+p.x,rim]
    for tri in mesh.loop_triangles:
        ring=[(mesh.vertices[mesh.loops[k].vertex_index].co.copy(),uv[k].uv.copy(),normals[k].vector.copy()) for k in tri.loops]
        for dist in cuts:
            if ring:ring=clip(ring,dist)
        for j in range(1,len(ring)-1):
            a,b,c=ring[0],ring[j],ring[j+1]
            if (b[0]-a[0]).cross(c[0]-a[0]).length<1e-12:continue
            first=len(coords);faces.append((first,first+1,first+2))
            for p,tex,normal in (a,b,c):
                coords.append(p);uvs.append(tex);ns.append(normal.normalized())
    m=bpy.data.meshes.new(name);m.from_pydata(coords,[],faces);m.materials.append(seat_material);m.update()
    layer=m.uv_layers.new(name='UVMap')
    for f in m.polygons:f.use_smooth=True
    for loop in m.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    m.normals_split_custom_set([ns[loop.vertex_index] for loop in m.loops])
    obj=bpy.data.objects.new(name,m);master.objects.link(obj)
    return obj

def assemble(name,parts):
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for part in parts:
        obj=part.copy();obj.data=part.data.copy();exports.objects.link(obj)
        obj.select_set(True);copies.append(obj)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    result=copies[0];result.name=result.data.name=name
    bpy.ops.export_scene.fbx(filepath=str(ART/(name+'.fbx')),use_selection=True,object_types={'MESH'},
         axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
         mesh_smooth_type='FACE',use_tspace=True,use_triangles=True,path_mode='STRIP')
    return result

common=[crest(),shoe(),ferrule()]
for side in (-1,1):
    for i in (1,2,3):common.append(vane(i,side))
regular=assemble(BASE_NAME,[crop_donor(stock,'Original blade root')]+common+[vane(0,s) for s in (-1,1)])
broad=assemble(BASE_NAME+'_ExecutionerSeat',[crop_donor(wide,'Wide blade root')]+common+[vane(0,s,True) for s in (-1,1)])
master.hide_viewport=True;master.hide_render=True;broad.hide_set(True);broad.hide_render=True
bpy.ops.object.select_all(action='DESELECT');regular.select_set(True);bpy.context.view_layer.objects.active=regular
for img in bpy.data.images:
    if img.source=='FILE' and img.filepath and not img.packed_file:
        path=Path(bpy.path.abspath(img.filepath))
        if path.is_file():img.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'RavenQuillGuard.blend'),compress=True)
receipt={}
for obj in (regular,broad):
    obj.data.calc_loop_triangles()
    receipt[obj.name]={'triangles':len(obj.data.loop_triangles),'slots':[m.name for m in obj.data.materials]}
(ART/'exports.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
