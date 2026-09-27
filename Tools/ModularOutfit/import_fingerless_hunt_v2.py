"""Save the brown fingerless family and material; publication is a separate step."""
import json,hashlib,time
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
DEST='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SAVE=u.EditorLoadingAndSavingUtils
def load(path):
    x=u.load_asset(path)
    if not x:raise RuntimeError('Missing '+path)
    return x
def save(a):
    a.modify()
    if not (SAVE.save_packages([a.get_outer()],False) or E.save_loaded_asset(a,False)):raise RuntimeError('Cannot save '+a.get_path_name())
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world and ('UEDPIE' in world.get_name() or 'PIE_' in world.get_name()):raise RuntimeError('End PIE before saving glove assets')
if globals().get('MESHES_ONLY',False):
    mat=load(DEST+'/Materials/M_FingerlessHunt_Brown')
else:
    E.make_directory(DEST+'/Materials')
    normal_path=DEST+'/Materials/T_FingerlessHunt_Normal'
    normal=u.load_asset(normal_path)
    if not normal:
        task=u.AssetImportTask();task.filename=str(P/'SourceAssets/HandEquipmentAppearance/Source/Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_Normal.jpg')
        task.destination_path=DEST+'/Materials';task.destination_name='T_FingerlessHunt_Normal';task.automated=True;task.save=False
        A.import_asset_tasks([task]);normal=load(normal_path)
    normal.set_editor_property('srgb',False);normal.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
    normal.set_editor_property('flip_green_channel',True);normal.set_editor_property('lod_bias',0);save(normal)
    matpath=DEST+'/Materials/M_FingerlessHunt_Brown';mat=u.load_asset(matpath)
    if not mat:mat=A.create_asset('M_FingerlessHunt_Brown',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    for expr in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expr)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    uv=node(mat,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    inputs={'Fields':node(mat,u.MaterialExpressionTextureCoordinate,coordinate_index=1),'Details':node(mat,u.MaterialExpressionTextureCoordinate,coordinate_index=2)}
    texroot='/Game/Characters/ArmsLeatherCandidate/Textures/'
    for name,path,kind in [('Color',texroot+'T_Fab_Leather_BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                          ('RoughScan',texroot+'T_Fab_Leather_Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS),
                          ('Grain',normal_path,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                          ('Cavity',texroot+'T_Fab_Leather_Cavity',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE),
                          ('AO',texroot+'T_Fab_Leather_AO',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE),
                          ('SpecScan',texroot+'T_Fab_Leather_Specular',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)]:
        n=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=load(path),sampler_type=kind)
        wire(uv,n,'UVs');inputs[name]=n
    code=(P/'Tools/ModularOutfit/fingerless_hunt_leather_v2.hlsl').read_text()
    c=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='Metric tangent leather, exposed-digit glove shell')
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    c.set_editor_property('inputs',pins);extra=[]
    for name,kind in [('OutNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutSpecular',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        x=u.CustomOutput();x.set_editor_property('output_name',name);x.set_editor_property('output_type',kind);extra.append(x)
    c.set_editor_property('additional_outputs',extra)
    for name,n in inputs.items():wire(n,c,name)
    for out,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutNormal',u.MaterialProperty.MP_NORMAL),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutSpecular',u.MaterialProperty.MP_SPECULAR)]:
        if not L.connect_material_property(c,out,prop):raise RuntimeError('Cannot connect output '+out)
    L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=0),'',u.MaterialProperty.MP_METALLIC)
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Leather compilation failed '+str(errors))
    save(mat)
receipts=ROOT/'Saved';receipts.mkdir(exist_ok=True)
entries=json.loads((ROOT/'manifest.json').read_text());published={};saved_count=0
for entry in entries:
    path=Path(entry['authored']);raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw);name=d['profile']
    receipt=receipts/f'{name}.json'
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old['sha256']==sha and E.does_asset_exist(old['mesh']):published[name]=old['mesh'];continue
    if globals().get('MAX_SAVES',0) and saved_count>=MAX_SAVES:continue
    print('FINGERLESS_IMPORT_BEGIN',name,flush=True)
    source=load(d['binding_source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read binding '+name)
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    verts=[];norm=[];uv=[[],[],[]];weights=[];tris=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        row=[]
        for k,vi in enumerate(face):
            n=d['normals'][fi][k];coords=[d[ch][fi][k] for ch in ('uv','uv1','uv2')]
            key=(vi,*[round(v,7) for seq in (n,*coords) for v in seq])
            if key not in lookup:
                lookup[key]=len(verts);verts.append(u.Vector(*d['positions'][vi]));norm.append(u.Vector(*n));weights.append(d['weights'][vi])
                for ch in range(3):uv[ch].append(u.Vector2D(*coords[ch]))
            row.append(lookup[key])
        tris.append(u.IntVector(*row))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=verts,normals=norm,uv0=uv[0],uv1=uv[1],uv2=uv[2],triangles=tris),0,True)
    if dm.get_triangle_count()!=len(tris):raise RuntimeError('Rejected glove triangles '+name)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,w in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[bn],weight=bw) for bn,bw in w.items()])
    folder=DEST+'/'+name;assetname='SK_'+name+'_FingerlessHuntV2';asset=u.load_asset(folder+'/'+assetname)
    if not asset:E.make_directory(folder);asset=A.duplicate_asset(assetname,folder,source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[mat],new_material_slot_names=['FingerlessGloveLeather'],
        enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write glove '+name)
    asset.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    E.set_metadata_tag(asset,'SourceContract',d['contract']);save(asset)
    if not (u.FPSModularOutfitComponent.configure_outfit_lods(asset) and S.regenerate_lod(asset,3,True,False)):raise RuntimeError('Cannot build glove LODs '+name)
    save(asset);published[name]=asset.get_path_name()
    receipt.write_text(json.dumps(dict(mesh=asset.get_path_name(),sha256=sha,lods=3,runtime_tested=False),indent=2)+'\n')
    print('FINGERLESS_SAVED',name,flush=True)
    saved_count+=1
(ROOT/'asset-receipt.json').write_text(json.dumps(dict(material=mat.get_path_name(),profiles=published,complete=len(published)==len(entries),runtime_tested=False),indent=2)+'\n')
print('FINGERLESS_ASSETS_SAVED',len(published),flush=True)
