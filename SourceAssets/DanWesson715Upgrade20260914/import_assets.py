"""Import the completed upgrade and register its wet-surface variants."""
import unreal as u,json,ast
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1];D='/Game/Weapons/DanWesson715/Upgrade20260914'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
reference=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny')
bindings={str(slot.material_slot_name):slot.material_interface for slot in reference.materials}
manifest=json.loads((O/'textures.json').read_text());materials={};receipt={'materials':{},'textures':{},'animations':{}}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Unable to save '+asset.get_path_name())
    return asset
def task(filename,dest,options=None):
    t=u.AssetImportTask();t.filename=str(filename);t.destination_path=dest;t.destination_name=Path(filename).stem;t.automated=True;t.replace_existing=True;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);asset=u.load_asset(dest+'/'+t.destination_name)
    if not asset:raise RuntimeError('Asset import failed: '+str(filename))
    return asset
for group,info in manifest.items():
    name=info['material'];path=D+'/Materials/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);maps={}
    for kind,filename in info['textures'].items():
        tex=task(filename,D+'/Textures');tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('lod_bias',0)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);node=L.create_material_expression(m,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if kind=='BaseColor':L.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        elif kind=='Normal':L.connect_material_property(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:
            for channel,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:L.connect_material_property(node,channel,prop)
        maps[kind]=tex.get_path_name()
    L.recompile_material(m);save(m);materials[name]=m;receipt['materials'][name]=m.get_path_name();receipt['textures'][group]=maps
    u.log('DW715_UPGRADE_MATERIAL_IMPORTED '+group)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=reference.skeleton
data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh=task(O/'SK_DW715_Manny.fbx',D,opt);slots=mesh.materials
for i,slot in enumerate(slots):
    key=str(slot.material_slot_name);slot.material_interface=materials[key] if key in materials else bindings[key];slots[i]=slot
mesh.set_editor_property('materials',slots);save(mesh)
for filename in sorted((O/'Animations').glob('*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    clip=task(filename,D+'/Animations',opt);clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(clip);receipt['animations'][filename.stem]=clip.get_path_name()
# Construct wet variants using the existing project graph, preserving the maps
# registered by other weapon/weather tasks.
unreal=u;LIB=L;TOOLS=A;DEST=D+'/Materials';REPORT={'materials':[]}
tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in {'node','wire','prop','scalar','constant','vector','custom','save'}],type_ignores=[]),'<weather material helpers>','exec'))
wetmaps={}
for name,surface in materials.items():
    wetpath=D+'/Materials/'+name+'_Wet';wet=u.load_asset(wetpath) if E.does_asset_exist(wetpath) else E.duplicate_asset(surface.get_path_name(),wetpath)
    if not E.get_metadata_tag(wet,'DW715UpgradeWet'):
        original={}
        for pname in ['BASE_COLOR','ROUGHNESS','NORMAL']:
            propid=getattr(u.MaterialProperty,'MP_'+pname);n=L.get_material_property_input_node(wet,propid);original[pname]=(n,L.get_material_property_input_node_output_name(wet,propid))
        beads=custom(wet,(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=node(wet,u.MaterialExpressionTextureCoordinate),Wet=scalar(wet,'WeaponWetness',0)),4,'WeatherBeads')
        prop(custom(wet,'return Base*(1-Data.a*.07);',dict(Base=original['BASE_COLOR'],Data=beads),3),'BASE_COLOR')
        prop(custom(wet,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=original['ROUGHNESS'],Data=beads),1),'ROUGHNESS')
        prop(custom(wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=original['NORMAL'],Data=beads),3),'NORMAL')
        E.set_metadata_tag(wet,'DW715UpgradeWet','1');L.set_material_usage(wet,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);save(wet)
    wetmaps[surface.get_path_name()]=wet
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'));mapping.update(wetmaps);library.set_editor_property('wet_materials',mapping);save(library)
receipt.update({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'wet_materials':{k:v.get_path_name() for k,v in wetmaps.items()},'material_slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'state':'Imported and saved; no rendered or gameplay testing'})
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');u.log('DW715_UPGRADE_IMPORT_COMPLETE')
