"""Read the current editor state and only this blade's material/texture packages."""
import unreal as u, json
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[3]
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
receipt = {'playing': bool(editor.is_in_play_in_editor()), 'assets': []}
dirty_packages = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
catalog = json.loads((ROOT/'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
row = catalog['slots']['blade_1']['tengyun_dragon']
paths = [row['mesh'].split('.')[0],
    '/Game/Weapons/TangDao20261002/CloudRune20261002/Materials/M_TangDaoBladeRuneSurface_CloudTengyun']
paths += ['/Game/Weapons/TangDao20261002/TengyunBlade20261002/Textures/T_TangDao_Tengyun_'+key
          for key in ['BaseColor', 'Normal', 'ORM']]
for path in paths:
    obj = u.load_asset(path)
    info = {'path': path, 'exists': bool(obj)}
    if obj:
        info['dirty'] = obj.get_outermost().get_path_name() in dirty_packages
        if isinstance(obj, u.StaticMesh):
            info['slots'] = [str(s.material_slot_name) for s in obj.static_materials]
    receipt['assets'].append(info)
(P/'editor-state.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('TENGYUN_JOINT_EDITOR_STATE', json.dumps(receipt, ensure_ascii=False), flush=True)
