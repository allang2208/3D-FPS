"""Import the five accepted leather/stitch textures from licensed local sources."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
DEST = '/Game/Characters/ArmsLeatherCandidate'
SOURCE = '/Game/Weapons/M4InfimaV3'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
config_path = OUT/'source_maps.json'
config = json.loads(config_path.read_text())
report = {'listing':'https://www.fab.com/listings/ccd7a956-27f6-4417-b4e0-d1eb92e55ea0',
          'fab_imported':bool(config), 'runtime_applied':False, 'textures':[]}
def imported(path, name, kind, flip_green=False):
    path = Path(path)
    assert path.is_file(), path
    task = u.AssetImportTask()
    task.filename = str(path)
    task.destination_path, task.destination_name = DEST+'/Textures', name
    task.automated, task.replace_existing, task.save = True, True, True
    A.import_asset_tasks([task])
    tex = u.load_asset(DEST+'/Textures/'+name)
    assert tex
    tex.set_editor_property('srgb', kind=='color')
    tex.set_editor_property('compression_settings',{
        'color':u.TextureCompressionSettings.TC_DEFAULT,
        'normal':u.TextureCompressionSettings.TC_NORMALMAP,
        'mask':u.TextureCompressionSettings.TC_MASKS}[kind])
    if kind=='normal':
        tex.set_editor_property('flip_green_channel',flip_green)
    assert E.save_loaded_asset(tex,False)
    report['textures'].append({'source':str(path),'asset':tex.get_path_name(),
                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return tex
regions = imported(OUT/'T_Manny_LeatherRegions.png','T_Manny_LeatherRegions','mask')
thread = imported(OUT/'T_Manny_StitchNormal.png','T_Manny_StitchNormal','normal')
assert config['listing']==report['listing'], 'Review a different Fab listing before importing.'
color = imported(config['basecolor'],'T_Fab_Leather_BaseColor','color')
normal = imported(config['normal'],'T_Fab_Leather_Normal','normal',config['normal_convention']=='OpenGL')
rough = imported(config['roughness'],'T_Fab_Leather_Roughness','mask')
(OUT/'leather_import_report.json').write_text(json.dumps(report,indent=2))
u.log('HAND_LEATHER_TEXTURES_IMPORT_PASS')
