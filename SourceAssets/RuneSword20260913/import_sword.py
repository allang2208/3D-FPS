"""Import sword mesh, current Manny materials, authored clips and CC0 audio."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913';A=u.AssetToolsHelpers.get_asset_tools();receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def task(file,name,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=D;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True
    if options:t.options=options
    A.import_asset_tasks([t]);asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+str(file))
    receipt.append({'source':str(file),'asset':asset.get_path_name()});return asset
original=next((P/'Original').rglob('*.fbx'));textures={}
for suffix,name in [('', 'BaseColor'),('_normal','Normal'),('_metallic','Metallic'),('_roughness','Roughness'),('_emission','Emissive')]:
    tex=task(original.with_name(original.stem+suffix+'.png'),'T_RuneSword_'+name)
    tex.set_editor_property('srgb',name in ['BaseColor','Emissive'])
    if name=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif name in ['Roughness','Metallic']:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    u.EditorAssetLibrary.save_loaded_asset(tex);textures[name]=tex
mat=u.load_asset(D+'/M_AzureRunesword') or A.create_asset('M_AzureRunesword',D,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('used_with_skeletal_mesh',True)
E=u.MaterialEditingLibrary;E.delete_all_material_expressions(mat)
for i,(name,prop) in enumerate([('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Emissive',u.MaterialProperty.MP_EMISSIVE_COLOR)]):
    n=E.create_material_expression(mat,u.MaterialExpressionTextureSample,-650,i*200);n.texture=textures[name]
    n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if name in ['Metallic','Roughness'] else u.MaterialSamplerType.SAMPLERTYPE_COLOR
    if name=='Emissive':
        mult=E.create_material_expression(mat,u.MaterialExpressionMultiply,-300,800);mult.set_editor_property('const_b',3.5)
        E.connect_material_expressions(n,'RGB',mult,'A');E.connect_material_property(mult,'',prop)
    else:E.connect_material_property(n,'R' if name in ['Metallic','Roughness'] else 'RGB',prop)
E.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=True
sm=task(P/'Export/SM_AzureRunesword.fbx','SM_AzureRunesword',opt);sm.set_material(0,mat);u.EditorAssetLibrary.save_loaded_asset(sm)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
sk=task(P/'Export/SK_AzureRunesword_Manny.fbx','SK_AzureRunesword_Manny',opt)
source=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings={str(s.material_slot_name):s.material_interface for s in source.get_editor_property('materials')};bindings['M_AzureRunesword']=mat
slots=sk.get_editor_property('materials')
for i,slot in enumerate(slots):
    key=str(slot.material_slot_name)
    if key not in bindings:raise RuntimeError('Missing source material binding: '+key)
    slot.material_interface=bindings[key];slots[i]=slot
sk.set_editor_property('materials',slots)
sk.set_editor_property('positive_bounds_extension',u.Vector(120,120,120));sk.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
u.EditorAssetLibrary.save_loaded_asset(sk)
for name in ['Idle','Walk','Slash1','Slash2','Equip','Sprint']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=sk.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    seq=task(P/('Export/A_RuneSword_'+name+'.fbx'),'A_RuneSword_'+name,opt)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:seq.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(seq)
for name in ['Sword_Hit','Sword_Swing']:
    sound=task(P/('Reference/'+name+'.wav'),name)
    sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE);u.EditorAssetLibrary.save_loaded_asset(sound)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));u.log('RUNESWORD_IMPORT_COMPLETE')
