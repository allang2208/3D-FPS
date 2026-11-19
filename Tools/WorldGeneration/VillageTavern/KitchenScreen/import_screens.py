"""Bind the village finishes and save the two compound screens in a private asset host."""
import json
from pathlib import Path
import unreal as u

DEST='/Game/WorldGeneration/VillageTavern/KitchenScreen'
VILLAGE='/Game/WorldGeneration/TemperateHills'
CARPENTER=VILLAGE+'/VillageCarpenter/Props/Surfaces/M_Carpenter'
SCAN='/Game/Dungeons/TunnelStyleIncinerator20261111/Quixel/CrackedPaintedPlaster_d91bfe39/Textures/T_CrackedPaintedPlaster_d91bfe39_'
source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/KitchenScreen'
tools=u.AssetToolsHelpers.get_asset_tools()
lib=u.EditorAssetLibrary
graph=u.MaterialEditingLibrary
saved=[]

def load(path):
    obj=u.load_asset(path)
    if not obj: raise RuntimeError('Required finish missing '+path)
    return obj

def save(obj):
    if not lib.save_loaded_asset(obj,False): raise RuntimeError('Save failed: '+obj.get_path_name())
    saved.append(obj.get_name())

def color(r,g,b):
    return u.LinearColor(r,g,b,1)

def limewash():
    mat=tools.create_asset('M_TavernKitchenLimewash',DEST,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    def node(kind,x,y):
        return graph.create_material_expression(mat,getattr(u,'MaterialExpression'+kind),x,y)
    def connect(src,out,dst,pin):
        if not graph.connect_material_expressions(src,out,dst,pin): raise RuntimeError('Bad input '+pin)
    def output(src,out,prop):
        if not graph.connect_material_property(src,out,getattr(u.MaterialProperty,'MP_'+prop)):
            raise RuntimeError('Bad property '+prop)
    def sample(role,y):
        n=node('TextureSample',-830,y)
        tex=load(SCAN+role)
        n.texture=tex
        sampler={
            u.TextureCompressionSettings.TC_NORMALMAP:'NORMAL',
            u.TextureCompressionSettings.TC_MASKS:'MASKS',
            u.TextureCompressionSettings.TC_GRAYSCALE:'GRAYSCALE' if tex.srgb else 'LINEAR_GRAYSCALE',
            u.TextureCompressionSettings.TC_ALPHA:'ALPHA'
        }.get(tex.compression_settings,'COLOR' if tex.srgb else 'LINEAR_COLOR')
        if tex.virtual_texture_streaming: sampler='VIRTUAL_'+sampler
        n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler)
        return n
    tex=sample('BaseColor',-360)
    luminance=node('DotProduct',-610,-350)
    weights=node('Constant3Vector',-830,-550)
    weights.constant=color(.30,.59,.11)
    connect(tex,'RGB',luminance,'A'); connect(weights,'',luminance,'B')
    tint=node('VectorParameter',-620,-170)
    tint.set_editor_property('parameter_name','LimeAndEarthTint')
    tint.set_editor_property('default_value',color(.75,.68,.52))
    mul=node('Multiply',-390,-350)
    connect(luminance,'',mul,'A'); connect(tint,'',mul,'B')
    floor=node('VectorParameter',-380,-150)
    floor.set_editor_property('parameter_name','PigmentFloor')
    floor.set_editor_property('default_value',color(.13,.117,.091))
    add=node('Add',-185,-310)
    connect(mul,'',add,'A'); connect(floor,'',add,'B')
    output(add,'','BASE_COLOR')
    rough=sample('Roughness',150)
    ao=sample('AO',370)
    output(sample('Normal',-90),'RGB','NORMAL')
    output(rough,'R','ROUGHNESS'); output(ao,'R','AMBIENT_OCCLUSION')
    graph.recompile_material(mat)
    save(mat)
    return mat

def finish(name,base,tint,floor):
    obj=tools.create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    graph.set_material_instance_parent(obj,base)
    graph.set_material_instance_vector_parameter_value(obj,'LimeAndEarthTint',color(*tint))
    graph.set_material_instance_vector_parameter_value(obj,'PigmentFloor',color(*floor))
    save(obj)
    return obj

plaster=limewash()
aged=finish('MI_TavernKitchenWeatheredLime',plaster,(.58,.49,.38),(.07,.066,.055))
daub=finish('MI_TavernKitchenDaub',plaster,(.34,.21,.105),(.045,.03,.018))
slots={'Oak':load(VILLAGE+'/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
       'Rot':load(CARPENTER+'Rot'),'Iron':load(CARPENTER+'Iron'),'Endgrain':load(CARPENTER+'Cut'),
       'Daub':daub}
for ruined in (False,True):
    name='SM_TavernKitchenScreen'+('Ruined' if ruined else '')
    opts=u.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh=True
    opts.import_as_skeletal=False
    opts.import_materials=False
    opts.import_textures=False
    data=opts.static_mesh_import_data
    data.combine_meshes=False
    data.convert_scene=True; data.convert_scene_unit=True; data.transform_vertex_to_absolute=True
    data.generate_lightmap_u_vs=True; data.auto_generate_collision=False; data.one_convex_hull_per_ucx=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask()
    task.filename=str(source/(name+'.fbx'))
    task.destination_path=DEST; task.destination_name=name; task.automated=True
    task.options=opts; task.factory=u.FbxFactory()
    tools.import_asset_tasks([task])
    mesh=load(DEST+'/'+name)
    slots['Plaster']=aged if ruined else plaster
    for i,slot in enumerate(mesh.static_materials):
        k=str(slot.get_editor_property('imported_material_slot_name'))
        if k in ('None',''): k=str(slot.material_slot_name)
        mesh.set_material(i,slots[k])
    mesh.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    mesh.set_editor_property('light_map_resolution',256)
    lods=u.StaticMeshReductionOptions()
    lods.auto_compute_lod_screen_size=False
    lods.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=r,screen_size=s)
                             for r,s in ((1.,1.),(.54,.36),(.23,.14))]
    edits=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    edits.set_lods(mesh,lods)
    save(mesh)
root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(root/'saved.json').write_text(json.dumps(saved,indent=2))
