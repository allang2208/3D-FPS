"""Save the original-shape M4 derivative through the existing UE MCP batch.

Edit native DynamicMesh positions only: retain original weights, normal/UV
overlays, triangle winding, reference bones and bind transforms. No FBX roundtrip.
"""
import json,hashlib
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=Path(globals().get('AUTHOR_ROOT',PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'))
DEST=globals().get('ASSET_DEST','/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4')
SMOOTH_SKIN=bool(globals().get('SMOOTH_SKIN',False))
REFINED_SKIN=bool(globals().get('REFINED_SKIN',False))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play before saving the new bare-hand assets; original assets have not been modified')
saved=[]
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())
def load_texture(suffix,srgb,compression):
    name='T_M4OriginalShape_'+suffix
    if globals().get('RESUME_TEXTURES',False):
        existing=u.load_asset(DEST+'/'+name)
        if not existing:raise RuntimeError('Resume expected already saved texture '+name)
        saved.append(existing.get_path_name());return existing
    task=u.AssetImportTask();task.filename=str(ROOT/(name+'.png'))
    task.destination_path=DEST;task.destination_name=name;task.automated=True
    task.replace_existing=True;task.save=True;A.import_asset_tasks([task])
    tex=u.load_asset(DEST+'/'+name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    tex.set_editor_property('srgb',srgb);tex.set_editor_property('compression_settings',compression)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if suffix=='SkinNormal':tex.set_editor_property('flip_green_channel',False)
    save(tex);return tex
colour=load_texture('SkinColour',True,u.TextureCompressionSettings.TC_DEFAULT)
normal=load_texture('SkinNormal',False,u.TextureCompressionSettings.TC_NORMALMAP)
surface=load_texture('SkinSurface',False,u.TextureCompressionSettings.TC_MASKS)
micro=load_texture('SkinMicro',False,u.TextureCompressionSettings.TC_BC7) if SMOOTH_SKIN else None
colour_detail=load_texture('SkinColourDetail',False,u.TextureCompressionSettings.TC_BC7) if REFINED_SKIN else None
mat=u.load_asset(DEST+'/M_M4OriginalShape_Skin')
if not mat:mat=A.create_asset('M_M4OriginalShape_Skin',DEST,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
def node(cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def connect(a,pin,prop):
    if not L.connect_material_property(a,pin,prop):raise RuntimeError('Cannot connect skin material output')
def sample(name,tex,kind):return node(u.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=tex,sampler_type=kind)
col=sample('SkinColour',colour,u.MaterialSamplerType.SAMPLERTYPE_COLOR)
connect(col,'RGB',u.MaterialProperty.MP_BASE_COLOR)
inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
        'AnatomicalNormal':sample('AnatomicalNormal',normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        'Surface':sample('SkinSurface',surface,u.MaterialSamplerType.SAMPLERTYPE_MASKS),
        'PoreTiling':scalar('PoreTiling',1800),'DetailStrength':scalar('DetailStrength',.025),
        'RoughnessOffset':scalar('RoughnessOffset',0)}
if SMOOTH_SKIN:
    parameters=json.loads((ROOT/'micro_surface.json').read_text())
    surface_sample=inputs['Surface']
    view=node(u.MaterialExpressionCameraVectorWS)
    transform=node(u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    if not L.connect_material_expressions(view,'',transform,''):raise RuntimeError('Cannot connect tangent view direction')
    inputs={'UV':inputs['UV'],'AnatomicalNormal':inputs['AnatomicalNormal'],
      'NailMask':(surface_sample,'R'),'PalmMask':(surface_sample,'A'),'BaseRoughness':(surface_sample,'G'),
      'MicroTexture':node(u.MaterialExpressionTextureObjectParameter,parameter_name='SkinMicroHeight',texture=micro,
                          sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
      'ViewTangent':transform,'MicroRepeat':scalar('MicroRepeat',parameters['tile_repeat']),
      'MicroTileCm':scalar('MicroTileCm',parameters['tile_size_cm']),
      'MicroHeightCm':scalar('MicroHeightCm',parameters['height_range_cm']),
      'MicroNormalStrength':scalar('MicroNormalStrength',.85),'RoughnessOffset':scalar('RoughnessOffset',0)}
    if REFINED_SKIN:
        inputs['MicroNormalStrength'].set_editor_property('default_value',parameters['normal_strength'])
        inputs.update({'BaseColour':(col,'RGB'),
          'ColourDetail':node(u.MaterialExpressionTextureObjectParameter,parameter_name='SkinColourDetail',texture=colour_detail,
                              sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
          'ColourDetailStrength':scalar('ColourDetailStrength',parameters['colour_detail_strength']),
          'MicroHeightZero':scalar('MicroHeightZero',parameters['height_zero']),
          'MicroTextureSize':scalar('MicroTextureSize',parameters['texture_size'])})
detail=node(u.MaterialExpressionCustom,code=(ROOT/'skin_detail.hlsl').read_text(),
            output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='Original-shape skin and nails')
items=[]
for name in inputs:
    item=u.CustomInput();item.set_editor_property('input_name',name);items.append(item)
detail.set_editor_property('inputs',items)
out=u.CustomOutput();out.set_editor_property('output_name','OutRoughness');out.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
extra=[out]
if REFINED_SKIN:
    colour_output=u.CustomOutput();colour_output.set_editor_property('output_name','OutColour')
    colour_output.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3);extra.append(colour_output)
detail.set_editor_property('additional_outputs',extra)
for name,value in inputs.items():
    expression,pin=value if isinstance(value,tuple) else (value,'')
    if not L.connect_material_expressions(expression,pin,detail,name):raise RuntimeError('Cannot connect skin input '+name)
connect(detail,'',u.MaterialProperty.MP_NORMAL);connect(detail,'OutRoughness',u.MaterialProperty.MP_ROUGHNESS)
if REFINED_SKIN:connect(detail,'OutColour',u.MaterialProperty.MP_BASE_COLOR)
connect(scalar('SkinSpecular',.35),'',u.MaterialProperty.MP_SPECULAR)
connect(scalar('SkinScatterStrength',.10 if REFINED_SKIN else .18),'',u.MaterialProperty.MP_OPACITY)
connect(node(u.MaterialExpressionConstant,r=0),'',u.MaterialProperty.MP_METALLIC)
profile=u.load_asset('/Game/Characters/ArmsSkinSleeveCandidate/SSP_ForearmSkin')
if not profile:raise RuntimeError('Missing accepted skin scattering profile')
if REFINED_SKIN:
    local_profile=u.load_asset(DEST+'/SSP_RefinedM4Skin')
    if not local_profile:local_profile=A.duplicate_asset('SSP_RefinedM4Skin',DEST,profile)
    settings=local_profile.get_editor_property('settings')
    settings.set_editor_property('mean_free_path_distance',parameters['skin_profile_mfp_cm'])
    settings.set_editor_property('enable_burley',True)
    local_profile.set_editor_property('settings',settings);save(local_profile);profile=local_profile
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
mat.set_editor_property('subsurface_profile',profile)
L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.layout_material_expressions(mat)
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Skin material build failed '+str(errors))
save(mat)
instance=u.load_asset(DEST+'/MI_M4OriginalShape_Skin')
if not instance:instance=A.create_asset('MI_M4OriginalShape_Skin',DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
L.set_material_instance_parent(instance,mat);L.update_material_instance(instance);save(instance)

author=(ROOT/'M4_bare_shape.json').read_bytes();d=json.loads(author)
original=json.loads((ROOT/'M4_original.json').read_text())
source=u.load_asset(d['source'])
if not source:raise RuntimeError('Original M4 missing')
arm_slots=original['arm_materials']
sleeve=source.materials[arm_slots[0]].material_interface
forearm_source=source.materials[arm_slots[1]].material_interface
forearm=u.load_asset(DEST+'/MI_M4OriginalShape_Forearm')
if not forearm:forearm=A.duplicate_asset('MI_M4OriginalShape_Forearm',DEST,forearm_source)
# Local instance only: remove the 3 cm leather extension from the exposed arm.
L.set_material_instance_scalar_parameter_value(forearm,'GloveCuffStart',2.0)
L.update_material_instance(forearm);save(forearm)

dm,result=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy native reference mesh')
if d.get('new_topology',False):
    B=u.GeometryScript_BoneWeights
    native=dm;dm=u.DynamicMesh();_,bones=B.get_all_bones_info(native)
    indices={str(b.name):b.index for b in bones};lookup={};vertices=[];normals=[];uvs=[];weights=[];triangles=[]
    for ti,face in enumerate(original['triangles']):
        row=[]
        for corner,vi in enumerate(face):
            uv=original['uv'][ti][corner];n=d['normals'][ti][corner]
            key=(vi,*[round(x,7) for x in (*uv,*n)])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n))
                uvs.append(u.Vector2D(*uv));weights.append(original['weights'][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uvs,triangles=triangles)
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,w in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=v) for n,v in w.items()])
    for ti,material in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,material,True)
else:
    apply_native_shape=True
# IDs refer directly to this native export. Apply only authored nonzero deltas.
for vi,p,old in zip(d.get('source_vertex_ids',[]),d['positions'],original['positions']):
    if max(abs(a-b) for a,b in zip(p,old))<.000001:continue
    _,valid=u.GeometryScript_MeshEdits.set_vertex_position(dm,vi,u.Vector(*p),True)
    if not valid:raise RuntimeError('Native source vertex no longer exists')
_,tri_list,_=Q.get_all_triangle_indices(dm,False)
triangles=u.GeometryScript_List.convert_triangle_list_to_array(tri_list)
retained=set(d.get('source_triangle_ids',range(len(triangles))))
remove=[i for i in range(len(triangles)) if i not in retained]
for ti,material in zip(d.get('source_triangle_ids',[]),d['triangle_materials']):
    u.GeometryScript_Materials.set_triangle_material_id(dm,ti,material,True)
if 'normals' in d and not d.get('new_topology',False):
    for ti,material,ns in zip(d['source_triangle_ids'],d['triangle_materials'],d['normals']):
        if material!=2:continue
        values=u.GeometryScriptTriangle(vector0=u.Vector(*ns[0]),vector1=u.Vector(*ns[1]),vector2=u.Vector(*ns[2]))
        _,valid=u.GeometryScript_Normals.set_mesh_triangle_normals(dm,ti,values,True)
        if not valid:raise RuntimeError('Cannot set smooth skin normals')
index_list=u.GeometryScript_List.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE)
_,deleted=u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,index_list,True)
if deleted!=len(remove):raise RuntimeError('Unable to extract all native arm sections')
u.GeometryScript_MeshRepair.remove_unused_vertices(dm)
u.GeometryScript_MeshRepair.compact_mesh(dm)
name='SK_M4_OriginalShape_BareHands';mesh=u.load_asset(DEST+'/'+name)
if not mesh:mesh=A.duplicate_asset(name,DEST,source)
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[sleeve,forearm,instance],
    new_material_slot_names=['OriginalSleeves','OriginalForearmSkin','BareHandsOriginalGrip'],
    enable_recompute_normals=False,enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,result=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save original-shape derivative')
mesh.set_editor_property('physics_asset',None)
if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot author outfit LODs')
if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot build LODs')
contract=('Original M4 reference skeleton; native weights on retained surfaces, interpolated wrist weights. '
          if d.get('new_topology',False) else 'Original M4 topology, reference skeleton and weights. ')
E.set_metadata_tag(mesh,'SourceContract',contract+'Contact constrained. '+str(d.get('geometry_policy',{})))
save(mesh)

# Activate only after all packages have been saved. Preserve unrelated recipes.
config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
entry=config['profiles'][source.get_path_name()]
previous=entry.get('bare_arms_candidate','')
entry['bare_arms_candidate']=mesh.get_path_name()
config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'fps.Outfit.BareArmsCandidate 1')
receipt={'source':source.get_path_name(),'mesh':mesh.get_path_name(),'previous_candidate':previous,
 'saved_assets':saved,'author_sha256':hashlib.sha256(author).hexdigest(),
 'preserved':['original skeleton and bind transforms','native weights','original arm topology/UV',
              'palm/finger-pad contact surfaces','sleeves and forearms','animation assets','original glove equipment restoration'],
 'scope':'M4 first-person; no modular shirt/gloves equipped; next Play reads updated profile',
 'runtime_tested':False,'visual_acceptance':'Pending user test'}
receipt['geometry_policy']=d.get('geometry_policy',{})
receipt['hand_normals_rebuilt']='normals' in d
receipt['micro_height_surface']=SMOOTH_SKIN
if REFINED_SKIN:
    receipt['preserved']=['original skeleton and bind transforms','native bindings on retained surfaces',
      'palm/finger-pad grip positions','animation assets','original glove restoration']
    receipt['wrist_reconstructed']=True
    receipt['new_wrist_weights']='interpolated from native cut-boundary weights'
    receipt['skin_source']='Katsukagi Skin Human 002, CC0; local micro-pores and roughness'
(ROOT/'saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ORIGINAL_SHAPE_BARE_M4_SAVED',mesh.get_path_name())
