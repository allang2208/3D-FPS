"""Save the compact 1x optics and original PSO side mount through the active UE authoring gate."""
import json,shutil,runpy
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
S=json.loads((O/'authoring.json').read_text())
compact_import=O.parent/'RSH12CompactOptics20261004/import_assets.py'
has_compact_revision=(compact_import.parent/'authoring.json').exists()
if has_compact_revision:
    for key in ('holographic','eoth_holographic','rail_holographic','rail_eoth_holographic'):S['meshes'].pop(key,None)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE active; new models are authored but asset import waits until play ends')
targets={v['asset'] for v in S['meshes'].values()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Unsaved target packages: '+str(targets&dirty))
receipt=dict(saved=[],meshes={},complete=False,runtime_tested=False)
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing input '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record()
bindings={}
for key,s in S['meshes'].items():
    file=P/'Content'/(s['asset'].removeprefix('/Game/')+'.uasset')
    if file.exists():
        backup=O/'BeforeAssets'/(s['asset'].removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(file,backup)
        mesh=load(s['asset']);bindings[key]={str(m.material_slot_name):m.material_interface for m in mesh.static_materials}
mount=load('/Game/Weapons/RSH12/Optics20261004/Materials/MI_RSH12_RailSteel')
shell=load('/Game/Weapons/RSH12/PSO20261004/Materials/M_RSH12_PSO_Shell')
glass=load('/Game/Weapons/SVDDragunov20260922/Complete20260923/Materials/M_SVD_OpticalGlass')
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,s in S['meshes'].items():
        folder,name=s['asset'].rsplit('/',1);task=u.AssetImportTask();task.filename=s['fbx'];task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opt
        A.import_asset_tasks([task]);mesh=load(s['asset']);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            label=str(slot.material_slot_name)
            if key.startswith('rail_') or key=='pso_side_shoe':mat=mount
            elif key=='pso1_4x':
                if 'OpticalGlass' in label:mat=glass
                elif 'Shell' in label:mat=shell
                elif 'MountSteel' in label:mat=mount
                else:raise RuntimeError('Unmapped PSO material '+label)
            else:
                candidates=bindings[key]
                mat=candidates.get(label)
                if not mat:
                    # UE may retain exported material asset names during reimport.
                    mat=next((m for m in candidates.values() if m.get_name()==label),None)
                if not mat:raise RuntimeError('Unmapped compact optic material '+key+' '+label)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for name,p in s.get('sockets_cm',{}).items():
            sock=mesh.find_socket(name)
            if not sock:
                sock=u.new_object(u.StaticMeshSocket,outer=mesh);sock.set_editor_property('socket_name',name);mesh.add_socket(sock)
            sock.set_editor_property('relative_location',u.Vector(*p))
        E.set_metadata_tag(mesh,'RSHOpticRefit','20261004: user-requested compact 1x optics; original PSO side bracket on fixed forward frame')
        if key=='pso1_4x':E.set_metadata_tag(mesh,'SourceAttribution','PSO-1 from SVD by LeroyCake / CC BY 4.0; repaired UV and opaque seam partition retained; original bracket and lever restored, RSH side receiver shoe')
        save(mesh);receipt['meshes'][key]=dict(asset=mesh.get_path_name(),materials={str(m.material_slot_name):m.material_interface.get_path_name() for m in slots},sockets_cm=s.get('sockets_cm',{}));record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
runpy.run_path(str(O.parent/'RSH12PSO20261004/publish_icon.py'),run_name='__main__')
if has_compact_revision:runpy.run_path(str(compact_import),run_name='__main__')
receipt['shared_pso_icon_saved']=True;receipt['complete']=True;record();print('RSH_OPTIC_REFIT_IMPORTED',len(receipt['meshes']),flush=True)
