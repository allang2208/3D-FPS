"""Author the reference-derived blue energy sword; export only, no review renders.

Reference: game-dev/assets/weapons/blue_energy_sword_pure.png (local project art).
Centimetre contract: tip +X, width Y, thickness Z, origin at overall midpoint.
The 2D silhouette is adapted into a beveled crystal volume, not texture-projected.
Run Blender 5.1 --background --factory-startup --python-exit-code 1 --python thisfile.
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
S = .01

def material(name, base, emission, strength, roughness):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*base, 1)
    p.inputs['Emission Color'].default_value = (*emission, 1)
    p.inputs['Emission Strength'].default_value = strength
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = .12
    return m

mats = [
    material('M_RuneBlade_Crystal', (.008,.10,.32), (.025,.25,1), .9,.20),
    material('M_RuneBlade_Edge', (.04,.38,.68), (.10,.70,1), 2.0,.18),
    material('M_RuneBlade_Core', (.48,.86,1), (.48,.86,1), 4.0,.20),
]
verts, faces, indices, smooth = [], [], [], []

def shape(vs, fs, mis=0, soft=False):
    offset = len(verts)
    verts.extend(vs)
    faces.extend(tuple(offset+i for i in f) for f in fs)
    indices.extend(mis if isinstance(mis,list) else [mis]*len(fs))
    smooth.extend([soft]*len(fs))

# Deliberately narrow and continuous from the ricasso to a long needle point.
sections = [(-16.1,1.18,.37),(-15.2,1.42,.43),(-13.7,1.87,.50),
            (-11.5,1.94,.51),(-5,1.86,.49),(3,1.65,.44),(11,1.36,.36),
            (18,1.02,.28),(23,.67,.19),(27,.30,.10),(29.3,.07,.03)]
vs, fs, mi = [], [], []
for x,w,t in sections:
    c = min(.115,w*.24)
    yz = [(c,t),(.56*w,.62*t),(.94*w,.13*t),(w,0),(.94*w,-.13*t),(.56*w,-.62*t),
          (c,-t),(-c,-t),(-.56*w,-.62*t),(-.94*w,-.13*t),(-w,0),(-.94*w,.13*t),(-.56*w,.62*t),(-c,t)]
    vs.extend((x,y,z) for y,z in yz)
n = 14
for ring in range(len(sections)-1):
    for k in range(n):
        fs.append((ring*n+k,ring*n+(k+1)%n,(ring+1)*n+(k+1)%n,(ring+1)*n+k))
        mi.append(2 if k in (6,13) else 1 if k in (2,3,9,10) else 0)
fs.append(tuple(reversed(range(n)))); mi.append(0)
tip=len(vs);vs.append((30,0,0))
for k in range(n):
    fs.append(((len(sections)-1)*n+k,(len(sections)-1)*n+(k+1)%n,tip))
    mi.append(2 if k in (6,13) else 1)
shape(vs,fs,mi)

def ellipsoid(center, radius, slot, segments=48, rings=16):
    vs,fs=[],[]
    # Non-degenerate poles; elliptical guard has a softly rounded lens silhouette.
    vs.append((center[0],center[1],center[2]+radius[2]))
    for j in range(1,rings):
        p=math.pi*j/rings
        for k in range(segments):
            a=2*math.pi*k/segments
            vs.append(tuple(center[i]+radius[i]*v for i,v in enumerate((math.sin(p)*math.cos(a),math.sin(p)*math.sin(a),math.cos(p)))))
    bottom=len(vs);vs.append((center[0],center[1],center[2]-radius[2]))
    for k in range(segments):
        fs.append((0,1+k,1+(k+1)%segments))
        for j in range(rings-2):
            a=1+j*segments+k;b=1+j*segments+(k+1)%segments
            fs.append((a,a+segments,b+segments,b))
        a=1+(rings-2)*segments
        fs.append((a+k,bottom,a+(k+1)%segments))
    shape(vs,fs,slot,True)

# A small luminous oval guard replaces the perpendicular block on the old mesh.
ellipsoid((-16.7,0,0),(.82,3.5,.48),1)
ellipsoid((-16.6,0,.39),(.34,2.95,.15),2,48,10)
ellipsoid((-16.6,0,-.39),(.34,2.95,.15),2,48,10)

# Swept crystal grip with restrained collar rings, no dark metal hilt.
def grip(profile,slot):
    vs,fs=[],[]
    n=24
    for x,r in profile:
        for k in range(n):
            a=2*math.pi*k/n
            vs.append((x,r*math.cos(a),r*.78*math.sin(a)))
    for j in range(len(profile)-1):
        for k in range(n):fs.append((j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k))
    fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+k for k in range(n))])
    shape(vs,fs,slot,True)

grip([(-28.4,.43),(-27.7,.55),(-26,.56),(-22,.60),(-19,.67),(-17.2,.73)],0)
for x,r in [(-27.6,.62),(-18,.77)]:
    grip([(x-.18,r*.85),(x-.10,r),(x+.10,r),(x+.18,r*.85)],1)
# Slim energy inlays follow the handle and retain the reference's white-blue spine.
for zsign in (-1,1):
    shape([(-27.9,-.095,zsign*.45),(-27.9,.095,zsign*.45),
           (-17.4,.10,zsign*.59),(-17.4,-.10,zsign*.59)],[(0,1,2,3)],2)
ellipsoid((-28.65,0,0),(1.35,.96,.74),1,32,12)
ellipsoid((-28.65,0,.62),(.58,.42,.16),2,24,10)
ellipsoid((-28.65,0,-.62),(.58,.42,.16),2,24,10)

def object_from_data(name,vs,fs,slots,material_indices,soft):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([Vector(v)*S for v in vs],[],fs)
    for mat in slots:mesh.materials.append(mat)
    for poly,idx,sm in zip(mesh.polygons,material_indices,soft):poly.material_index=idx;poly.use_smooth=sm
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    # Each part has actual UVs; the body shader also reads this local gradient.
    bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj

blade=object_from_data('SM_RuneOrbBlade',verts,faces,mats,indices,smooth)
shardmat=material('M_RuneBlade_Shards',(.015,.16,.48),(.035,.38,1),2.2,.16)
# A real asymmetrical triangular crystal splinter, 9 cm before burst scaling.
sv=[(-4.2,0,0),(-1.6,.75,.18),(-.9,.15,.67),(-1.0,-.65,.06),(-1.3,-.15,-.45),
    (2.4,.30,.05),(2.1,0,.28),(1.6,-.25,-.02),(2.0,0,-.19),(4.8,.03,.02)]
sf=[(0,2,1),(0,3,2),(0,4,3),(0,1,4),(1,2,6,5),(2,3,7,6),(3,4,8,7),(4,1,5,8),
    (5,6,9),(6,7,9),(7,8,9),(8,5,9)]
shard=object_from_data('SM_RuneBladeShard',sv,sf,[shardmat],[0]*len(sf),[False]*len(sf))

for obj in (blade,shard):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # Match the already-established orbit blade import axes and centimetre unit conversion.
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-X',axis_up='Y',apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',
        add_leaf_bones=False,path_mode='AUTO',use_mesh_modifiers=True)
bpy.ops.object.select_all(action='DESELECT');blade.select_set(True);bpy.context.view_layer.objects.active=blade
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RuneEnergyBlade.blend'))
(OUT/'authoring.json').write_text(json.dumps({
    'reference':'E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/weapons/blue_energy_sword_pure.png',
    'provenance':'Existing local game-dev art; newly authored mesh; no downloaded geometry or textures.',
    'reference_identity':'Long blue double edged blade, white central ridge, tiny oval guard, luminous slim grip and rounded pommel.',
    'reconstruction':'Thickness and rear-face details inferred from a single 2D reference.',
    'length_cm':60,'guard_span_cm':7,'blade_span_cm':3.88,'blade_max_thickness_cm':1.02,
    'forward_axis':'+X','up_axis':'+Z','burst_fragment_length_cm':9,
    'meshes':{o.name:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons)} for o in (blade,shard)},
    'rendered':False
},indent=2,ensure_ascii=False),encoding='utf-8')
print('RUNE_BLADE_AUTHOR_COMPLETE',str(OUT))
