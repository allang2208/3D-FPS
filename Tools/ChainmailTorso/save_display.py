"""Save worn-geometry-matched pickup and UI meshes without changing recipes."""
import importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailTorsoRepair20261021'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailTorsoRepair20261021'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End PIE before saving display assets')
io=module('mail_display_save','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
geom=module('mail_display_geometry','Tools/BlueMageSetIcons/save_icons.py');T=u.GeometryScript_MeshTransforms
d=read(R/'Authored/ue_chainmail_shirt/Jason.json');mats=[u.load_asset(p) for p in d['materials']]
dm=geom.dynamic(d);center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)]
T.translate_mesh(dm,u.Vector(*[-x for x in center]));T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
pickup=io.static(dm,DEST+'/Pickups/SM_ChainmailShirt',mats)
editable=read(R/'editable.json');dm=geom.dynamic(read(Path(editable['display'])))
T.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)))
icon=io.static(dm,DEST+'/Icons/SM_ChainmailShirt_Icon',mats)
task=u.AssetImportTask();task.filename=editable['icon'];task.destination_path=DEST+'/Icons';task.destination_name='T_ChainmailShirt_Icon';task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=u.load_asset(DEST+'/Icons/T_ChainmailShirt_Icon')
for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():texture.set_editor_property(k,v)
io.save(texture)
(R/'display_assets.json').write_text(json.dumps(dict(completed=True,pickup=pickup,icon=icon,texture=texture.get_path_name(),runtime_tested=False),indent=2),encoding='utf-8')
print('CHAINMAIL_DISPLAY_SAVED',flush=True)
