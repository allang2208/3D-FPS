import unreal,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');SRC=ROOT/'SourceAssets/Ammo12Gauge20261012/Models'
DEST='/Game/Items/Ammo12Gauge20261012'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Stop PIE before importing/saving ammunition assets.')
manifest=json.loads((SRC/'manifest.json').read_text(encoding='utf-8'))
tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
receipt={'materials':[],'meshes':[]}
def imp(file,name,dest,options=None):
    task=unreal.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    tools.import_asset_tasks([task]);obj=unreal.load_asset(dest+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+name)
    return obj
def save(obj):
    obj.modify()
    if not unreal.EditorAssetLibrary.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
grain=imp(SRC/'PaperGrain.png','T_PaperGrain',DEST+'/Textures')
grain.set_editor_property('srgb',False);grain.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS);save(grain)
materials={}
for name,row in manifest['materials'].items():
    path=DEST+'/Materials/M_'+name
    mat=unreal.load_asset(path) or tools.create_asset('M_'+name,DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    # New task-owned material graphs only. No shared weapon/item material changes.
    lib.delete_all_material_expressions(mat)
    color=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector);color.constant=unreal.LinearColor(*row['color'])
    output=color
    if row['paper_grain']:
        sample=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample);sample.texture=grain
        sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        scale=lib.create_material_expression(mat,unreal.MaterialExpressionMultiply);scale.set_editor_property('const_b',.28);lib.connect_material_expressions(sample,'R',scale,'A')
        bias=lib.create_material_expression(mat,unreal.MaterialExpressionAdd);bias.set_editor_property('const_b',.72);lib.connect_material_expressions(scale,'',bias,'A')
        output=lib.create_material_expression(mat,unreal.MaterialExpressionMultiply);lib.connect_material_expressions(color,'',output,'A');lib.connect_material_expressions(bias,'',output,'B')
    lib.connect_material_property(output,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(row['roughness'],unreal.MaterialProperty.MP_ROUGHNESS),(row['metallic'],unreal.MaterialProperty.MP_METALLIC)]:
        n=lib.create_material_expression(mat,unreal.MaterialExpressionConstant);n.r=value;lib.connect_material_property(n,'',prop)
    lib.recompile_material(mat);save(mat);materials[name]=mat;receipt['materials'].append(mat.get_path_name())
unreal.load_module('StaticMeshEditor')
sub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if sub is None:sub=unreal.new_object(unreal.StaticMeshEditorSubsystem)
for row in manifest['meshes']:
    name=row['name'];opt=unreal.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    opt.import_as_skeletal=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;opt.automated_import_should_detect_type=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.generate_lightmap_u_vs=True
    opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=imp(SRC/(name+'.fbx'),name,DEST+'/Meshes',opt)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unknown slot '+key)
        mesh.set_material(i,materials[key])
    sub.remove_collisions(mesh);sub.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)
    options=unreal.EditorScriptingMeshReductionOptions()
    options.auto_compute_lod_screen_size=True
    levels=[]
    for ratio in [1.,.5,.2]:
        level=unreal.EditorScriptingMeshReductionSettings();level.percent_triangles=ratio;levels.append(level)
    options.reduction_settings=levels;sub.set_lods(mesh,options)
    save(mesh);receipt['meshes'].append({'path':mesh.get_path_name(),'kind':row['kind'],'slots':len(mesh.static_materials),'bounds':str(mesh.get_bounds())})
(ROOT/'SourceAssets/Ammo12Gauge20261012/model_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('AMMO_MODELS_SAVED '+str(len(receipt['meshes'])))
