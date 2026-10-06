"""Background asset production for the RSH-only tactical device variants."""
import json,shutil
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent;P=O.parents[1]
D='/Game/Weapons/RSH12/Tactical20261005'
SOURCE='/Game/Weapons/DanWesson715/AccessoryPolymer20260914/Materials'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text())
receipt={'saved':[],'meshes':{},'materials':{},'icons':{},'complete':False,'runtime_tested':False}
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE is active')

def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing production input '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record()
def clone(source,path):
    a=u.load_asset(path) or E.duplicate_asset(source,path)
    if not a:raise RuntimeError('Cannot duplicate '+source)
    return a

mount=clone('/Game/Weapons/RSH12/MaterialFinish20261005/MI_RSH12_RailInsert',D+'/Materials/MI_RSH12_TacticalMount')
save(mount)
wetmap={mount.get_path_name():mount}
materials={}
for kind in ('laser','flashlight'):
    dry=clone(SOURCE+'/M_DW715_Polymer_'+kind,D+'/Materials/M_RSH12_'+kind+'_Body')
    wet=clone(SOURCE+'/M_DW715_Polymer_'+kind+'_Wet',D+'/Materials/M_RSH12_'+kind+'_Wet')
    for material in (dry,wet):
        for flag in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):
            material.set_editor_property(flag,False)
        E.set_metadata_tag(material,'RSH_TacticalFinish','Original compact body UV0/normal/optical vertex mask; polymer exterior; RSH-only copy')
        errors=L.recompile_material(material)
        if errors:raise RuntimeError('Material compilation failed '+str(errors))
        save(material)
    materials[kind]=dry;wetmap[dry.get_path_name()]=wet
    receipt['materials'][kind]={'body':dry.get_path_name(),'wet':wet.get_path_name(),'mount':mount.get_path_name()}

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for kind,part in auth['parts'].items():
        name='SM_RSH12_'+kind
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=part['fbx'];task.destination_path=D+'/Meshes';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
        A.import_asset_tasks([task]);mesh=load(D+'/Meshes/'+name)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            slot.material_interface=mount if str(slot.material_slot_name)=='RSH_Tactical_Mount' else materials[kind]
            slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        settings=mesh_editor.get_lod_build_settings(mesh,0)
        settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
        mesh_editor.set_lod_build_settings(mesh,0,settings)
        for name,point in part['sockets_cm'].items():
            socket=mesh.find_socket(name)
            if not socket:
                socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*point))
        E.set_metadata_tag(mesh,'RSH_TacticalSource',part['source'])
        E.set_metadata_tag(mesh,'RSH_TacticalMount','Front lower-rail clamp with right-side offset bracket; UE +X forward/+Y right; native WPN_root .01 scale')
        E.set_metadata_tag(mesh,'SourceAttribution',auth['source_contact'])
        if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Mesh production build failed '+kind)
        save(mesh);receipt['meshes'][kind]=mesh.get_path_name()
        # Existing official common icons are already the preferred UI paths.
        icon='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/tactical_'+kind
        receipt['icons'][kind]={'shared_png':'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/tactical_'+kind+'.png','texture':load(icon).get_path_name()}
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

table=load('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
backup=O/'Before/DA_RSH12_WetMaterials.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(P/'Content/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.uasset',backup)
mapping=dict(table.get_editor_property('wet_materials'));mapping.update(wetmap)
table.set_editor_property('wet_materials',mapping);save(table)
receipt['complete']=True;record()
print('RSH_TACTICAL_ASSETS_SAVED',flush=True)
