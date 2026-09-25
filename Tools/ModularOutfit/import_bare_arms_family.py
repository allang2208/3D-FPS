"""Build/save the accepted bare-arm family, then publish the complete config."""
import hashlib,json
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=Path(globals().get('AUTHOR_ROOT',PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6'))
DEST=globals().get('ASSET_ROOT','/Game/Characters/ModularOutfit20260924/BareArmsFamilyV6')
VERSION=globals().get('FAMILY_VERSION','V6')
M4='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4BareArmsV6'
V5='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SurfaceV5'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play before saving bare-arm family assets')
receipts=ROOT/'Saved';receipts.mkdir(parents=True,exist_ok=True)

def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing authoring dependency: '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect skin input '+pin)
def skin(suffix,source):
    name='M_BareFamily_'+suffix;parent=u.load_asset(DEST+'/Materials/'+name)
    if not parent:parent=A.duplicate_asset(name,DEST+'/Materials',load(source))
    if E.get_metadata_tag(parent,'BareFamilyCoordinates')!='CanonicalUV123':
        custom=L.get_material_property_input_node(parent,u.MaterialProperty.MP_NORMAL)
        if not isinstance(custom,u.MaterialExpressionCustom):raise RuntimeError('Missing shared skin expression')
        def node(cls,**props):
            n=L.create_material_expression(parent,cls)
            for key,value in props.items():n.set_editor_property(key,value)
            return n
        xy=node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
        zx=node(u.MaterialExpressionTextureCoordinate,coordinate_index=2)
        yz=node(u.MaterialExpressionTextureCoordinate,coordinate_index=3)
        z=node(u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False);wire(zx,z,'')
        x=node(u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False);wire(zx,x,'')
        position=node(u.MaterialExpressionAppendVector);wire(xy,position,'A');wire(z,position,'B')
        normal=node(u.MaterialExpressionAppendVector);wire(x,normal,'A');wire(yz,normal,'B')
        wire(position,custom,'RestPosition');wire(normal,custom,'RestNormal')
        if globals().get('SOFT_PALM',False):
            code=custom.get_editor_property('code')
            code=code.replace('f.rnm(AnatomicalNormal,detail)',
                'f.rnm(normalize(float3(AnatomicalNormal.xy*lerp(1,.58,palmar*(1-nail)),AnatomicalNormal.z)),detail)')
            custom.set_editor_property('code',code)
        L.set_material_usage(parent,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        errors=L.recompile_material(parent)
        if errors:raise RuntimeError('Skin material compilation failed: '+str(errors))
        E.set_metadata_tag(parent,'BareFamilyCoordinates','CanonicalUV123');save(parent)
    name='MI_BareFamily_'+suffix;instance=u.load_asset(DEST+'/Materials/'+name)
    if not instance:instance=A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,parent);L.update_material_instance(instance);save(instance)
    return instance

arm=skin('Arms',M4+'/M_M4FullBareArmSkin')
hand=skin('Hands',V5+'/M_M4UnifiedSkin_Hand')
manifest=json.loads((ROOT/'manifest.json').read_text());published={}
active_profiles=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['profiles']
for entry in manifest:
    name=entry['profile'];raw=Path(entry['authored']).read_bytes();data=json.loads(raw)
    sha=hashlib.sha256(raw).hexdigest();receipt_path=receipts/f'{name}.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if receipt['authored_sha256']==sha and E.does_asset_exist(receipt['mesh']):
            published[data['source']]=receipt['mesh'];continue
    print('BARE_FAMILY_IMPORT_BEGIN',name,flush=True)
    profile=active_profiles[data['source']]
    binding_source=profile.get('original_gloved_source',data['source']) if profile.get('native_bare_arms') else data['source']
    original_package=ROOT/'NativeDefaults/Packages'/f'{name}.uasset'
    source_file=original_package if profile.get('native_bare_arms') and original_package.exists() else PROJECT/'Content'/(data['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(source_file.read_bytes()).hexdigest()!=data['source_sha256']:
        raise RuntimeError('Native source changed during authoring; refresh only '+name)
    source=load(binding_source)
    native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native reference '+name)
    _,bones=B.get_all_bones_info(native);bone_ids={str(b.name):b.index for b in bones}
    vertices=[];normals=[];uvs=[[],[],[],[]];weights=[];triangles=[];lookup={};colours=[]
    for ti,face in enumerate(data['triangles']):
        row=[]
        for corner,vi in enumerate(face):
            uv=data['uv'][ti][corner];normal=data['normals'][ti][corner]
            canonical=data['canonical_positions'][vi];rest_n=data['canonical_normals'][ti][corner]
            key=(vi,data['triangle_materials'][ti],*[round(v,7) for v in (*uv,*normal,*rest_n)])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*normal));weights.append(data['weights'][vi])
                colours.append(u.LinearColor(0 if data['triangle_materials'][ti]==2 else 1,0,0,1))
                for channel,pair in enumerate((uv,canonical[:2],(canonical[2],rest_n[0]),rest_n[1:])):
                    uvs[channel].append(u.Vector2D(*pair))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(
        vertices=vertices,normals=normals,uv0=uvs[0],uv1=uvs[1],uv2=uvs[2],uv3=uvs[3],vertex_colors=colours,triangles=triangles),0,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,bindings in enumerate(weights):
        B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bone_ids[n],weight=w) for n,w in bindings.items()])
    for ti,material in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,material,True)
    folder=DEST+'/'+name;mesh_name='SK_'+name+'_BareArms'+VERSION
    mesh=u.load_asset(folder+'/'+mesh_name)
    if not mesh:mesh=A.duplicate_asset(mesh_name,folder,source)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[arm,arm,hand],
        new_material_slot_names=['BareUpperArms','BareLowerArms','BareHandsOriginalGrip'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write native bare arms '+name)
    mesh.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
    S.set_lod_build_settings(mesh,0,build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot configure LODs '+name)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot build LODs '+name)
    E.set_metadata_tag(mesh,'SourceContract',data['contract']);save(mesh)
    receipt={'profile':name,'mesh':mesh.get_path_name(),'source':data['source'],
        'authored_sha256':sha,'source_sha256':data['source_sha256'],'native_skeleton':data['skeleton'],
        'skin_coordinates':'UV0 accepted anatomy; UV1-3 canonical position/normal; full precision',
        'runtime_tested':False}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    published[data['source']]=mesh.get_path_name()
    print('BARE_FAMILY_SAVED',name,mesh.get_path_name(),flush=True)

# Publish only after the complete family is saved; never point to source-only work.
if globals().get('PUBLISH_CONFIG',True):
    config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    previous={}
    for path,profile in config['profiles'].items():
        name=profile['rig_profile']
        if name=='Body':continue
        previous[path]={key:profile.get(key) for key in ('bare_arms_candidate','native_bare_skin','base','shirt_covers','glove_covers')}
        asset=published[path] if path in published else load(M4+'/SK_M4_OriginalShape_BareHands').get_path_name()
        profile['bare_arms_candidate']=asset;profile['native_bare_skin']=asset;profile['base']=asset
        profile['shirt_covers']=[0,1];profile['glove_covers']=[2]
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'published.json').write_text(json.dumps({'profiles':published,
        'previous_profile_fields':previous,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('BARE_FAMILY_PUBLISHED',len(previous),flush=True)
