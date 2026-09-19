"""Read back the installed battle axe assets with tolerant property access. Read-only.

UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
report = {}
EAL = u.EditorAssetLibrary


def vec(v):
    return None if v is None else [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def editor_subsystem(cls):
    # Commandlets do not automatically instantiate all editor subsystems.
    return u.get_editor_subsystem(cls) or u.new_object(cls)


def safe(call, *args):
    try:
        return call(*args)
    except Exception as error:
        return 'ERR ' + str(error)


def stat(path):
    asset = u.load_asset(path)
    if not asset:
        return {'asset': path, 'loaded': False}
    entry = {'asset': path, 'loaded': True, 'class': asset.get_class().get_name()}
    if isinstance(asset, u.StaticMesh):
        bounds = asset.get_bounds()
        entry['bounds'] = {'origin': vec(bounds.origin), 'extent': vec(bounds.box_extent)}
        entry['materials'] = []
        for i in range(len(asset.get_editor_property('static_materials'))):
            material = asset.get_material(i)
            entry['materials'].append(str(material.get_path_name()) if material else None)
        editor = editor_subsystem(u.StaticMeshEditorSubsystem)
        entry['lod_count'] = safe(editor.get_lod_count, asset) if editor else None
        count = entry['lod_count']
        entry['lod_triangles'] = [safe(asset.get_num_triangles, i) for i in range(count)]             if isinstance(count, int) else None
    if isinstance(asset, u.SkeletalMesh):
        for key in ['skeleton', 'Skeleton']:
            try:
                value = asset.get_editor_property(key)
                entry['skeleton_' + key] = value.get_path_name() if value else None
            except Exception as error:
                entry['skeleton_' + key] = 'ERR ' + str(error)
        entry['materials'] = [str(s.material_slot_name) + '=' + (str(s.material_interface.get_path_name()) if s.material_interface else 'None')
                              for s in asset.get_editor_property('materials')]
        bounds = asset.get_bounds()
        entry['bounds'] = {'origin': vec(bounds.origin), 'extent': vec(bounds.box_extent)}
        entry['positive_ext'] = vec(asset.get_editor_property('positive_bounds_extension'))
        try:
            editor = editor_subsystem(u.SkeletalMeshEditorSubsystem)
            count = editor.get_lod_count(asset)
            entry['lod_count'] = count
            entry['lod_triangles'] = [editor.get_lod_triangle_count(asset, i) for i in range(count)]
        except Exception as error:
            entry['lod_error'] = str(error)
    if isinstance(asset, u.Material):
        entry['expressions'] = len(u.MaterialEditingLibrary.get_material_expressions(asset))
        entry['blend'] = asset.get_editor_property('blend_mode').name
        entry['two_sided'] = asset.get_editor_property('two_sided')
        entry['used_with_skeletal'] = asset.get_editor_property('used_with_skeletal_mesh')
    if isinstance(asset, u.Texture2D):
        entry['size'] = [asset.blueprint_get_size_x(), asset.blueprint_get_size_y()]
        entry['srgb'] = asset.get_editor_property('srgb')
        entry['flip_green'] = asset.get_editor_property('flip_green_channel')
        entry['compression'] = asset.get_editor_property('compression_settings').name
    return entry


report['sm_battle_axe'] = stat('/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe')
report['m_battle_axe'] = stat('/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe')
report['viewmodel'] = stat('/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe')
report['skeleton_exists'] = EAL.does_asset_exist('/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe_Skeleton')
report['anim_exists'] = {clip: EAL.does_asset_exist(f'/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_{clip}')
                         for clip in ['Idle', 'Walk', 'Equip', 'Swing', 'HitRecover']}
report['harvest_material'] = stat('/Game/Items/ProductionTools/GripMotion20260913/M_Harvest_Axe')
for channel in ['BaseColor', 'Normal', 'Metallic', 'Roughness']:
    report['tex_' + channel] = stat(f'/Game/Items/ProductionTools/BattleAxe20260919/T_BattleAxe_{channel}')

animation = u.load_asset('/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle')
if animation:
    skeleton = animation.get_editor_property('skeleton')
    report['anim_idle'] = {'skeleton': skeleton.get_path_name() if skeleton else None,
                           'length': round(animation.get_play_length(), 4)}
report['retired_mesh_still_loadable'] = bool(u.load_asset('/Game/Items/ProductionTools/FreeFab20260913/Axe/SM_Free_Axe'))

(ROOT / 'SourceAssets/BattleAxeReplace20260919/readback.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
u.log('BATTLE_AXE_READBACK_DONE')