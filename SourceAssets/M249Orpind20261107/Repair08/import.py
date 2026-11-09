"""Install six framed factory icons, articulated factory legs and corrected quick melee."""
from pathlib import Path
import unreal as u,json,gzip,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2];E=u.EditorAssetLibrary
if not (r/'DATA_MODEL_quick_melee.pkl').exists():
    import runpy
    runpy.run_path(str(r/'collect_model.py'))
    raise RuntimeError('Authoritative data-model motion captured; author the repair from it before installation')
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; stop play before saving M249 assets')
icon_dir='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
owned=['/Game/Weapons/M249/Animations/A_M249_quick_melee']+[icon_dir+'/'+p.stem for p in (r/'Icons').glob('*.png')]
owned += ['/Game/Weapons/M249/Bipod/'+p.stem for p in (r/'Exports').glob('*.fbx')]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(owned):raise RuntimeError('Preserve unsaved owned assets: '+str(dirty.intersection(owned)))
hashes=json.loads((r/'before_hashes.json').read_text())
for path,digest in hashes.items():
    if path.endswith('.uasset') and hashlib.sha256((project/path).read_bytes()).hexdigest()!=digest:raise RuntimeError('Asset changed during repair: '+path)
tasks=[]
for p in (r/'Icons').glob('*.png'):
    task=u.AssetImportTask();task.filename=str(p);task.destination_path=icon_dir;task.destination_name=p.stem
    task.automated=True;task.replace_existing=True;task.save=False;tasks.append(task)
for p in (r/'Exports').glob('*.fbx'):
    task=u.AssetImportTask();task.filename=str(p);task.destination_path='/Game/Weapons/M249/Bipod';task.destination_name=p.stem
    task.automated=True;task.replace_existing=True;task.save=False
    ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
    ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;ui.automated_import_should_detect_type=False
    ui.static_mesh_import_data.combine_meshes=True;ui.static_mesh_import_data.auto_generate_collision=False
    task.options=ui;tasks.append(task)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
saved=[]
for p in (r/'Icons').glob('*.png'):
    obj=u.load_asset(icon_dir+'/'+p.stem)
    if not obj:raise RuntimeError('Icon import failed '+p.stem)
    obj.srgb=True;obj.lod_group=u.TextureGroup.TEXTUREGROUP_UI;obj.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    obj.never_stream=True;obj.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save icon '+p.stem)
    saved.append(obj.get_path_name())
surface=u.load_asset('/Game/Weapons/M249/Surface20261108/Materials/MI_M249_Bipod_Static') or u.load_asset('/Game/Weapons/M249/Materials/M_M249_Surface')
for p in (r/'Exports').glob('*.fbx'):
    obj=u.load_asset('/Game/Weapons/M249/Bipod/'+p.stem)
    if not obj:raise RuntimeError('Bipod import failed '+p.stem)
    for i in range(len(obj.static_materials)):obj.set_material(i,surface)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save bipod '+p.stem)
    saved.append(obj.get_path_name())
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');clip=u.load_asset(owned[0])
with gzip.open(r/'quick_melee.json.gz','rt') as f:data=json.load(f)
ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 continuous right arm and baked handoff',False)
try:
    ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False)
    ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
    for bone,rows in data['tracks'].items():
        ctl.add_bone_curve(bone,False)
        if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Bone '+bone)
finally:ctl.close_bracket(False)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip,False):raise RuntimeError('Save quick melee')
saved.append(clip.get_path_name())
(r/'import_receipt.json').write_text(json.dumps(dict(saved=saved,factory_icons=6,texture_assets=12,bipod_parts=3,melee_duration=clip.get_play_length()),indent=2))
print('M249_REPAIR08_SAVED',len(saved),flush=True)
