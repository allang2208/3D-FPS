"""Check only the installed PNG decoder path; no PIE or player/profile mutation."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
path=Path(u.Paths.project_content_dir())/'ColdSteelData/Icons/ue_a762.png'
texture=u.RenderingLibrary.import_file_as_texture2d(world,str(path))
if not texture:raise RuntimeError('UE could not decode installed A762 icon')
result={'file':str(path),'loaded_class':texture.get_class().get_name(),'size':[texture.blueprint_get_size_x(),texture.blueprint_get_size_y()],'game_tested':False}
assert result['size']==[768,320]
(O/'ue_decode.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('A762_CATALOG_ICON_DECODED_768x320')
