"""Import and save fitted common accessories; no world, render or gameplay tests."""
import unreal as u, json, re, hashlib, shutil, importlib.util
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
DEST = '/Game/Weapons/PitViper2011/Attachments20261002'
BODY = '/Game/Weapons/PitViper2011/Integrated20261002/Materials'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
auth = json.loads((O/'authoring.json').read_text())
receipt = {'saved': [], 'meshes': {}, 'shared_icons': {}, 'runtime_tested': False, 'rendered_for_acceptance': False}

def record(): (O/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing production dependency '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()], False):
        raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']: receipt['saved'].append(obj.get_path_name())
    record()
def canonical(name): return re.sub(r'[._]\d{3}$', '', name)

if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve() != (P/'Content').resolve():
    raise RuntimeError('Wrong project content mount')
targets = {DEST+'/'+v['name'] for v in auth.values()}
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty: raise RuntimeError('Preserve unsaved Pit Viper target assets: '+str(dirty))

metal = load(BODY+'/MI_PitViper2011_h_190')
steel = load(BODY+'/MI_PitViper2011_Magazine_stell')
polymer = load(BODY+'/MI_PitViper2011_Magazine_polymer')
bindings = {
    'M_PitViper2011_Magazine_stell': steel, 'M_PitViper2011_Magazine_polymer': polymer,
    'M_pistol_grip_granular': load('/Game/Weapons/PistolGripSurface20260927/Materials/M_pistol_grip_granular'),
    'M_HoloReticle': load('/Game/Weapons/M4Holographic/M_HoloReticle'),
    'M_Panoramic_Glass': load('/Game/Weapons/PanoramicRedDot/M_Panoramic_Glass'),
    'M_Panoramic_Reticle': load('/Game/Weapons/PanoramicRedDot/M_Panoramic_Reticle'),
    'M_Tactical_laser': load('/Game/Weapons/M1911/Tactical20260913/Materials/M_M1911_laser_Body'),
    'M_Tactical_flashlight': load('/Game/Weapons/M1911/Tactical20260913/Materials/M_M1911_flashlight_Body'),
}
recess = load('/Game/Weapons/M4MuzzlesV1/MI_MuzzleRecess')
for label in ('RecessMetal', 'MI_MuzzleRecess', 'TacticalRecess'): bindings[label] = recess
eoth = load('/Game/Weapons/CommonHK41620260930/Meshes/SM_M1911_eoth_holographic')
for slot in eoth.static_materials:
    name = canonical(str(slot.material_slot_name))
    if name in ('M_HK416_Glass', 'M_HK416_Eo_tech_Reticle'): bindings[name] = slot.material_interface
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
    for key, entry in auth.items():
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh = True; opt.import_materials = False; opt.import_textures = False
        opt.import_animations = False; opt.override_full_name = True
        settings = opt.static_mesh_import_data
        settings.combine_meshes = True; settings.auto_generate_collision = False; settings.generate_lightmap_u_vs = False
        settings.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        settings.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        task = u.AssetImportTask()
        task.filename = entry['fbx']; task.destination_path = DEST; task.destination_name = entry['name']
        task.automated = True; task.replace_existing = True; task.replace_existing_settings = True
        task.save = False; task.options = opt; task.factory = u.FbxFactory()
        path = DEST+'/'+entry['name']
        signature = hashlib.sha256(Path(entry['fbx']).read_bytes()).hexdigest()
        mesh = u.load_asset(path)
        if not mesh or E.get_metadata_tag(mesh, 'PitViperAttachmentSourceSHA256') != signature:
            A.import_asset_tasks([task]); mesh = load(path)
        slots = list(mesh.static_materials)
        for i, slot in enumerate(slots):
            label = canonical(str(slot.material_slot_name))
            slot.material_interface = bindings.get(label, metal)
            slots[i] = slot
        mesh.set_editor_property('static_materials', slots)
        for name, p in entry['sockets_blender_m'].items():
            socket = mesh.find_socket(name)
            if not socket:
                socket = u.new_object(u.StaticMeshSocket, outer=mesh)
                socket.set_editor_property('socket_name', name); mesh.add_socket(socket)
            socket.set_editor_property('relative_location', u.Vector(p[0]*100, -p[1]*100, p[2]*100))
        if editor:
            build = editor.get_lod_build_settings(mesh, 0)
            build.use_full_precision_u_vs = True; editor.set_lod_build_settings(mesh, 0, build)
        E.set_metadata_tag(mesh, 'PitViperAttachmentSourceSHA256', signature)
        E.set_metadata_tag(mesh, 'WeaponSurfaceHost', 'Pit Viper own clean finish; source UV0 and optical materials retained')
        E.set_metadata_tag(mesh, 'FittedInterfaceSource', str(O/'authoring.json'))
        save(mesh)
        receipt['meshes'][key] = {'asset': mesh.get_path_name(), 'source': entry['fbx'],
            'materials': {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots},
            'sockets_cm': {name: [p[0]*100, -p[1]*100, p[2]*100] for name, p in entry['sockets_blender_m'].items()}}
        record(); print('PIT_VIPER_ATTACHMENT_SAVED', key, flush=True)
finally: u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))

# Promote existing approved images to shared keys once. No image generation or
# per-weapon copies; the UI reads this common directory for all firearm hosts.
icon_dir = P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
keys = ['reargrip_pistol_grip_granular', 'reargrip_pistol_grip_diamond', 'reargrip_pistol_grip_quickdot', 'category_trigger']
for key in keys:
    target = icon_dir/(key+'.png'); source = icon_dir/('ue_m1911_'+key+'.png')
    if not target.exists(): shutil.copy2(source, target)
    receipt['shared_icons'][key] = {'file': str(target), 'reused_from': str(source), 'generated': False}
record()
script = O/'publish_catalog.py'
exec(compile(script.read_text(encoding='utf8'), str(script), 'exec'), {'__file__': str(script), '__name__': '__main__'})
receipt.update(status='imported_and_saved', catalog_published=True, shared_icons_published=True)
record(); print('PIT_VIPER_COMMON_ATTACHMENTS_IMPORT_AND_SAVE_COMPLETE', len(receipt['meshes']), flush=True)
finish=O.parent/'PitViper2011SurfaceRefine20261003/restore_saved_finish.py'
if finish.exists():
    import runpy
    runpy.run_path(str(finish),run_name='__main__')
