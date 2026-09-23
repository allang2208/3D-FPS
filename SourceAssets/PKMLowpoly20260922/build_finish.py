"""Source-preserving surface development. Texture baking is production, not a preview render."""
import bpy, json, pathlib, math, struct
from mathutils import Matrix, Vector

ROOT=pathlib.Path(__file__).parent
CFG=json.loads((ROOT/'finish_settings.json').read_text(encoding='utf-8'))
OUT=ROOT/'Refinement01'
TEX=OUT/'Textures'
TEX.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Original'/'PKM_Source.blend'))
parts=list(o for o in bpy.context.scene.objects if o.type=='MESH')
source_mats={m.name:m for m in bpy.data.materials}

# Flatten only the import conversion hierarchy. Meshes and their UVs remain separate.
for o in parts:
    world=o.matrix_world.copy()
    o.parent=None
    o.matrix_world=world
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
for o in list(bpy.data.objects):
    if o.type=='EMPTY':bpy.data.objects.remove(o,do_unlink=True)

assembly=bpy.data.objects.new('PKM_Lowpoly_Assembly',None)
bpy.context.collection.objects.link(assembly)
for o in parts:
    world=o.matrix_world.copy();o.parent=assembly;o.matrix_world=world
    sid=int(o.name.rsplit('_',1)[1]);o['source_part_id']=sid
    o.name='PKM_Part_%03d'%sid
    if sid in CFG['bevel_source_parts']:
        bevel=o.modifiers.new('NearView_MicroBevel','BEVEL')
        bevel.width=CFG['bevel_width_m'];bevel.segments=CFG['bevel_segments']
        bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(CFG['bevel_angle_degrees'])
        bevel.use_clamp_overlap=True;bevel.harden_normals=True
        weighted=o.modifiers.new('Planar_WeightedNormals','WEIGHTED_NORMAL')
        weighted.keep_sharp=True;weighted.weight=50
        o['surface_operation']='0.18 mm limited angle bevel and weighted normals; original mesh retained'
    else:o['surface_operation']='Original geometry and custom normals retained'

# Texture tiles are baked from explicit periodic fields, retaining the source UV layout.
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.bake.margin=0
for o in parts:o.hide_render=True
bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,3))
plane=bpy.context.object;plane.name='TextureAuthoringPlane'
finished=[]

def node(nt,kind):return nt.nodes.new(kind)
def mathnode(nt,op,a=None,b=None):
    n=node(nt,'ShaderNodeMath');n.operation=op
    for idx,val in enumerate([a,b]):
        if val is None:continue
        if isinstance(val,(float,int)):n.inputs[idx].default_value=val
        else:nt.links.new(val,n.inputs[idx])
    return n.outputs[0]

for spec in CFG['materials']:
    author=bpy.data.materials.new(spec['name']+'_Author');author.use_nodes=True
    nt=author.node_tree;nt.nodes.clear()
    uv=node(nt,'ShaderNodeTexCoord');sep=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(uv.outputs['UV'],sep.inputs[0])
    x,y=sep.outputs['X'],sep.outputs['Y']
    # Integer frequencies ensure an exactly repeating field at both tile boundaries.
    slow=mathnode(nt,'SINE',mathnode(nt,'MULTIPLY',y,math.tau*2))
    warp=mathnode(nt,'MULTIPLY',slow,2.3 if spec['wood'] else 0.35)
    band=mathnode(nt,'SINE',mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',x,math.tau*(22 if spec['wood'] else 47)),warp))
    fine=mathnode(nt,'MULTIPLY',mathnode(nt,'SINE',mathnode(nt,'MULTIPLY',x,math.tau*117)),mathnode(nt,'SINE',mathnode(nt,'MULTIPLY',y,math.tau*131)))
    field=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',band,0.36 if spec['wood'] else 0.08),mathnode(nt,'MULTIPLY',fine,0.07))
    field=mathnode(nt,'ADD',field,0.5)
    ramp=node(nt,'ShaderNodeValToRGB')
    for e,scale in zip(ramp.color_ramp.elements,[0.65 if spec['wood'] else 0.92,1.3 if spec['wood'] else 1.08]):
        e.color=(*[min(1,c*scale) for c in spec['color']],1)
    nt.links.new(field,ramp.inputs[0])
    rough=mathnode(nt,'ADD',spec['roughness'],mathnode(nt,'MULTIPLY',mathnode(nt,'SUBTRACT',field,0.5),spec['variation']*2))
    bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=spec['bump_m'];bump.inputs['Strength'].default_value=0.35
    nt.links.new(field,bump.inputs['Height'])
    bsdf=node(nt,'ShaderNodeBsdfPrincipled');nt.links.new(ramp.outputs['Color'],bsdf.inputs['Base Color']);nt.links.new(rough,bsdf.inputs['Roughness']);nt.links.new(bump.outputs[0],bsdf.inputs['Normal'])
    bsdf.inputs['Metallic'].default_value=spec['metallic']
    output=node(nt,'ShaderNodeOutputMaterial');emit=node(nt,'ShaderNodeEmission')
    plane.data.materials.clear();plane.data.materials.append(author)
    maps={}
    for channel,socket in [('BaseColor',ramp.outputs['Color']),('Roughness',rough),('Normal',None)]:
        img=bpy.data.images.new(spec['name']+'_'+channel,width=spec['resolution'],height=spec['resolution'],alpha=False)
        img.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        target=node(nt,'ShaderNodeTexImage');target.image=img;nt.nodes.active=target
        if channel=='Normal':
            nt.links.new(bsdf.outputs[0],output.inputs['Surface'])
            bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',use_clear=True)
        else:
            nt.links.new(socket,emit.inputs['Color']);nt.links.new(emit.outputs[0],output.inputs['Surface'])
            bpy.ops.object.bake(type='EMIT',use_clear=True)
        img.filepath_raw=str(TEX/(img.name+'.png'));img.file_format='PNG';img.save()
        maps[channel]=img
    mat=bpy.data.materials.new(spec['name']);mat.use_nodes=True
    mat.diffuse_color=(*spec['color'],1);mat.metallic=spec['metallic'];mat.roughness=spec['roughness']
    n=mat.node_tree;bs=next(x for x in n.nodes if x.type=='BSDF_PRINCIPLED');bs.inputs['Metallic'].default_value=spec['metallic']
    bs.inputs['Roughness'].default_value=spec['roughness']
    for channel,img in maps.items():
        t=n.nodes.new('ShaderNodeTexImage');t.image=img;t.extension='REPEAT'
        if channel=='Normal':
            normal=n.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=0.3
            n.links.new(t.outputs['Color'],normal.inputs['Color']);n.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:n.links.new(t.outputs['Color'],bs.inputs['Base Color' if channel=='BaseColor' else 'Roughness'])
    for o in parts:
        for slot in o.material_slots:
            if slot.material==source_mats[spec['source']]:slot.material=mat
    finished.append(dict(name=spec['name'],metallic=spec['metallic'],maps={k:str(pathlib.Path(v.filepath_raw).relative_to(OUT)) for k,v in maps.items()}))
    # Keep editable author nodes without exporting the bake plane.
    author.use_fake_user=True
    print('MATERIAL_COMPLETE',spec['name'],flush=True)

bpy.data.objects.remove(plane,do_unlink=True)
for o in parts:o.hide_render=False
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
assembly.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
# Store an editable assembly. UVs, parts, and original surface normals remain available.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PKM_Lowpoly_Refined.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'PKM_Lowpoly_Refined.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'PKM_Lowpoly_Refined.fbx'),use_selection=True,object_types={'MESH','EMPTY'},use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='RELATIVE')
deps=bpy.context.evaluated_depsgraph_get()
output_triangles=sum(sum(len(p.vertices)-2 for p in o.evaluated_get(deps).data.polygons) for o in parts)
receipt=dict(source_triangles=113206,output_triangles=output_triangles,source_meshes=141,beveled_parts=CFG['bevel_source_parts'],materials=finished,source_preserved=True,animations_created=False,runtime_integrated=False,visual_tested=False)
(OUT/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('PKM_REFINEMENT_COMPLETE',str(OUT),flush=True)
