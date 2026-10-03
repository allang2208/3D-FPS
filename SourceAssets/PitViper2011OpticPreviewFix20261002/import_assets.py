"""Save three fitted optics and refresh this gun's opaque WS material variants."""
import unreal as u,json,re,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
DEST='/Game/Weapons/PitViper2011/Attachments20261002'
BODY='/Game/Weapons/PitViper2011/Integrated20261002/Materials'
entries=json.loads((O/'authoring.json').read_text())
names=('h_190','stell','copper','polymer','Magazine_stell','Magazine_polymer','brass')
targets={DEST+'/'+v['name'] for v in entries.values()}|{BODY+'/MI_PitViper2011_'+k for k in names}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:raise RuntimeError('Preserve unsaved target assets: '+str(dirty))
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project content mount')
receipt={'saved':[],'meshes':{},'materials':{},'runtime_tested':False,'diagnosis_scope':'three optic seats and existing material/preview binding','rendered_for_acceptance':False}
def record(): (O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing production dependency '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());record()
for key in names:
    mi=load(BODY+'/MI_PitViper2011_'+key)
    overrides=mi.get_editor_property('base_property_overrides')
    overrides.set_editor_property('override_two_sided',False)
    mi.set_editor_property('base_property_overrides',overrides)
    L.update_material_instance(mi)
    E.set_metadata_tag(mi,'PitViperOpaqueShaderPolicy','20261002: inherit shared WS opaque closed-surface permutation; original finish parameters preserved')
    save(mi)
    color=L.get_material_instance_vector_parameter_value(mi,'FinishColor')
    receipt['materials'][key]={'asset':mi.get_path_name(),'parent':mi.parent.get_path_name(),'FinishColor':[color.r,color.g,color.b],
        'Roughness':L.get_material_instance_scalar_parameter_value(mi,'Roughness'),'Metallic':L.get_material_instance_scalar_parameter_value(mi,'Metallic'),
        'two_sided_override':False}
canonical=lambda s:re.sub(r'[._]\d{3}$','',s)
metal=load(BODY+'/MI_PitViper2011_h_190')
eoth=load('/Game/Weapons/CommonHK41620260930/Meshes/SM_M1911_eoth_holographic')
optical={canonical(str(s.material_slot_name)):s.material_interface for s in eoth.static_materials
    if canonical(str(s.material_slot_name)) in ('M_HK416_Glass','M_HK416_Eo_tech_Reticle')}
optical.update(M_HoloReticle=load('/Game/Weapons/M4Holographic/M_HoloReticle'),
    M_Panoramic_Glass=load('/Game/Weapons/PanoramicRedDot/M_Panoramic_Glass'),
    M_Panoramic_Reticle=load('/Game/Weapons/PanoramicRedDot/M_Panoramic_Reticle'))
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,entry in entries.items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=DEST;task.destination_name=entry['name']
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=load(DEST+'/'+entry['name']);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):slot.material_interface=optical.get(canonical(str(slot.material_slot_name)),metal);slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for name,p in entry['sockets_blender_m'].items():
            socket=mesh.find_socket(name)
            if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(p[0]*100,-p[1]*100,p[2]*100))
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
        if editor:
            build=editor.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,build)
        E.set_metadata_tag(mesh,'PitViperAttachmentSourceSHA256',hashlib.sha256(Path(entry['fbx']).read_bytes()).hexdigest())
        E.set_metadata_tag(mesh,'FittedInterfaceSource',str(O/'authoring.json'))
        E.set_metadata_tag(mesh,'OpticSeatRevision','20261002: complete contoured slide plate and actual foot contact; reticle-derived aim point')
        save(mesh);receipt['meshes'][key]={'asset':mesh.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
            'source':entry['fbx'],'aim_source':entry['aim_source'],'body_vertical_adjustment_mm':entry['body_vertical_adjustment_mm'],
            'sockets_cm':{name:[p[0]*100,-p[1]*100,p[2]*100] for name,p in entry['sockets_blender_m'].items()}}
        record();print('PIT_VIPER_FITTED_OPTIC_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
previous=P/'SourceAssets/PitViper2011Attachments20261002/import_receipt.json'
if previous.exists():
    report=json.loads(previous.read_text(encoding='utf8'))
    for key,value in receipt['meshes'].items():report['meshes'][key].update(value)
    report['optic_repair_receipt']=str(O/'import_receipt.json')
    previous.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
receipt['status']='imported_and_saved';record();print('PIT_VIPER_OPTIC_AND_MATERIAL_REPAIR_SAVED',flush=True)
