"""Author and save common part assets through the existing serialized UE bridge."""
import unreal as u,json,re,shutil,importlib.util
from pathlib import Path
from runpy import run_path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/CommonHK41620260930';H='/Game/Weapons/HK416/Reworked20260930'
apply_m16_bindings=run_path(str(O.parent/'WeaponSurface20260930/M16/current_bindings.py'))['apply_current_bindings']
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != P.resolve():
    raise RuntimeError('This common attachment batch belongs to D:/FPS3D/FPSGAME only')
A=u.AssetToolsHelpers.get_asset_tools();report={'saved':[],'meshes':{},'icons':{},'runtime_tested':False}
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing common attachment dependency '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
donors={
 'M1911':'/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_holographic',
 'G18':'/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_holographic',
 'DW715':'/Game/Weapons/DanWesson715/AccessoryPolymer20260914/Attachments/Meshes/SM_DW715_holographic',
 'M16':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_holographic'}
bindings={}
for family,path in donors.items():
    mesh=load(path);bindings[family]={re.sub(r'[._]\d{3}$','',str(s.material_slot_name)):s.material_interface for s in mesh.static_materials}
interface=next(m for key,m in bindings['M1911'].items() if 'AdapterSteel' in key)
spec=importlib.util.spec_from_file_location('eoth_reticle_materials',O/'reticle_materials.py');reticle_materials=importlib.util.module_from_spec(spec);spec.loader.exec_module(reticle_materials)
clear_reticle,clear_glass=reticle_materials.build()
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for key,entry in json.loads((O/'authoring.json').read_text()).items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_name=entry['name'];task.destination_path=ROOT+'/Meshes'
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task])
        mesh=load(ROOT+'/Meshes/'+entry['name']);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
            if entry['kind']=='eoth_holographic' and name=='M_HK416_Eo_tech_Reticle':mat=clear_reticle
            elif entry['kind']=='eoth_holographic' and name=='M_HK416_Glass':mat=clear_glass
            elif name.startswith('M_HK416_'):mat=load(H+'/Materials/'+name)
            elif name=='Universal_InterfaceSteel':mat=bindings['M16']['M16_InterfaceMetal'] if entry['family']=='M16' else interface
            else:mat=bindings[entry['family']][name]
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        apply_m16_bindings(mesh)
        for name,p in entry['sockets_blender_m'].items():
            socket=mesh.find_socket(name)
            if not socket:
                socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(p[0]*100,-p[1]*100,p[2]*100))
        system=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);settings=system.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;system.set_lod_build_settings(mesh,0,settings)
        u.EditorAssetLibrary.set_metadata_tag(mesh,'Attribution','HK416 Full ReWorked by MojoLeeDa / Sketchfab 669a9ee17dc44580b53425a08c2f83d0 / CC BY 4.0; detached, reframed and fitted for FPSGAME')
        save(mesh);report['meshes'][key]={'asset':mesh.get_path_name(),'material_slots':[s.material_interface.get_path_name() for s in mesh.static_materials],'sockets':list(entry['sockets_blender_m'])}
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
# Same two physical source parts already have approved-format framed production
# images. Reuse them under the independent option keys without generating variants.
icons=P/'Content/ColdSteelData/AttachmentIcons20260913'
for old,new in [('ue_hk416_optic_holographic','optic_eoth_holographic'),('ue_hk416_muzzle_true','muzzle_multi_caliber_suppressor')]:
    for folder in ('','FramedFirearms'):
        src=icons/folder/(old+'.png');dst=icons/folder/(new+'.png');shutil.copy2(src,dst)
        task=u.AssetImportTask();task.filename=str(dst);task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'+('/'+folder if folder else '')
        task.destination_name=new;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
        tex=load(task.destination_path+'/'+new);tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
        tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.never_stream=True;save(tex);report['icons'][folder+'/'+new]={'source':str(src),'file':str(dst),'asset':tex.get_path_name()}
report['status']='nine_fitted_meshes_and_four_ui_textures_saved'
(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('COMMON_HK416_PARTS_IMPORTED_SAVED',len(report['saved']))
