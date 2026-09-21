"""Finish the unchanged focus material's shader build; no gameplay run."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
material=u.load_asset('/Game/Skills/Whirlwind20260920/M_WhirlwindFocus')
if not material:raise RuntimeError('Missing whirlwind focus material')
# GetStatistics waits for this material's outstanding shader compilation.
u.MaterialEditingLibrary.get_statistics(material)
# No material graph or parameters changed in this correction. Shader output
# goes to the derived-data cache; do not resave the unchanged package.
(P/'focus-build-no-fallback.json').write_text(json.dumps({'asset':material.get_path_name(),'material_graph_changed':False,'pending_shader_build_finished':True,'tested':False},indent=2),encoding='utf-8')
print('WHIRLWIND_FOCUS_SHADER_BUILD_FINISHED')
