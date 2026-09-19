"""Import the eleven authored rifle clips; no runtime checks or rendering."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
manifest=json.loads((P/'authoring.json').read_text())
tools=u.AssetToolsHelpers.get_asset_tools();receipt={}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for weapon,spec in manifest['weapons'].items():
        mesh=u.load_asset(spec['mesh'])
        compression=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/BC_AKM_GripPrecision'
                                 if weapon=='AKM' else '/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
        for profile,item in spec['profiles'].items():
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
            options.skeleton=mesh.skeleton
            options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
            options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
            task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=item['asset'].rsplit('/',1)[0]
            task.destination_name=item['asset'].rsplit('/',1)[1];task.options=options;task.automated=True
            task.replace_existing=True;task.save=False
            tools.import_asset_tasks([task]);clip=u.load_asset(item['asset'])
            if not clip:raise RuntimeError('Import failed: '+item['asset'])
            clip.set_editor_property('bone_compression_settings',compression)
            if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+item['asset'])
            receipt[weapon+':'+profile]={'asset':clip.get_path_name(),'length':clip.get_play_length()}
            u.log('RIFLE_N_IMPORTED '+weapon+' '+profile)
    (P/'import.json').write_text(json.dumps({'animations':receipt,'status':'Imported and saved; user testing pending'},indent=2))
    u.log('RIFLE_N_IMPORT_COMPLETE %d'%len(receipt))
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {previous}')
