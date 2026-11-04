"""Split accepted hatchet; adapt shared knife finishes to its real mating surfaces.

Reuses the established Kukri clipping, UV/corner-normal and material authoring
helpers. Only newly exposed cuts are capped. No gameplay or acceptance render.
"""
import ast, bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
P=Path(__file__).resolve().parent
SOURCE=P.parent/'TacticalHatchet_Editable.blend'
SA=P.parents[1]
ROOT='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
TOP=.115
BOTTOM=-.0775
for folder in ('Export','Textures','IconInputs','Icons','Before'):(P/folder).mkdir(exist_ok=True)
sys.path.insert(0,str(SA/'KukriComponentVariants20261026'))
from asset_tools import *

def reuse_functions(path,names,replace=()):
    text=path.read_text(encoding='utf-8-sig')
    for old,new in replace:text=text.replace(old,new)
    tree=ast.parse(text)
    code=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
    exec(compile(code,str(path),'exec'),globals())

reuse_functions(SA/'KukriModules20261026/author_modules.py',{'clip'})

def split_closed(polys,above):
    # Meshy's UV-split vertices include sub-micron duplicates. Canonicalize only
    # this newly created interface, with a 0.005 mm weld; retain corner UV/normals.
    epsilon=.000005;cells={};points=[];result=[];edges=set();attrs={}
    def canonical(co):
        cell=tuple(math.floor(v/epsilon) for v in co)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for i in cells.get((cell[0]+dx,cell[1]+dy,cell[2]+dz),[]):
                        if (points[i]-co).length<=epsilon:return i
        i=len(points);points.append(co.copy());cells.setdefault(cell,[]).append(i);return i
    for poly in polys:
        cut=clip(poly,above)
        if len(cut)<3:continue
        corrected=[];ids=[]
        for co,uv,n in cut:
            if abs(co.z-CUT)<1e-8:
                i=canonical(co);corrected.append((points[i],uv,n));ids.append(i);attrs.setdefault(i,uv)
            else:corrected.append((co,uv,n));ids.append(None)
        result.append(corrected)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            if a is not None and b is not None and a!=b:edges.add(tuple(sorted((a,b))))
    adjacency={}
    for a,b in edges:adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    bad=[i for i,neighbors in adjacency.items() if len(neighbors)!=2]
    if bad:raise RuntimeError('Non-simple interface at '+str(CUT)+': '+str([(tuple(points[i]),len(adjacency[i])) for i in bad][:30]))
    remaining=set(adjacency);loops=[]
    while remaining:
        start=min(remaining);loop=[];previous=None;current=start
        while True:
            loop.append(current);remaining.discard(current)
            following=next(k for k in sorted(adjacency[current]) if k!=previous)
            previous,current=current,following
            if current==start:break
        loops.append(loop)
    n=Vector((0,0,-1 if above else 1))
    for loop in loops:
        coords=[points[i] for i in loop];center=sum(coords,Vector())/len(coords)
        uvcenter=sum((attrs[i] for i in loop),Vector((0,0)))/len(loop)
        for tri in tessellate_polygon([coords]):
            tri=[coords[i] for i in tri] if isinstance(tri[0],int) else list(tri)
            if (tri[1]-tri[0]).cross(tri[2]-tri[0]).dot(n)<0:tri.reverse()
            result.append([(p.copy(),uvcenter+Vector((p.x-center.x,p.y-center.y))*2,n.copy()) for p in tri])
    return result,[[list(points[i]*100) for i in loop] for loop in loops]
reuse_functions(SA/'KukriGripSurfaceV220261027/author_surfaces.py',{'scale_vector','noise','clamp','ramp','author_material'},[
    ('T_Kukri_BaseColor.png','source_image_01.png'),('T_Kukri_ORM.png','source_image_02.png'),('T_Kukri_Normal.png','source_image_00.png'),
    ("op(nt, 'MULTIPLY', old.outputs[0],", "op(nt, 'MULTIPLY', 1.,")])
BASE=P.parent/'Textures'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source=bpy.data.objects['SM_TacticalHatchet'];mesh=source.data
# Snapshot corrected author normals before any split or geometry edit.
normals=[Vector(n.vector) for n in mesh.corner_normals]
polygons=[[(mesh.vertices[mesh.loops[i].vertex_index].co.copy(),mesh.uv_layers.active.data[i].uv.copy(),normals[i].copy()) for i in p.loop_indices] for p in mesh.polygons]
CUT=TOP
head,head_ring=split_closed(polygons,True)
lower,_=split_closed(polygons,False)
CUT=BOTTOM
grip,tail_ring=split_closed(lower,True)
tail,_=split_closed(lower,False)
origins={'blade_1':Vector(),'grip':Vector((0,0,TOP)),'pommel':Vector((0,0,BOTTOM))}
names={'blade_1':'Head','grip':'Grip','pommel':'Pommel'}
receipt={'source':str(SOURCE),'normal_convention':'OpenGL tangent; UE green flip',
    'interface':'hatchet-factory-cuts-v1','head_cut_z_cm':TOP*100,'pommel_cut_z_cm':BOTTOM*100,
    'interfaces':{'head_grip_rings_cm':head_ring,'grip_pommel_rings_cm':tail_ring},
    'factory':{},'variants':[],'runtime_tested':False}

def mesh_from_polys(slot,polys):
    verts=[];lookup={};faces=[];corners=[]
    for poly in polys:
        face=[];kept=[]
        for co,uv,n in poly:
            key=tuple(round(v,7) for v in co)
            if key not in lookup:lookup[key]=len(verts);verts.append(tuple(co-origins[slot]))
            index=lookup[key]
            if face and face[-1]==index:continue
            face.append(index);kept.append((uv,n))
        if len(face)>1 and face[0]==face[-1]:face.pop();kept.pop()
        if len(face)<3 or len(set(face))!=len(face):continue
        a,b,c=[Vector(verts[i]) for i in face[:3]]
        if (b-a).cross(c-a).length<1e-14:continue
        faces.append(face);corners.extend(kept)
    name='SM_TacticalHatchet_'+names[slot]+'_Factory'
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    for label in ('UVMap','SourceUV'):
        layer=data.uv_layers.new(name=label)
        for i,(uv,n) in enumerate(corners):layer.data[i].uv=uv
    data.uv_layers.active_index=0;data.uv_layers[0].active_render=True
    for poly in data.polygons:poly.use_smooth=True
    print('AUTHOR_NORMALS '+slot+' faces='+str(len(faces)),flush=True)
    data.normals_split_custom_set([tuple(n) for uv,n in corners])
    data.materials.append(mesh.materials[0])
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    return obj

def emit(obj,slot,option,texture_maps=None):
    activate(obj);obj.location=Vector()
    fbx=P/'Export'/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False)
    obj.location=origins[slot]
    entry={'slot':slot,'id':option,'object':obj.name,'mesh':ROOT+'/'+obj.name+'.'+obj.name,
        'fbx':str(fbx),'origin_cm':list(origins[slot]*100),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
        'material_slot':obj.data.materials[0].name,'textures':texture_maps}
    if option=='factory':receipt['factory'][slot]=entry
    else:receipt['variants'].append(entry)
    (P/'modules.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    obj.hide_render=True;obj.hide_set(True)

for o in bpy.context.scene.objects:o.hide_render=True;o.hide_set(True)
factory={slot:mesh_from_polys(slot,polys) for slot,polys in [('blade_1',head),('grip',grip),('pommel',tail)]}
for slot,obj in factory.items():emit(obj,slot,'factory')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'

def tail_deform(kind):
    def deform(p):
        q=p.copy();f=(1-smooth(-.007,-.003,p.z))*smooth(.0045,.007,abs(p.y))
        if kind=='PommelFaceted':q.y-=math.copysign(.00065*f*max(0.,1-abs(p.x-.004)/.026),p.y)
        elif kind=='PommelRinged':
            bands=sum(math.exp(-((p.z-z)/.00055)**2) for z in (-.020,-.024,-.028))
            q.y-=math.copysign(.00025*f*bands,p.y)
        return q
    return deform

def tail_material(kind):
    m,nt,bs,out=make_mat('Author_Hatchet_'+kind)
    tc=node(nt,'ShaderNodeTexCoord');xyz=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],xyz.inputs[0]);z=xyz.outputs[2]
    region=op(nt,'SUBTRACT',1,ramp(nt,z,-.005,-.001))
    original=tex(nt,BASE/'source_image_01.png',True,'SourceUV')
    oldtex=tex(nt,BASE/'source_image_02.png',False,'SourceUV');old=node(nt,'ShaderNodeSeparateColor');nt.links.new(oldtex.outputs[0],old.inputs[0])
    grain=noise(nt,tc.outputs['Object'],850,2)
    if kind=='PommelSteel':color=mix(nt,grain,(.22,.24,.25,1),(.34,.35,.36,1));metal=.97;rough=.29
    elif kind=='PommelFaceted':color=mix(nt,grain,(.12,.055,.019,1),(.27,.15,.054,1));metal=.94;rough=.34
    else:
        band=0.
        for height in (-.020,-.024,-.028):
            band=op(nt,'MAXIMUM',band,op(nt,'SUBTRACT',1,ramp(nt,op(nt,'ABSOLUTE',op(nt,'SUBTRACT',z,height)),.00055,.0011)))
        color=mix(nt,band,(.055,.061,.067,1),(.38,.39,.40,1));metal=.96;rough=.32
    base=mix(nt,region,original.outputs[0],color)
    roughness=mix(nt,region,old.outputs[1],(rough,rough,rough,1))
    metallic=mix(nt,region,old.outputs[2],(metal,metal,metal,1))
    packed=node(nt,'ShaderNodeCombineColor');packed.inputs[0].default_value=1
    put(nt,packed.inputs[1],roughness);put(nt,packed.inputs[2],metallic)
    oldnormal=tex(nt,BASE/'source_image_00.png',False,'SourceUV');nm=node(nt,'ShaderNodeNormalMap',uv_map='SourceUV');nt.links.new(oldnormal.outputs[0],nm.inputs['Color'])
    geo=node(nt,'ShaderNodeNewGeometry');normal=mix(nt,region,nm.outputs[0],geo.outputs['Normal'])
    bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=.00004
    put(nt,bump.inputs['Strength'],region);put(nt,bump.inputs['Height'],grain);put(nt,bump.inputs['Normal'],normal)
    for socket,value in [('Base Color',base),('Metallic',metallic),('Roughness',roughness),('Normal',bump.outputs[0])]:put(nt,bs.inputs[socket],value)
    return m,{'BaseColor':base,'ORM':packed.outputs[0]},bs,out

plans=[('grip','knife_grip_checkered','GripCheckered'),('grip','knife_grip_leather','GripLeather'),('grip','knife_grip_laminate','GripLaminate'),
       ('pommel','knife_pommel_steel','PommelSteel'),('pommel','knife_pommel_faceted','PommelFaceted'),('pommel','knife_pommel_ringed','PommelRinged')]
for slot,option,kind in plans:
    obj=derived_mesh(factory[slot].data,'SM_TacticalHatchet_'+kind,tail_deform(kind) if slot=='pommel' else lambda p:p.copy(),levels=0)
    unwrap(obj)
    material=author_material(kind) if slot=='grip' else tail_material(kind)
    obj.data.materials.append(material[0])
    maps=bake(obj,[material],'T_TacticalHatchet_'+kind,P/'Textures',2048 if slot=='grip' else 1024)
    emit(obj,slot,option,maps)
for obj in factory.values():obj.hide_render=False;obj.hide_set(False)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_Modules_Editable.blend'))
print('HATCHET_MODULES_AUTHORED factory=3 variants=6')
