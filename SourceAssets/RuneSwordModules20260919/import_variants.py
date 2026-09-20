"""Import this task's hilt modules in the current editor and merge only their catalog entries."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1];D='/Game/Weapons/AzureRunesword20260913/Modules20260919'
L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing rune sword modules; keep the editor open.')
rows=json.loads((P/'variant_exports.json').read_text(encoding='utf-8'))
# Older manifests also contain retired Rune pommel prototypes.
rows=[row for row in rows if row['slot']!='pommel']
stock=u.load_asset('/Game/Weapons/AzureRunesword20260913/SM_AzureRunesword').get_material(0)
receipt=[]
def material(name,color,metal,rough,emission=0,crystal=False):
    path=D+'/'+name
    if L.does_asset_exist(path):
        mat=u.load_asset(path)
        if not L.save_loaded_asset(mat,False):raise RuntimeError('Unable to save existing task material '+name)
        return mat
    mat=A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    def constant(value,prop):
        node=M.create_material_expression(mat,u.MaterialExpressionConstant)
        node.set_editor_property('r',value)
        if not M.connect_material_property(node,'',prop):raise RuntimeError('Material scalar connection failed')
    rgb=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);rgb.set_editor_property('constant',u.LinearColor(*color,1))
    if not M.connect_material_property(rgb,'',u.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Material color connection failed')
    constant(metal,u.MaterialProperty.MP_METALLIC);constant(rough,u.MaterialProperty.MP_ROUGHNESS)
    if emission:
        rgb=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);rgb.set_editor_property('constant',u.LinearColor(*(c*emission for c in color),1))
        if not M.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Material emissive connection failed')
    if crystal:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        constant(.68,u.MaterialProperty.MP_OPACITY)
    M.recompile_material(mat)
    if not L.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+name)
    return mat
materials={'M_RuneModuleSilver':material('M_RuneModuleSilver',(.36,.43,.50),.88,.29),
           'M_RuneModuleGlow':material('M_RuneModuleGlow',(.11,.48,.80),0,.3,3.),
           'M_RuneModuleCrystal':material('M_RuneModuleCrystal',(.055,.30,.64),0,.12,.5,True)}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
path=ROOT/'Content/ColdSteelData/rune-sword-modules.json'
catalog=json.loads(path.read_text(encoding='utf-8')) if path.exists() else json.loads((P/'catalog_base.json').read_text(encoding='utf-8'))
catalog['trace_from_animation']=True
catalog['slots']['blade_1']['factory']['trace_base_cm']=[0,0,2.4]
catalog['slots']['blade_1']['factory']['trace_tip_cm']=[0,0,80.]
for row in rows:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'));task.destination_path=D;task.destination_name=row['mesh']
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(D+'/'+row['mesh'])
    if not asset or not task.imported_object_paths:raise RuntimeError('Module import failed: '+row['mesh'])
    for i,slot in enumerate(asset.static_materials):
        name=str(slot.material_slot_name)
        finish=next((mat for key,mat in materials.items() if key in name),stock)
        asset.set_material(i,finish)
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Module save failed '+row['mesh'])
    spec={'mesh':asset.get_path_name(),'location_cm':row['location_cm'],'interface':'azure_hilt_v1'}
    if row['slot']=='grip':
        spec['pommel_offset_cm']=[0,0,-2.8 if row['id']=='long_twohand' else 0]
        if row['id']=='long_twohand':
            spec['animation_folder']='/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'
            spec['appearance']='加长握柄 · 柄尾联动'
    catalog['slots'].setdefault(row['slot'],{})[row['id']]=spec
    receipt.append({'source':task.filename,'asset':asset.get_path_name()})
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RUNE_SWORD_VARIANTS_IMPORTED',len(receipt))
