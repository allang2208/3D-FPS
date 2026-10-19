"""Save only ST6 materials, Jason neck geometry, and the matching display mesh."""
import json,sys,shutil,hashlib,runpy
from pathlib import Path
import unreal as u
O=Path(__file__).parent; R=O.parents[1]; OLD=O.parent/'ST6Reset20261017'
DEST=runpy.run_path(str(O/'recipe.py'))['DEST']
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
receipt={'saved':[],'game_tested':False}

def load(path):
    value=u.load_asset(path)
    if not value:raise RuntimeError('Missing '+path)
    return value

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
    print('ST6_REFINED_SAVED',asset.get_path_name(),flush=True)

def node(mat,cls,**props):
    v=L.create_material_expression(mat,cls)
    for k,x in props.items():v.set_editor_property(k,x)
    return v

def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Connection '+pin)

def materials():
    folder=DEST+'/Materials';E.make_directory(folder);name='M_ST6Fabric'
    mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def interp(cls):
        n=node(mat,u.MaterialExpressionVertexInterpolator);wire(node(mat,cls),n,'');return n
    tex='/Game/Weapons/Super90/Cransh20261006/Textures/T_S90_sleeve_st6_generalist_'
    inputs={
        'RestPosition':interp(u.MaterialExpressionPreSkinnedPosition),
        'RestNormal':interp(u.MaterialExpressionPreSkinnedNormal),
        'WorldPosition':node(mat,u.MaterialExpressionWorldPosition),
        'SurfaceNormal':node(mat,u.MaterialExpressionVertexNormalWS),
        'Fabric':node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='OriginalFabric',texture=load(tex+'Base_color'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR),
        'FabricNormal':node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='OriginalFabricNormal',texture=load(tex+'Normal_OpenGL'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        'Origin':node(mat,u.MaterialExpressionVectorParameter,parameter_name='Origin',default_value=u.LinearColor(0,0,0,1)),
    }
    for name,value in dict(ShoulderHeight=52,TorsoMode=0,CollarTop=151.2,NormalStrength=.45).items():
        inputs[name]=node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    custom=node(mat,u.MaterialExpressionCustom,code=(O/'fabric.ush').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='ST6 rest-space cloth and differential skinned normal')
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    outputs=[]
    for key,typ in [('OutNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        out=u.CustomOutput();out.set_editor_property('output_name',key);out.set_editor_property('output_type',typ);outputs.append(out)
    custom.set_editor_property('additional_outputs',outputs)
    for key,value in inputs.items():wire(value,custom,key)
    for pin,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
        if not L.connect_material_property(custom,pin,prop):raise RuntimeError('Material output '+pin)
    transform=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire(custom,transform,'','OutNormal');L.connect_material_property(transform,'',u.MaterialProperty.MP_NORMAL)
    spec=node(mat,u.MaterialExpressionConstant,r=.26);L.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    errors=[str(e) for e in (L.recompile_material(mat) or [])]
    receipt['material_compile_errors']=errors
    if errors:raise RuntimeError('ST6 material compilation: '+'; '.join(errors))
    save(mat)
    for profile in ('Body','Jason','Pickup'):
        if profile=='Pickup':
            d=json.loads((O/'pickup.json').read_text());origin=d['body_origin'];height=d['shoulder_height'];top=d['collar_top']
        else:
            d=json.loads((OLD/'Read'/f'{profile}.json').read_text());bones=d['bones'];origin=bones['pelvis']['position'];height=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5-origin[2];top=151.2 if profile=='Jason' else 160.5
        name='MI_ST6Torso_'+profile
        mi=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,mat)
        L.set_material_instance_vector_parameter_value(mi,'Origin',u.LinearColor(*origin,1))
        for key,value in dict(ShoulderHeight=height,TorsoMode=1,CollarTop=top).items():L.set_material_instance_scalar_parameter_value(mi,key,value)
        L.update_material_instance(mi);save(mi)

def dynamic(d,native=None):
    vertices=[];normals=[];uv=[];weights=[];faces=[];seen={}
    for fi,face in enumerate(d['triangles']):
        tri=[]
        for j,vi in enumerate(face):
            n=d['normals'][fi][j];t=d['uv'][fi][j];key=(vi,*[round(v,7) for v in n+t])
            if key not in seen:
                seen[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append(d['weights'][vi])
            tri.append(seen[key])
        faces.append(u.IntVector(*tri))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=faces),0,True)
    if native:
        _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
        B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
        for i,ws in enumerate(weights):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in ws.items()])
    for fi,m in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,m,True)
    return dm

def skeletal(file,name):
    d=json.loads((O/file).read_text());target=DEST+'/Jason/'+name
    E.make_directory(DEST+'/Jason')
    template='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Jason/SK_Jason_ue_st6_sleeves'
    asset=u.load_asset(target) or E.duplicate_asset(template,target)
    native,status=G.copy_mesh_from_skeletal_mesh(load(d['binding_source']),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read binding')
    dm=dynamic(d,native)
    opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(p) for p in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opt,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save neck geometry')
    asset.set_editor_property('physics_asset',None)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    # Keep the policy and source-model settings consistent, so regeneration
    # cannot simplify the neck against the independent full-detail head.
    policy_path=DEST+'/Jason/'+name+'_NeckLODPolicy'
    policy=u.load_asset(policy_path)
    if not policy:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
        policy=A.create_asset(name+'_NeckLODPolicy',DEST+'/Jason',u.SkeletalMeshLODSettings,factory)
    groups=[]
    for i in range(3):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=1.0,num_of_vert_percentage=1.0,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():
            settings.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',settings)
        group.set_editor_property('screen_size',u.PerPlatformFloat(default=[1.,.18,.075][i]));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy)
    asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset,3,True,False)
    sha=hashlib.sha256((O/file).read_bytes()).hexdigest()
    receipt.setdefault('source_sha256',{})[file]=sha
    E.set_metadata_tag(asset,'ST6RefinementSource',sha);save(asset)

def pickup():
    d=json.loads((O/'pickup.json').read_text());dm=dynamic(d)
    path='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Pickups/SM_ue_st6_sleeves'
    asset=load(path);rel=path.removeprefix('/Game/')+'.uasset';backup=O/'Before/Assets'/rel
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'Content'/rel,backup)
    opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(p) for p in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True)
    _,status=G.copy_mesh_to_static_mesh(dm,asset,opt,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save pickup')
    receipt.setdefault('source_sha256',{})['pickup.json']=hashlib.sha256((O/'pickup.json').read_bytes()).hexdigest()
    save(asset)

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve active PIE')
materials()
skeletal('collar.json','SK_Jason_ST6Trims')
skeletal('world_shirt.json','SK_Jason_ST6Refined')
pickup()
receipt['completed']=True;(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('ST6_REFINEMENT_ASSETS_COMPLETE',flush=True)
