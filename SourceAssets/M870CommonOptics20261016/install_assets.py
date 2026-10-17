"""Install private M870 optic bodies and measured saddles; preserve the weapon rig."""
import unreal as u
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M870/Optics20261016'
C=json.loads((O/'inputs.json').read_text());G=json.loads((O/'authoring.json').read_text());F=json.loads((O/'finish.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
R={'saved':[],'meshes':{},'complete':False,'gameplay_tested':False,
   'preserved':['M870 skeletal mesh','skeleton','all animations','factory sights','source optic assets']}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in R['saved']:R['saved'].append(obj.get_path_name())
    record();return obj
def clone(src,path):
    return load(path) if E.does_asset_exist(path) else E.duplicate_asset(src,path)
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE')
if any(p.get_name().startswith(D+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved M870 optic assets')
finished={}
def finish(source):
    path=source.get_path_name()
    if path in finished:return finished[path]
    label=hashlib.sha256(path.encode()).hexdigest()[:10]
    dst=D+'/Materials/MI_M870_Optic_'+label
    if 'M_Thermal_Graphite.' in path:
        mat=load(dst) if E.does_asset_exist(dst) else A.create_asset(dst.rsplit('/',1)[1],D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mat,source)
        L.set_material_instance_vector_parameter_value(mat,'SurfaceTint',u.LinearColor(*F['base_color_linear'],1))
        L.set_material_instance_scalar_parameter_value(mat,'DryRoughness',F['Roughness'][0])
        L.set_material_instance_scalar_parameter_value(mat,'Metallic',F['Metalic'][0])
        L.update_material_instance(mat)
    else:
        mat=clone(path,dst)
        if isinstance(mat,u.MaterialInstanceConstant):
            names={str(n) for n in L.get_scalar_parameter_names(mat.get_base_material())}
            if 'R01_Roughness' in names:
                L.set_material_instance_scalar_parameter_value(mat,'R01_Roughness',F['Roughness'][0])
                # Retain the accepted source's metal mask, source wear and
                # polymer tint. Use the M870 rail's neutral coated finish.
                L.set_material_instance_vector_parameter_value(mat,'R01_ToneScale',u.LinearColor(.59,.59,.59,1))
            L.update_material_instance(mat)
    E.set_metadata_tag(mat,'M870OpticSourceMaterial',path)
    finished[path]=save(mat);return mat
for key,row in C['assets'].items():
    obj=clone(row['path'],D+'/Meshes/SM_M870_'+key)
    slots=list(obj.static_materials)
    for i,slot in enumerate(slots):
        name=str(slot.material_slot_name).lower()
        # Preserve glass, reticles, thermal display, rubber, accents and labels.
        optical=any(n in name for n in ('glass','reticle','red_dot','objective','display','rubber','copper','titanium','legend','marking'))
        if slot.material_interface and not optical:
            slot.material_interface=finish(load(row['slots'][i]['material']));slots[i]=slot
    obj.set_editor_property('static_materials',slots)
    E.set_metadata_tag(obj,'M870OpticSource',row['path'])
    E.set_metadata_tag(obj,'M870Mount','Native receiver rail with fitted OpticSeat; source sockets and optical geometry retained')
    save(obj);R['meshes'][key]=obj.get_path_name();record()
path=D+'/Materials/M_M870_AdapterSteel'
steel=load(path) if E.does_asset_exist(path) else A.create_asset('M_M870_AdapterSteel',D+'/Materials',u.Material,u.MaterialFactoryNew())
for node in list(L.get_material_expressions(steel)):L.delete_material_expression(steel,node)
color=L.create_material_expression(steel,u.MaterialExpressionConstant3Vector)
color.set_editor_property('constant',u.LinearColor(*F['base_color_linear'],1))
L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
metal=L.create_material_expression(steel,u.MaterialExpressionConstant);metal.set_editor_property('r',F['Metalic'][0])
L.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
wet=L.create_material_expression(steel,u.MaterialExpressionScalarParameter);wet.set_editor_property('parameter_name','WeaponWetness');wet.set_editor_property('default_value',0.)
rough=L.create_material_expression(steel,u.MaterialExpressionLinearInterpolate);rough.set_editor_property('const_a',F['Roughness'][0]);rough.set_editor_property('const_b',.12)
L.connect_material_expressions(wet,'',rough,'Alpha');L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
L.recompile_material(steel);save(steel)
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,row in G['parts'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True
        opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=D+'/Meshes';task.destination_name='SM_M870_OpticSeat_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
        A.import_asset_tasks([task]);obj=load(task.destination_path+'/'+task.destination_name)
        slots=list(obj.static_materials)
        for slot in slots:slot.material_interface=steel
        obj.set_editor_property('static_materials',slots)
        settings=sms.get_lod_build_settings(obj,0);settings.recompute_normals=False;settings.recompute_tangents=False
        settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.generate_lightmap_u_vs=False
        sms.set_lod_build_settings(obj,0,settings)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(obj)
        E.set_metadata_tag(obj,'M870Interface','19.28072 mm native rail wing; donor-foot underside pockets; independent low saddle')
        E.set_metadata_tag(obj,'M870OpticOffsetCm',json.dumps(row['optic_offset_cm']))
        save(obj);R['meshes']['OpticSeat_'+key]=obj.get_path_name();record()
        print('M870_OPTIC_ASSEMBLY_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
R['complete']=True;record();print('M870_COMMON_OPTICS_SAVED',len(R['saved']),flush=True)
