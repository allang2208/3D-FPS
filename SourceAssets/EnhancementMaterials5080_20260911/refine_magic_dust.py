"""Authored physical reconstruction from approved turnaround; NOT raw TRELLIS output.
The separate raw 5080 models remain untouched for quality comparison.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
random.seed(91102)
bpy.ops.wm.read_factory_settings(use_empty=True)
def material(name,color,metal,rough,trans=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.46
    return m
glass=material('Thick clear glass',(0.96,.985,1),0,.065,1)
steel=material('Weathered silver steel',(.32,.35,.38),.92,.31)
powder=material('Fine silver mineral powder',(.43,.47,.50),.13,.83)
crystal=material('Pale blue mineral grains',(.65,.83,.95),.05,.21,.35)
def micro(m,scale,strength,distance):
    nt=m.node_tree; p=nt.nodes.get('Principled BSDF'); noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=3
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=strength;bump.inputs['Distance'].default_value=distance
    nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
micro(steel,130,.28,.00006);micro(powder,230,.5,.00015)
def mesh(name,verts,faces,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
    for poly in me.polygons: poly.use_smooth=True
    return o
def square_xy(angle,r):
    c=math.cos(angle);s=math.sin(angle)
    return (math.copysign(abs(c)**.4,c)*r,math.copysign(abs(s)**.4,s)*r)
def vessel():
    outer=[(.015,.34),(.025,.38),(.045,.412),(.075,.425),(.59,.425),(.625,.42),(.655,.40),(.69,.34),(.72,.30),(.745,.292),(.805,.292)]
    inner=[(.805,.278),(.745,.278),(.725,.285),(.701,.328),(.66,.388),(.625,.407),(.59,.412),(.083,.412),(.061,.393),(.051,.36)]
    profile=outer+inner;verts=[];n=128
    for z,r in profile:
        # blend rounded square body into circular neck
        t=max(0,min(1,(z-.63)/.10))
        for i in range(n):
            a=2*math.pi*i/n;x,y=square_xy(a,r);verts.append((x*(1-t)+r*math.cos(a)*t,y*(1-t)+r*math.sin(a)*t,z))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple((len(profile)-1)*n+i for i in range(n)))
    return mesh('Glass vessel with interior wall',verts,faces,glass)
vessel()
def lid():
    profile=[(.79,.287),(.798,.326),(.808,.331),(.819,.322),(.83,.318),(.927,.318),(.931,.324),(.936,.324),(.986,.324),(.991,.324),(.996,.31),(1.0,.285)]
    n=384;verts=[]
    for z,r in profile:
        for i in range(n):
            a=2*math.pi*i/n; rr=r+(.0035*math.cos(a*96) if .935<z<.99 else 0);verts.append((rr*math.cos(a),rr*math.sin(a),z))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces+=[tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))]
    mesh('Closed steel lid with geometric knurling',verts,faces,steel)
lid()
def surface(x,y):return .45+.21*math.exp(-((x+.11)**2+(y-.07)**2)/.054)+.004*math.sin(x*61)*math.sin(y*54)
verts=[(0,0,surface(0,0))];faces=[];n=96;rings=24
for j in range(1,rings+1):
    for i in range(n):
        x,y=square_xy(2*math.pi*i/n,.397*j/rings);verts.append((x,y,surface(x,y)))
for i in range(n):faces.append((0,1+i,1+(i+1)%n))
for j in range(rings-1):
    for i in range(n):faces.append((1+j*n+i,1+j*n+(i+1)%n,1+(j+1)*n+(i+1)%n,1+(j+1)*n+i))
start=len(verts)
for i in range(n):
    x,y=square_xy(2*math.pi*i/n,.397);verts.append((x,y,.065))
for i in range(n):faces.append((1+(rings-1)*n+i,start+i,start+(i+1)%n,1+(rings-1)*n+(i+1)%n))
faces.append(tuple(reversed(range(start,start+n))))
mesh('Contained powder volume',verts,faces,powder)
def grains(count,name,mat,minsize,maxsize,side=False):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1)
    template=bpy.context.object;tv=[v.co.copy() for v in template.data.vertices];tf=[tuple(p.vertices) for p in template.data.polygons];bpy.data.objects.remove(template,do_unlink=True)
    vv=[];ff=[]
    for j in range(count):
        while True:
            x=random.uniform(-.389,.389);y=random.uniform(-.389,.389)
            if (abs(x)/.392)**5+(abs(y)/.392)**5<1:break
        size=random.uniform(minsize,maxsize);z=surface(x,y)+size*.25;offset=len(vv)
        if side:
            x,y=square_xy(random.uniform(0,2*math.pi),.397)
            z=random.uniform(.069,surface(x,y)-.004)
        aspect=random.uniform(.7,1.6)
        vv.extend([(x+v.x*size,y+v.y*size,z+v.z*size*aspect) for v in tv]);ff.extend([tuple(offset+i for i in f) for f in tf])
    mesh(name,vv,ff,mat)
grains(1800,'Individual powder grains',powder,.0015,.004)
grains(5000,'Packed powder side grains',powder,.001,.003,True)
grains(95,'Embedded crystalline mineral fragments',crystal,.006,.016)
# Source dimensions are deliberately explicit and editable; 16 cm candidate height.
for o in list(bpy.context.scene.objects):o.scale*=.16
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'magic_dust_physical_editable.blend'))
bpy.ops.export_scene.gltf(filepath=str(P/'magic_dust_physical_candidate.glb'),export_format='GLB')
(P/'magic_dust_physical_provenance.json').write_text(json.dumps({'method':'Authored physical reconstruction from generated turnaround, not unmodified 5080 output','height_m':.16,'parts':[o.name for o in bpy.context.scene.objects],'procedural_micro_bump':'Editable Blender only; GLB preserves geometry and scalar PBR, micro bump needs baking for engine use'},indent=2))
