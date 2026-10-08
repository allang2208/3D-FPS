"""Save fitted guards and a private native rune branch on the existing silver steel."""
import copy,json,shutil
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004/RuneGuard20261005'
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
REV='XuanChiRuneGuard20261005'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before importing the fitted guards and rune material; no assets changed')
receipt={'complete':False,'assets':[],'game_tested':False,'rune_graph_source':None}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def save(asset):
    L.set_metadata_tag(asset,'XuanChiRuneGuardRevision',REV)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()

def connect(a,pin,b,target):
    target='' if target is None or str(target)=='None' else str(target)
    if not E.connect_material_expressions(a,pin,b,target):
        raise RuntimeError('Material connection failed: '+target)

steel=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/BladeV3/Materials/M_XuanChi_SteelRelief_V3')
hilt=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/SurfaceV2/Materials/M_XuanChi_Hilt_V2')
if not steel or not hilt:raise RuntimeError('The current silver and copper materials are required')
material_path=D+'/Materials/M_XuanChiBladeRuneSurface'
material=u.load_asset(material_path)
if not material:
    tang=json.loads((ROOT/'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
    source_path=next(v for v in tang['slots']['blade_1']['factory']['materials'].values() if 'M_TangDaoBladeRuneSurface' in v)
    source=u.load_asset(source_path)
    emission=E.get_material_property_input_node(source,u.MaterialProperty.MP_EMISSIVE_COLOR)
    if not source or not emission:raise RuntimeError('The installed native TangDao rune graph is required')
    material=L.duplicate_asset(steel.get_path_name(),material_path)
    if not material:raise RuntimeError('Could not create the private silver rune surface')
    # Copy only emission dependencies. The complete silver PBR/POM graph remains intact.
    originals={}
    def gather(node):
        if node.get_name() in originals:return
        originals[node.get_name()]=node
        for upstream in E.get_inputs_for_material_expression(source,node):
            if upstream:gather(upstream)
    gather(emission)
    copies={name:E.duplicate_material_expression(material,None,node) for name,node in originals.items()}
    for name,node in originals.items():
        for upstream,pin in zip(E.get_inputs_for_material_expression(source,node),E.get_material_expression_input_names(node)):
            if upstream:connect(copies[upstream.get_name()],'',copies[name],pin)
    for node in copies.values():
        if isinstance(node,u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='RuneMode':
            node.set_editor_property('default_value',-1.)
        if isinstance(node,u.MaterialExpressionVectorParameter) and str(node.get_editor_property('parameter_name'))=='Dimensions':
            node.set_editor_property('default_value',u.LinearColor(11,2,108,0))
    output_pin=E.get_material_property_input_node_output_name(source,u.MaterialProperty.MP_EMISSIVE_COLOR)
    output_pin='' if str(output_pin)=='None' else str(output_pin)
    slab=E.get_material_property_input_node(material,u.MaterialProperty.MP_FRONT_MATERIAL)
    connect(copies[emission.get_name()],output_pin,slab,'Emissive Color')
    if not E.connect_material_property(copies[emission.get_name()],output_pin,u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Rune emission output failed')
    L.set_metadata_tag(material,'XuanChiRuneSource',source.get_path_name())
    E.layout_material_expressions(material)
elif L.get_metadata_tag(material,'XuanChiRuneGuardRevision')!=REV:
    raise RuntimeError('Preserved an unowned material at '+material_path)
errors=list(E.recompile_material(material) or [])
if errors:raise RuntimeError('Rune material compile failed: '+str(errors))
save(material)
receipt['rune_graph_source']=L.get_metadata_tag(material,'XuanChiRuneSource')
temporal_path=material_path+'_Whirlwind'
temporal=u.load_asset(temporal_path)
if not temporal:
    temporal=L.duplicate_asset(material.get_path_name(),temporal_path)
    response=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
    connect(one,'',response,'')
elif L.get_metadata_tag(temporal,'XuanChiRuneGuardRevision')!=REV:
    raise RuntimeError('Preserved an unowned temporal material')
errors=list(E.recompile_material(temporal) or [])
if errors:raise RuntimeError('Temporal material compile failed: '+str(errors))
save(temporal)

spec=json.loads((P/'exports.json').read_text(encoding='utf-8'))
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
for row in spec['options']:
    path=D+'/Meshes/'+row['mesh'];mesh=u.load_asset(path)
    if not mesh:
        cfg=u.FbxImportUI();cfg.automated_import_should_detect_type=False
        cfg.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        cfg.import_as_skeletal=False;cfg.import_mesh=True
        cfg.import_materials=False;cfg.import_textures=False;cfg.import_animations=False
        data=cfg.static_mesh_import_data
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.build_nanite=False
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=row['mesh']
        task.automated=True;task.replace_existing=False;task.save=False;task.options=cfg
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Guard import failed: '+path)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,steel if 'SteelRelief' in str(slot.material_slot_name) else hilt)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    build=subsystem.get_lod_build_settings(mesh,0)
    build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True;build.use_full_precision_u_vs=True
    subsystem.set_lod_build_settings(mesh,0,build);save(mesh)

def update_json(file,merge):
    before=file.read_bytes();data=json.loads(before.decode('utf-8-sig'));merge(data)
    backup=P/'Before'/file.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog update; saved assets retained: '+str(file))
    temporary=file.with_suffix(file.suffix+'.xuanchi-runes.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(file)

def modules(catalog):
    for row in catalog['slots']['blade_1'].values():
        current=row.setdefault('materials',{}).get('M_XuanChi_SteelRelief_V3','')
        # A later legendary rune branch contains this graph plus mode 8.
        if '/ZhenmoRune20261005/' not in current:
            row['materials']['M_XuanChi_SteelRelief_V3']=material.get_path_name()
    for row in spec['options']:
        entry=copy.deepcopy(catalog['slots']['guard']['factory'])
        entry.update(mesh=D+'/Meshes/'+row['mesh']+'.'+row['mesh'],appearance=row['appearance'])
        catalog['slots']['guard'][row['option']]=entry
    catalog['rune_surface_revision']=REV

def options(catalog):
    for column in catalog['columns']:
        if column['key']!='blade_2':continue
        for option in column['options']:
            if option['id'] in ['auspicious_cloud_rune','mountain_rune']:
                if 'ue_xuanchi_zhenyue' not in option['weapons']:option['weapons'].append('ue_xuanchi_zhenyue')
                option['description']=option['description'].replace('唐刀专属。','唐刀与玄螭镇岳限定。').replace('刀尖','刃尖').replace('刀身','刃身')

update_json(ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json',modules)
update_json(ROOT/'Content/ColdSteelData/melee-gunsmith.json',options)
update_json(ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json',lambda data:data.update({material.get_path_name():temporal.get_path_name()}))
receipt['complete']=True;receipt['catalogs_saved']=True;record()
print('XUANCHI_RUNES_GUARDS_SAVED '+json.dumps(receipt,ensure_ascii=False),flush=True)
