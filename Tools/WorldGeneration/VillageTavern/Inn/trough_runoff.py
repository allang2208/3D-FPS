"""Fitted ground wear on the grass side of the westernmost feed crib."""
import json
import math

from fit_inn import ROOT, STABLE, TAVERN, REPAIRED, component, require, state, u
from inn_forecourt import relief
from trough_profile import BOUNDS, MASK_NAME

PACKAGE = TAVERN+'Inn/'
MESH = PACKAGE+'SM_InnTroughRunoff'
MATERIAL = PACKAGE+'M_InnTroughRunoff'
TEXTURE = PACKAGE+'T_InnTroughRunoff'
TAG = 'VillageTavern.TroughRunoff'
SOURCE = ROOT/'SourceAssets/HillsVillageTavern/Inn'


def west_crib(site):
    """Use the actual repaired instances. Their mesh pivot is off-centre."""
    frame = site.get_actor_transform()
    ends = []
    for part in site.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh = part.static_mesh
        if not mesh or REPAIRED not in map(str,part.component_tags):
            continue
        if mesh.get_path_name().split('.')[0] != STABLE+'HayCrib':
            continue
        bounds = mesh.get_bounding_box()
        face = u.Vector(bounds.min.x, (bounds.min.y+bounds.max.y)*.5, bounds.min.z)
        for i in range(part.get_instance_count()):
            end = u.MathLibrary.transform_location(part.get_instance_transform(i,True),face)
            ends.append(u.MathLibrary.inverse_transform_location(frame,end))
    if not ends:
        raise RuntimeError('Missing repaired feed crib in House 02')
    return min(ends,key=lambda p:p.x)


def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())


def make_material():
    task = u.AssetImportTask()
    task.filename = str(SOURCE/MASK_NAME)
    task.destination_path, task.destination_name = TEXTURE.rsplit('/',1)
    task.automated = task.replace_existing = True
    task.save = False
    tools = u.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([task])
    tex = next((obj for obj in task.get_objects() if obj.get_path_name().split('.')[0]==TEXTURE),None)
    if not tex:
        raise RuntimeError('Missing imported runoff profile')
    tex.srgb = False
    tex.compression_settings = u.TextureCompressionSettings.TC_MASKS
    tex.compression_no_alpha = False
    tex.address_x = tex.address_y = u.TextureAddress.TA_CLAMP
    save(tex)
    mat = u.load_asset(MATERIAL) if u.EditorAssetLibrary.does_asset_exist(MATERIAL) else tools.create_asset(
        MATERIAL.rsplit('/',1)[1],PACKAGE.rstrip('/'),u.Material,u.MaterialFactoryNew())
    mat.modify()
    edit = u.MaterialEditingLibrary
    edit.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(cls):
        return edit.create_material_expression(mat,cls)
    def wire(a,pin,b,target):
        if not edit.connect_material_expressions(a,pin,b,target):
            raise RuntimeError('Cannot connect '+target)
    def output(a,pin,prop):
        if not edit.connect_material_property(a,pin,prop):
            raise RuntimeError('Cannot connect '+str(prop))
    def sample(texture,uv=None):
        n = node(u.MaterialExpressionTextureSample)
        n.texture = texture
        if texture.compression_settings==u.TextureCompressionSettings.TC_NORMALMAP:
            n.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_NORMAL
        elif texture.compression_settings==u.TextureCompressionSettings.TC_MASKS:
            n.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_MASKS
        elif not texture.srgb:
            n.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        if uv:
            wire(uv,'',n,'UVs')
        return n
    def custom(label,code,inputs):
        n=node(u.MaterialExpressionCustom)
        n.set_editor_property('description',label)
        n.set_editor_property('code',code)
        n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins=[]
        for name,_,_ in inputs:
            p=u.CustomInput()
            p.set_editor_property('input_name',name)
            pins.append(p)
        n.set_editor_property('inputs',pins)
        for name,a,channel in inputs:
            wire(a,channel,n,name)
        return n
    uv = node(u.MaterialExpressionTextureCoordinate)
    x0,x1,y0,y1=BOUNDS
    uv.u_tiling,uv.v_tiling=(x1-x0)/94.,(y1-y0)/94.
    weights = sample(tex)
    soil = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    mud = sample(require(soil+'B'),uv)
    sand = sample(require('/Game/WaterMaterials/Textures/T_Sand'),uv)
    grain = sample(require(soil+'N'),uv)
    color = custom('Wet loam to deposited sand',
        'float3 fines=lerp(Earth,Sand*float3(.85,.74,.61),.70);\n'
        'return lerp(fines,Earth*float3(.47,.43,.39),Wet);',
        [('Earth',mud,'RGB'),('Sand',sand,'RGB'),('Wet',weights,'G')])
    slopes=node(u.MaterialExpressionAppendVector)
    wire(weights,'B',slopes,'A')
    wire(weights,'A',slopes,'B')
    normal = custom('Shallow bed and softened soil grain',
        'return normalize(float3((Slope*2-1)+Grain.xy*lerp(.43,.19,Wet),1));',
        [('Slope',slopes,''),('Grain',grain,'RGB'),('Wet',weights,'G')])
    rough = node(u.MaterialExpressionLinearInterpolate)
    rough.set_editor_property('const_a',.89)
    rough.set_editor_property('const_b',.47)
    wire(weights,'G',rough,'Alpha')
    props = u.MaterialProperty
    output(weights,'R',props.MP_OPACITY)
    output(color,'',props.MP_BASE_COLOR)
    output(normal,'',props.MP_NORMAL)
    output(rough,'',props.MP_ROUGHNESS)
    edit.layout_material_expressions(mat)
    edit.recompile_material(mat)
    save(mat)
    return mat


def make_surface(site,end,material,plan):
    # Fit each vertex to the same village relief as the rendered terrain.
    # The very small clearance is for the mesh decal, not a raised walking surface.
    ground = relief(plan)
    frame = site.get_actor_transform()
    x0,x1,y0,y1 = BOUNDS
    nx,ny = math.ceil((x1-x0)/25),math.ceil((y1-y0)/25)
    vertices,uvs,triangles = [],[],[]
    for j in range(ny+1):
        for i in range(nx+1):
            s,t = i/nx,j/ny
            x,y = x0+(x1-x0)*s,y0+(y1-y0)*t
            p = u.MathLibrary.transform_location(frame,u.Vector(end.x+x,end.y+y,0))
            z = ground(p.x*.01,p.y*.01)+.95
            local = u.MathLibrary.inverse_transform_location(frame,u.Vector(p.x,p.y,z))
            vertices.append(u.Vector(x,y,local.z))
            uvs.append(u.Vector2D(s,t))
            if i<nx and j<ny:
                a = j*(nx+1)+i
                triangles.extend((u.IntVector(a,a+nx+2,a+1),u.IntVector(a,a+nx+1,a+nx+2)))
    dynamic = u.DynamicMesh()
    buf = u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=[u.Vector(0,0,1)]*len(vertices),
                                            uv0=uvs,triangles=triangles)
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buf)
    mesh = u.load_asset(MESH) if u.EditorAssetLibrary.does_asset_exist(MESH) else None
    if not mesh:
        opts = u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False,enable_nanite=False,
                enable_recompute_normals=False,enable_recompute_tangents=True)
        mesh,result = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,MESH,opts)
        if result!=u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot create '+MESH)
    opts = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
               replace_materials=True,new_materials=[material],new_material_slot_names=['Runoff'])
    _,result = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,mesh,opts,u.GeometryScriptMeshWriteLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(MESH)
    save(mesh)
    return len(triangles)


def install(site):
    end = west_crib(site)
    parts = [p for p in site.get_components_by_class(u.StaticMeshComponent) if TAG in map(str,p.component_tags)]
    if len(parts)>1:raise RuntimeError('Duplicate trough wear components')
    site.modify()
    part = parts[0] if parts else component(site,u.StaticMeshComponent)
    part.modify()
    part.set_mobility(u.ComponentMobility.STATIC)
    part.set_static_mesh(require(MESH))
    part.set_relative_transform(u.Transform(location=(end.x,end.y,0)),False,True)
    part.component_tags=[TAG,REPAIRED,'VillageTavern.NoCollision']
    part.set_cast_shadow(False)
    part.set_editor_property('receives_decals',False)
    part.set_editor_property('generate_overlap_events',False)
    part.set_cull_distance(3200)
    state(part,REPAIRED,False)
    return [round(end.x,2),round(end.y,2)]


def author(site):
    plan = json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf8'))
    end = west_crib(site)
    triangles = make_surface(site,end,make_material(),plan)
    return dict(triangles=triangles,crib_end_local_cm=install(site))

