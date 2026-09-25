"""Import/save a bounded batch of authored clothing in the current editor (or commandlet)."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
SOURCE=ROOT/'SourceAssets/ModularOutfit20260924'
DEST='/Game/Characters/ModularOutfit20260924'
A=u.AssetToolsHelpers.get_asset_tools(); E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play mode before saving outfit assets')
if not hasattr(u,'FPSModularOutfitComponent') or not hasattr(u.FPSModularOutfitComponent,'configure_outfit_lods'):
    raise RuntimeError('Build the current Editor module before importing outfit assets')
authored=json.loads((SOURCE/'authored.json').read_text())
state_path=SOURCE/'imported.json'
state=json.loads(state_path.read_text()) if state_path.exists() else {'profiles':{},'materials':{}}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

def texture(filename,name,normal=False):
    path=DEST+'/Materials/'+name
    asset=u.load_asset(path)
    if not asset:
        task=u.AssetImportTask();task.filename=str(filename);task.destination_path=DEST+'/Materials';task.destination_name=name
        task.automated=True;task.save=True
        A.import_asset_tasks([task]);asset=u.load_asset(path)
        if not asset:raise RuntimeError('Texture import failed '+str(filename))
    asset.set_editor_property('srgb',not normal)
    if normal:
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        asset.set_editor_property('flip_green_channel',True)
    save(asset)
    return asset

def make_material(name,color,leather=False):
    path=DEST+'/Materials/'+name
    m=u.load_asset(path)
    if m:return m
    m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_skeletal_mesh',True)
    def node(cls,**kw):
        n=L.create_material_expression(m,cls)
        for key,value in kw.items():n.set_editor_property(key,value)
        return n
    tint=node(u.MaterialExpressionVectorParameter,parameter_name='Tint',default_value=u.LinearColor(*color,1))
    rough=node(u.MaterialExpressionScalarParameter,parameter_name='Roughness',default_value=.72 if leather else .91)
    uv=node(u.MaterialExpressionTextureCoordinate)
    noise=node(u.MaterialExpressionCustom,code='float2 p=UV*float2(540,540); float grain=frac(sin(dot(floor(p),float2(12.9898,78.233)))*43758.5453); return Tint*(0.91+0.09*grain);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    ci=[]
    for key in ('UV','Tint'):
        entry=u.CustomInput();entry.set_editor_property('input_name',key);ci.append(entry)
    noise.set_editor_property('inputs',ci)
    L.connect_material_expressions(uv,'',noise,'UV');L.connect_material_expressions(tint,'',noise,'Tint')
    L.connect_material_property(noise,'',u.MaterialProperty.MP_BASE_COLOR)
    L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    if not leather:
        n=node(u.MaterialExpressionTextureSample,texture=cloth_normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        L.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation: '+str(errors))
    save(m);return m

cloth_normal=texture(SOURCE/'Donor/shirt-knit-NORM.png','T_FieldSweater_Normal',True)
materials={
 'ShirtOlive':make_material('M_FieldSweater_Olive',(.115,.135,.080)),
 'ShirtCharcoal':make_material('M_FieldSweater_Charcoal',(.045,.053,.065)),
 'GlovesBrown':make_material('M_FieldGloves_Brown',(.18,.085,.035),True),
 'GlovesBlack':make_material('M_FieldGloves_Black',(.026,.03,.034),True)}
state['materials']={k:v.get_path_name() for k,v in materials.items()}
state.setdefault('pickups',{})
for kind,name in (('shirt','SM_FieldSweater_Pickup'),('gloves','SM_FieldGloves_Pickup')):
    path=DEST+'/Pickups/'+name
    mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=str(SOURCE/'Exports'/(name+'.fbx'))
        task.destination_path=DEST+'/Pickups';task.destination_name=name;task.automated=True;task.save=False
        options=u.FbxImportUI();options.set_editor_property('import_as_skeletal',False)
        options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
        options.set_editor_property('automated_import_should_detect_type',False)
        options.set_editor_property('import_materials',False);options.set_editor_property('import_textures',False)
        options.get_editor_property('static_mesh_import_data').set_editor_property('combine_meshes',True)
        task.options=options;A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Pickup import failed '+path)
    mesh.set_material(0,materials['ShirtOlive' if kind=='shirt' else 'GlovesBrown']);save(mesh)
    state['pickups'][kind]=mesh.get_path_name()
skin=u.load_asset('/Game/Characters/Mannequins/PlayerBodySkin/MI_PlayerBodySkin')
if not skin:raise RuntimeError('Missing accepted world-body skin material')

done=0
for key,entry in authored.items():
    if key in state['profiles']:continue
    directory=DEST+'/Profiles/'+key
    skeleton=None;meshes={}
    for kind in ('Base','Shirt','Gloves'):
        name=f'SK_{key}_{kind}';path=directory+'/'+name
        mesh=u.load_asset(path)
        if not mesh:
            task=u.AssetImportTask();task.filename=str(SOURCE/'Exports'/(name+'.fbx'))
            task.destination_path=directory;task.destination_name=name;task.automated=True;task.save=False
            options=u.FbxImportUI();options.set_editor_property('import_as_skeletal',True)
            options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_SKELETAL_MESH)
            options.set_editor_property('automated_import_should_detect_type',False)
            options.set_editor_property('import_mesh',True);options.set_editor_property('import_animations',False)
            options.set_editor_property('import_materials',False);options.set_editor_property('import_textures',False)
            options.set_editor_property('create_physics_asset',False)
            if skeleton:options.set_editor_property('skeleton',skeleton)
            data=options.get_editor_property('skeletal_mesh_import_data')
            data.set_editor_property('update_skeleton_reference_pose',False)
            data.set_editor_property('use_t0_as_ref_pose',False)
            data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            task.options=options;A.import_asset_tasks([task]);mesh=u.load_asset(path)
            if not mesh:raise RuntimeError('Mesh import failed: '+path)
        if kind=='Base':skeleton=mesh.get_editor_property('skeleton')
        mats=mesh.get_editor_property('materials')
        for i,slot in enumerate(mats):
            slot.set_editor_property('material_interface',skin if kind=='Base' else materials['ShirtOlive' if kind=='Shirt' else 'GlovesBrown'])
            mats[i]=slot
        mesh.set_editor_property('materials',mats)
        if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):
            raise RuntimeError('Could not configure authoring LODs '+path)
        if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,3,False,False):
            raise RuntimeError('Could not generate distance LODs '+path)
        save(mesh);save(mesh.get_editor_property('skeleton'))
        meshes[kind.lower()]=mesh.get_path_name()
    base_asset=u.load_asset(meshes['base'])
    base_slots=[str(m.material_slot_name) for m in base_asset.get_editor_property('materials')]
    shirt_regions=('SkinArms','SkinTorso') if entry['world'] else ('SkinArms','SkinTorso','SkinRest')
    state['profiles'][key]={**entry,**meshes,
        'shirt_covers':[i for i,n in enumerate(base_slots) if n in shirt_regions],
        'glove_covers':[i for i,n in enumerate(base_slots) if n=='SkinHands']}
    state_path.write_text(json.dumps(state,indent=2),encoding='utf-8')
    print('SAVED_OUTFIT_PROFILE',key)
    done+=1
    if done>=4:break
print('OUTFIT_IMPORT_PROGRESS',len(state['profiles']),len(authored))
state_path.write_text(json.dumps(state,indent=2),encoding='utf-8')
