"""Save the corrected shirt pickup and equipment display to isolated packages."""
import importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/FieldRangerTop20261020';R=BASE/'CollarRepair20261021'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/CollarRepair20261021'
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving collar display assets')
editable=read(R/'editable.json')
if not editable['completed']:raise RuntimeError('Collar model export is incomplete')
mesh_io=module('collar_static_io','Tools/ChainmailPants/save_assets.py');mesh_io.DEST=DEST
display_io=module('collar_display_geometry','Tools/BlueMageSetIcons/save_icons.py')
mats=[u.load_asset(p) for p in read(BASE/'materials.json')['materials']];mats.append(mats[2])
T=u.GeometryScript_MeshTransforms
d=read(R/'Authored/ue_field_sweater/Jason.json');dm=display_io.dynamic(d)
center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)]
T.translate_mesh(dm,u.Vector(*[-v for v in center]));T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
pickup=mesh_io.static(dm,DEST+'/Pickups/SM_FieldRangerTop',mats)
dm=display_io.dynamic(read(Path(editable['display'])));T.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)))
icon=mesh_io.static(dm,DEST+'/Icons/SM_FieldRangerTop_Icon',mats)
task=u.AssetImportTask();task.filename=editable['icon'];task.destination_path=DEST+'/Icons';task.destination_name='T_FieldRangerTop_Icon';task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(DEST+'/Icons/T_FieldRangerTop_Icon')
for key,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():texture.set_editor_property(key,value)
mesh_io.save(texture)
(R/'display_assets.json').write_text(json.dumps(dict(completed=True,pickup=pickup,icon=icon,texture=texture.get_path_name(),runtime_tested=False),indent=2),encoding='utf-8')
print('COLLAR_DISPLAY_SAVED',flush=True)
