"""Read only the two target meshes before producing their replacement source."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[1]
out=root/'Receipts';out.mkdir(parents=True,exist_ok=True)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
result={'playing':bool(ue and ue.get_game_world()),'meshes':{}}
for key in ('PowerCabinet','CargoStack'):
    path='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_'+key
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing target '+path)
    result['meshes'][key]={'path':path,'dirty':path in dirty,
        'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.get_editor_property('static_materials')],
        'nanite':mesh.get_editor_property('nanite_settings').enabled}
(out/'inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('FACILITY_POLISH_INPUTS '+json.dumps(result))
