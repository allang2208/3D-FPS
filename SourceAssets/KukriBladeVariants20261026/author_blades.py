"""Author three cosmetic game meshes from the accepted Kukri and bake their PBR.

Background asset production only. No gameplay, preview, or acceptance renders.
The final three renders are the actual selectable inventory attachment icons.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
BASE = P.parent / 'KukriModules20261026'
SOURCE = BASE / 'Kukri_Modules_Editable.blend'
TEXSOURCE = P.parent / 'Kukri20261020' / 'Textures'
DEST = '/Game/Weapons/Kukri20261020/BladeVariants20261026'
FROZEN_Z = .066  # All accepted wood/hand contact lies below this plane.
ZTIP = .2629057765007019
VARIANTS = [
    ('swift_blade', 'Swift', '轻型迅刃'),
    ('heavy_back_blade', 'HeavyBack', '厚背重刃'),
    ('folded_balanced_blade', 'FoldedBalanced', '百炼均衡刃'),
]
for folder in ('Export', 'Textures', 'Icons'):
    (P / folder).mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.bake.margin = 16
scene.render.bake.use_clear = True
scene.render.bake.use_selected_to_active = False
factory = bpy.data.objects['SM_Kukri_Blade_Factory']
source = factory.data
source.calc_loop_triangles()
corners = [(source.vertices[l.vertex_index].co.copy(), source.uv_layers.active.data[i].uv.copy(),
            Vector(source.corner_normals[i].vector)) for i, l in enumerate(source.loops)]
triangles = [[corners[i] for i in tri.loops] for tri in source.loop_triangles]

def midpoint(a, b):
    return (a[0].lerp(b[0], .5), a[1].lerp(b[1], .5), a[2].lerp(b[2], .5).normalized())

# Uniform subdivision retains the accepted surface and UVs, with shared edge samples.
for _ in range(2):
    refined = []
    for a, b, c in triangles:
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        refined.extend(((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)))
    triangles = refined

# Actual source cross sections define the profile coordinates; never derive the root
# interface from a whole-object bounding box.
sections = []
for i in range(401):
    z = FROZEN_Z + (ZTIP - FROZEN_Z) * i / 400
    xs = []
    for edge in source.edges:
        a, b = [source.vertices[j].co for j in edge.vertices]
        if min(a.z, b.z) <= z <= max(a.z, b.z) and abs(b.z-a.z) > 1e-9:
            xs.append(a.x + (b.x-a.x) * (z-a.z)/(b.z-a.z))
    if xs:
        sections.append((min(xs), max(xs)))
    else:
        tip = max(source.vertices, key=lambda v:v.co.z).co.x
        sections.append((tip, tip))

def sat(v): return min(1., max(0., v))
def smooth(a, b, value):
    t = sat((value-a)/(b-a))
    return t*t*(3-2*t)

def profile(z):
    t = sat((z-FROZEN_Z)/(ZTIP-FROZEN_Z))*400
    i = min(int(t), 399)
    k = t-i
    return tuple(sections[i][j]*(1-k)+sections[i+1][j]*k for j in range(2))

def deform(p, kind):
    if p.z <= FROZEN_Z:
        return p.copy()
    lo, hi = profile(p.z)
    center = (lo+hi)*.5
    q = sat((p.x-lo)/max(hi-lo, 1e-6))
    t = sat((p.z-FROZEN_Z)/(ZTIP-FROZEN_Z))
    fade = smooth(FROZEN_Z, .115, p.z)
    belly = math.sin(math.pi*t)
    if kind == 'Swift':
        width = 1-.27*fade*belly
        x = center+(p.x-center)*width-.0025*fade*belly
        y = p.y*(1-.18*fade)
        channel = math.exp(-((q-.24)/.075)**2)
        channel *= smooth(.105,.125,p.z)*(1-smooth(.215,.24,p.z))
        y -= math.copysign(.00065*channel*smooth(.001,.003,abs(p.y)), p.y)
    elif kind == 'HeavyBack':
        width = 1+.30*fade*belly
        x = center+(p.x-center)*width+.0035*fade*belly
        ridge = max(0., 1-abs(q-.25)/.33)
        y = p.y*(1+.30*fade*belly+.08*fade*ridge)
    else:
        width = 1+.055*fade*belly
        x = center+(p.x-center)*width-.001*fade*belly
        y = p.y*(1+.045*fade*belly)
    return Vector((x, y, p.z))

def normal_at(p, n, kind):
    if p.z <= FROZEN_Z:
        return n.copy()
    h = .000002
    columns = []
    for axis in range(3):
        delta = Vector(); delta[axis] = h
        columns.append((deform(p+delta,kind)-deform(p-delta,kind))/(2*h))
    jacobian = Matrix(columns).transposed()
    return (jacobian.inverted_safe().transposed() @ n).normalized()

def node(nt, typ, **values):
    obj = nt.nodes.new(typ)
    for key, value in values.items(): setattr(obj, key, value)
    return obj

def mathnode(nt, op, a, b):
    out = node(nt,'ShaderNodeMath',operation=op)
    for i,value in enumerate((a,b)):
        if hasattr(value,'node'): nt.links.new(value,out.inputs[i])
        else: out.inputs[i].default_value=value
    return out.outputs[0]

def mix(nt, amount, a, b):
    out = node(nt,'ShaderNodeMixRGB',blend_type='MIX')
    for i,value in enumerate((amount,a,b)):
        if hasattr(value,'node'): nt.links.new(value,out.inputs[i])
        else: out.inputs[i].default_value=value
    return out.outputs[0]

def image_node(nt, path, color=False):
    tex = node(nt,'ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(path),check_existing=True)
    tex.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return tex

def procedural_material(kind):
    mat=bpy.data.materials.new('M_Kukri_'+kind+'_Author'); mat.use_nodes=True
    nt=mat.node_tree; nt.nodes.clear()
    out=node(nt,'ShaderNodeOutputMaterial')
    bsdf=node(nt,'ShaderNodeBsdfPrincipled'); nt.links.new(bsdf.outputs[0],out.inputs['Surface'])
    attr=node(nt,'ShaderNodeVertexColor',layer_name='BladeData')
    split=node(nt,'ShaderNodeSeparateColor'); nt.links.new(attr.outputs['Color'],split.inputs['Color'])
    root_mix,bevel=split.outputs[0],split.outputs[1]
    tc=node(nt,'ShaderNodeTexCoord')
    scale=node(nt,'ShaderNodeVectorMath',operation='MULTIPLY')
    scale.inputs[1].default_value=(6500,6500,95) if kind=='Swift' else (230,230,230)
    nt.links.new(tc.outputs['Object'],scale.inputs[0])
    noise=node(nt,'ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=1
    noise.inputs['Detail'].default_value=2
    nt.links.new(scale.outputs[0],noise.inputs['Vector'])
    pattern=noise.outputs['Fac']
    if kind=='FoldedBalanced':
        wave=node(nt,'ShaderNodeTexWave',wave_type='BANDS',bands_direction='X')
        wave.inputs['Scale'].default_value=310
        wave.inputs['Distortion'].default_value=6
        wave.inputs['Detail'].default_value=3
        wave.inputs['Detail Scale'].default_value=1.3
        nt.links.new(tc.outputs['Object'],wave.inputs['Vector'])
        pattern=wave.outputs['Fac']
    colors={'Swift':(.075,.125),'HeavyBack':(.065,.105),'FoldedBalanced':(.25,.34)}
    a,b=colors[kind]
    body=mix(nt,pattern,(a,a,a,1),(b,b,b,1))
    metal=mix(nt,bevel,body,(.43,.44,.46,1))
    original=image_node(nt,TEXSOURCE/'T_Kukri_BaseColor.png',True)
    base=mix(nt,root_mix,original.outputs['Color'],metal)
    orm=image_node(nt,TEXSOURCE/'T_Kukri_ORM.png')
    old_channels=node(nt,'ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'],old_channels.inputs['Color'])
    rough_face=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',pattern,.09),.31 if kind!='HeavyBack' else .38)
    rough=mix(nt,bevel,rough_face,(.22,.22,.22,1))
    rough=mix(nt,root_mix,old_channels.outputs[1],rough)
    metallic=mix(nt,root_mix,old_channels.outputs[2],(.97,.97,.97,1))
    packed=node(nt,'ShaderNodeCombineColor')
    nt.links.new(old_channels.outputs[0],packed.inputs[0])
    nt.links.new(rough,packed.inputs[1]); nt.links.new(metallic,packed.inputs[2])
    bump=node(nt,'ShaderNodeBump')
    bump.inputs['Distance'].default_value=.000035 if kind!='HeavyBack' else .000065
    nt.links.new(mathnode(nt,'MULTIPLY',root_mix,.22),bump.inputs['Strength'])
    nt.links.new(pattern,bump.inputs['Height'])
    nt.links.new(base,bsdf.inputs['Base Color']); nt.links.new(rough,bsdf.inputs['Roughness'])
    nt.links.new(metallic,bsdf.inputs['Metallic']); nt.links.new(bump.outputs[0],bsdf.inputs['Normal'])
    return mat,{'BaseColor':base,'ORM':packed.outputs[0]},bsdf,out

def bake_maps(obj, kind):
    material,channels,bsdf,out=procedural_material(kind)
    obj.data.materials.clear();obj.data.materials.append(material)
    nt=material.node_tree
    emit=node(nt,'ShaderNodeEmission')
    tex_target=node(nt,'ShaderNodeTexImage')
    maps={}
    for suffix in ('BaseColor','ORM','Normal'):
        name='T_Kukri_'+kind+'_'+suffix
        img=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
        img.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        tex_target.image=img;nt.nodes.active=tex_target
        for n in nt.nodes:n.select=n==tex_target
        if suffix=='Normal':
            nt.links.new(bsdf.outputs[0],out.inputs['Surface'])
            bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
        else:
            nt.links.new(channels[suffix],emit.inputs['Color'])
            nt.links.new(emit.outputs[0],out.inputs['Surface'])
            bpy.ops.object.bake(type='EMIT')
        img.filepath_raw=str(P/'Textures'/(name+'.png'));img.file_format='PNG';img.save()
        maps[suffix]=img
    nt.links.new(bsdf.outputs[0],out.inputs['Surface'])
    # Keep procedural author material, but bind the exported/baked material for icons.
    runtime=bpy.data.materials.new('M_Kukri_'+kind);runtime.use_nodes=True
    rt=runtime.node_tree;rt.nodes.clear()
    bs=node(rt,'ShaderNodeBsdfPrincipled');output=node(rt,'ShaderNodeOutputMaterial')
    rt.links.new(bs.outputs[0],output.inputs['Surface'])
    for suffix in maps:
        tex=node(rt,'ShaderNodeTexImage');tex.image=maps[suffix]
        if suffix=='BaseColor':rt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif suffix=='ORM':
            sep=node(rt,'ShaderNodeSeparateColor');rt.links.new(tex.outputs['Color'],sep.inputs['Color'])
            rt.links.new(sep.outputs[1],bs.inputs['Roughness']);rt.links.new(sep.outputs[2],bs.inputs['Metallic'])
        else:
            normal=node(rt,'ShaderNodeNormalMap');rt.links.new(tex.outputs['Color'],normal.inputs['Color'])
            rt.links.new(normal.outputs[0],bs.inputs['Normal'])
    obj.data.materials[0]=runtime
    return {key:str(P/'Textures'/(img.name+'.png')) for key,img in maps.items()}

for obj in scene.objects:obj.hide_render=True;obj.hide_set(True)
receipt={'source':str(SOURCE),'interface':'kukri-grip-frame-v1-20261026',
         'frozen_root_max_z_cm':FROZEN_Z*100,'stats_authored':False,'runtime_tested':False,'variants':[]}
variants=[]
for part_id,kind,label in VARIANTS:
    verts,lookup,faces,loop_uv,loop_normals,attributes=[],{},[],[],[],[]
    normal_cache={}
    for tri in triangles:
        face=[]
        for co,uv,n in tri:
            key=tuple(round(v,8) for v in co)
            if key not in lookup:
                lookup[key]=len(verts);verts.append(tuple(deform(co,kind)))
            face.append(lookup[key]);loop_uv.append(uv)
            nk=key+tuple(round(v,6) for v in n)
            if nk not in normal_cache:normal_cache[nk]=tuple(normal_at(co,n,kind))
            loop_normals.append(normal_cache[nk])
            lo,hi=profile(co.z)
            attributes.append((smooth(.066,.102,co.z),1-smooth(.0024,.0037,abs(co.y)),
                               sat((co.x-lo)/max(hi-lo,1e-6)),1))
        faces.append(face)
    name='SM_Kukri_Blade_'+kind
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for i,value in enumerate(loop_uv):uv.data[i].uv=value
    attr=mesh.color_attributes.new(name='BladeData',type='FLOAT_COLOR',domain='CORNER')
    for i,value in enumerate(attributes):attr.data[i].color=value
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set(loop_normals)
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    maps=bake_maps(obj,kind)
    fbx=P/'Export'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,
        bake_space_transform=False,add_leaf_bones=False)
    receipt['variants'].append({'id':part_id,'name':label,'kind':kind,'object':name,
        'mesh':DEST+'/'+name+'.'+name,'material':DEST+'/Materials/M_Kukri_'+kind+'.M_Kukri_'+kind,
        'fbx':str(fbx),'textures':maps,'triangles':len(faces),'vertices':len(verts),
        'icon_key':'blade_1_'+part_id,'icon':str(P/'Icons'/('blade_1_'+part_id+'.png'))})
    obj.hide_render=True;obj.hide_set(True);variants.append(obj)
    (P/'variants.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BLADE_AUTHORED '+part_id,flush=True)

# Master contains all three alternatives at the real shared pivot, hidden by default.
variants[0].hide_set(False);variants[0].hide_render=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Blade_Variants_Editable.blend'))

import runpy
runpy.run_path(str(P/'render_icons.py'), run_name='__main__')
