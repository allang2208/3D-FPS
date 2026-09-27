"""Author the approved ethereal sword direction; Blender background, no renders.

60 cm sword, tip +X, width Y, thickness Z. UV0 is object-locked along X.
Own geometric authoring: no external models or generated texture projections.
"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'

def material(name, rgb, alpha):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, alpha)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Metallic'].default_value = 0
    p.inputs['Roughness'].default_value = .24
    p.inputs['Alpha'].default_value = alpha
    p.inputs['Emission Color'].default_value = (*rgb, 1)
    p.inputs['Emission Strength'].default_value = .7
    return m

MATS = [material('M_SpectralBody',(.016,.055,.55),.82),
        material('M_SpectralEdge',(.03,.27,1),.90),
        material('M_SpectralRunes',(.10,.50,1),.86)]
WAKE = material('M_SpectralWake',(.015,.32,.82),.18)

class Geometry:
    def __init__(self):
        self.v=[];self.f=[];self.slots=[];self.uv=[];self.smooth=[]

    def add(self, verts, faces, slot=0, smooth=False, uv=None):
        offset=len(self.v)
        self.v.extend(verts)
        self.f.extend(tuple(offset+i for i in f) for f in faces)
        self.slots.extend(slot if isinstance(slot,list) else [slot]*len(faces))
        self.smooth.extend([smooth]*len(faces))
        self.uv.extend(uv if uv is not None else [((x+30)/60,.5+y/10) for x,y,z in verts])

    def tube(self, points, radii, slot=1, sides=8):
        verts=[];faces=[]
        for j,p in enumerate(points):
            tangent=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])).normalized()
            axis=tangent.cross(Vector((0,0,1)))
            if axis.length<.01:axis=tangent.cross(Vector((0,1,0)))
            axis.normalize();cross=tangent.cross(axis).normalized()
            for k in range(sides):
                a=2*math.pi*k/sides
                verts.append(tuple(Vector(p)+radii[j]*(math.cos(a)*axis+math.sin(a)*cross)))
        for j in range(len(points)-1):
            for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k))
        faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))])
        self.add(verts,faces,slot,True)

    def object(self,name,mats):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(a*.01 for a in v) for v in self.v],[],self.f)
        for m in mats:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='SpectralLocal')
        for poly,slot,smooth in zip(mesh.polygons,self.slots,self.smooth):
            poly.material_index=slot;poly.use_smooth=smooth
            for loop in poly.loop_indices:uv.data[loop].uv=self.uv[mesh.loops[loop].vertex_index]
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
        return obj

g=Geometry()
# Continuous, fine beveled blade. No jagged crystal lumps or oversized root collar.
sections=[(-16,1.05,.23),(-14.4,1.48,.29),(-12,1.68,.31),(-8,1.64,.30),
          (-2,1.50,.28),(5,1.28,.25),(12,1.01,.21),(19,.69,.16),
          (24,.40,.11),(27,.18,.065),(29.45,.035,.018)]
vs=[];fs=[];ids=[]
for x,w,h in sections:
    # Two broad planes, shallow center spine, very narrow actual cutting bevel.
    cross=[(0,h),(.72*w,.52*h),(.96*w,.12*h),(w,0),(.96*w,-.12*h),(.72*w,-.52*h),
           (0,-h),(-.72*w,-.52*h),(-.96*w,-.12*h),(-w,0),(-.96*w,.12*h),(-.72*w,.52*h)]
    vs.extend((x,y,z) for y,z in cross)
for j in range(len(sections)-1):
    for k in range(12):
        fs.append((j*12+k,j*12+(k+1)%12,(j+1)*12+(k+1)%12,(j+1)*12+k))
        ids.append(1 if k in (2,3,8,9) else 0)
fs.append(tuple(reversed(range(12))));ids.append(0)
tip=len(vs);vs.append((30,0,0))
for k in range(12):fs.append(((len(sections)-1)*12+k,(len(sections)-1)*12+(k+1)%12,tip));ids.append(1)
g.add(vs,fs,ids)

def profile(x):
    for a,b in zip(sections,sections[1:]):
        if a[0]<=x<=b[0]:
            t=(x-a[0])/(b[0]-a[0]);return (a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t)
    return sections[0][1:]

# Fine glyph strokes sit on both faces, physically following the shallow ridge.
# They use the same X-based UV clock so light runs coherently toward the tip.
def glyph_path(coords,sign):
    points=[]
    for x,y in coords:
        w,h=profile(x);z=h*(1-.66*min(1,abs(y)/max(.01,w)))+.033
        points.append((x,y,sign*z))
    g.tube(points,[.033]*len(points),2,5)

for sign in (-1,1):
    for i,x in enumerate((-11,-6.5,-2,2.5,7,11.5,16,20)):
        w,h=profile(x);r=min(.42,w*.50)
        glyph_path([(x-1.0,0),(x,r),(x+1.0,0),(x,-r),(x-1.0,0)],sign)
        if i%2==0:glyph_path([(x-1.45,-r),(x-.65,0),(x-1.45,r)],sign)
    for a,b in ((-13,-12.3),(-9.6,-8),(-5.1,-3.5),(-.6,1),(3.9,5.5),(8.4,10),(12.9,14.5),(17.4,18.5)):
        glyph_path([(a,0),(b,0)],sign)

# Narrow swept, translucent guard; no metallic crossbar or thick oval plate.
for sign in (-1,1):
    points=[];radii=[]
    for i in range(21):
        t=i/20
        points.append((-16.55+1.8*t*t,sign*(.2+3.3*t),.04*math.sin(math.pi*t)))
        radii.append(.28*(1-t)**.65+.015)
    g.tube(points,radii,0,10)
    for zsign in (-1,1):
        g.tube([(x,y,z+zsign*r*.88) for (x,y,z),r in zip(points,radii)],
               [max(.014,r*.13) for r in radii],1,6)

# Slim spirit hilt with an open helix of light instead of a solid leather handle.
grip=[(-29.2,.11),(-28,.31),(-25,.37),(-21,.41),(-18,.44),(-16.5,.48)]
g.tube([(x,0,0) for x,r in grip],[r for x,r in grip],0,16)
helix=[]
for i in range(145):
    t=i/144;x=-28.8+11.7*t;r=.33+.13*t;a=t*math.tau*3.3
    helix.append((x,r*math.cos(a),r*math.sin(a)))
g.tube(helix,[.027]*len(helix),2,5)
g.tube([(-30,0,0),(-29.1,0,0),(-28.35,0,0)],[.005,.33,.15],1,12)
blade=g.object('SM_SpectralRuneBlade',MATS)

def ribbons(name,length,start,width,number):
    out=Geometry()
    for ribbon in range(number):
        verts=[];faces=[];uv=[];phase=ribbon*math.tau/number
        for i in range(33):
            t=i/32;a=phase+.65*t
            y=math.sin(t*math.pi*1.6+phase)*width*.6*t
            z=math.cos(t*math.pi*1.3+phase)*width*.45*t
            w=width*(.20+.80*math.sin(math.pi*(.10+.89*t)))*(1-t*.84)
            for side in (-1,1):
                verts.append((start-length*t,y+side*w*math.cos(a),z+side*w*math.sin(a)))
                uv.append((t,(side+1)/2))
        for i in range(32):faces.append((2*i,2*i+1,2*i+3,2*i+2))
        out.add(verts,faces,0,True,uv)
    return out.object(name,[WAKE])

trail=ribbons('SM_SpectralWake',28,-27.5,.82,3)
wisp=ribbons('SM_SpectralWisp',6.0,3.0,.42,2)
# Three crossed soft-disc planes: six triangles per particle, visible from any
# view without per-frame camera-facing work. Local X stretches into a streak.
particle_geo=Geometry()
for coords in [((-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)),
               ((-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1)),
               ((0,-1,-1),(0,1,-1),(0,1,1),(0,-1,1))]:
    particle_geo.add(coords,[(0,1,2,3)],uv=[(0,0),(1,0),(1,1),(0,1)])
particle=particle_geo.object('SM_SpectralImpactParticle',[material('M_SpectralImpact',(.035,.22,1),.85)])
for obj in (blade,trail,wisp,particle):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-X',axis_up='Y',apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',
        add_leaf_bones=False,path_mode='AUTO',use_mesh_modifiers=True)
bpy.ops.object.select_all(action='DESELECT');blade.select_set(True);bpy.context.view_layer.objects.active=blade
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SpectralRuneBlade.blend'))
(OUT/'authoring.json').write_text(json.dumps({
    'style':'User selected ghost-blue spectral sword, not solid crystal.',
    'provenance':'Original local procedural mesh and analytic material; no third-party source assets.',
    'length_cm':60,'blade_width_cm':3.36,'blade_max_thickness_cm':.62,'forward_axis':'+X',
    'materials':'Translucent Substrate unlit body, blue rim and object-locked flowing glyphs; UV0 follows blade length.',
    'meshes':{o.name:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons)} for o in (blade,trail,wisp,particle)},
    'rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SPECTRAL_AUTHOR_COMPLETE',str(OUT))
