"""Import and save A762 assets in the existing UE editor. No PIE or tests."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/A762/Integrated20260920';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'geometry','saved':[]};textures={}
def save(asset):
    if not asset or not L.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+str(asset))
    report['saved'].append(asset.get_path_name());(O/'geometry_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def import_file(file,dest,name,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(dest+'/'+name)
    if not asset:raise RuntimeError('Import did not create '+dest+'/'+name)
    return asset
donor=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')
if not donor:raise RuntimeError('Current AKM donor unavailable')
bindings={str(s.material_slot_name):s.material_interface for s in donor.get_editor_property('materials')}
for channel in ['base_color','roughness','metallic','normal']:
    tex=import_file(O.parent/f'Meshy/candidate01/downloads/texture_urls_0_{channel}.png',P+'/Textures','T_A762_'+channel)
    tex.set_editor_property('srgb',channel=='base_color')
    if channel=='normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif channel!='base_color':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
    save(tex);textures[channel]=tex
author=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
names=[v['material'] for v in author['parts'].values()]+['M_A762_Inside'];materials={}
props={'base_color':u.MaterialProperty.MP_BASE_COLOR,'roughness':u.MaterialProperty.MP_ROUGHNESS,'metallic':u.MaterialProperty.MP_METALLIC,'normal':u.MaterialProperty.MP_NORMAL}
for name in names:
    mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat);M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if name=='M_A762_Inside':
        node=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);node.set_editor_property('constant',u.LinearColor(.013,.016,.020,1));M.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
        for prop,value in [(u.MaterialProperty.MP_METALLIC,.8),(u.MaterialProperty.MP_ROUGHNESS,.52)]:
            n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value);M.connect_material_property(n,'',prop)
    else:
        for channel,tex in textures.items():
            n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            M.connect_material_property(n,'RGB' if channel in ['base_color','normal'] else 'R',props[channel])
    M.recompile_material(mat);save(mat);materials[name]=mat
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=donor.skeleton
opts.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
mesh=import_file(O/'Exports/SK_A762_Manny.fbx',P,'SK_A762_Manny',opts)
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):
    name=str(slot.material_slot_name);material=materials.get(name) or bindings.get(name)
    if not material:raise RuntimeError('Missing source material binding '+name)
    slot.material_interface=material;slots[i]=slot
mesh.set_editor_property('materials',slots);save(mesh)
for part in ['RearSight','FrontSight']:
    name='SM_A762_'+part;opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    opt.static_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS);opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    static=import_file(O/'Exports'/f'{name}.fbx',P,name,opt)
    slots=static.get_editor_property('static_materials')
    for i,slot in enumerate(slots):slot.material_interface=materials[str(slot.material_slot_name)];slots[i]=slot
    static.set_editor_property('static_materials',slots);save(static)
report['complete']=True;report['mesh']=mesh.get_path_name();report['skeleton']=mesh.skeleton.get_path_name();report['donor_materials']=donor.get_path_name()
(O/'geometry_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8');u.log('A762 geometry imported and saved.')
