from pathlib import Path
import json,sys
import unreal as u
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(u.Paths.project_dir())/'Tools/Skills'))
from build_fireball_assets import API,ref
s=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold')
for method in ('GetSystemData','GetEmitterData'):
    r=API.call_method(method,(s,) if method=='GetSystemData' else (ref(s,'BaguaRisingGold'),))
    (OUT/(method+'.json')).write_text(r.get_editor_property('property_values'),encoding='utf-8')
print('PIE '+str(u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()))
print('NIAGARA_METHODS '+str([n for n in dir(s) if any(x in n for x in ['valid','compil','ready','error'])]))
print('TOOLS_METHODS '+str([n for n in dir(u.RainAssetEditor) if any(x in n for x in ['valid','compil','ready','error','debug'])]))
print('NEW '+str(hasattr(u,'new_object')))
print('RENDER '+str([n for n in dir(u.RenderingLibrary) if any(x in n for x in ['render_target','export'])]))
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('WORLD '+str(w))
if w:
    a=u.GameplayStatics.get_player_character(w,0)
    if a:print('ACTOR '+str(a)+' '+str([c.get_name() for c in a.get_components_by_class(u.DynamicMeshComponent)]))
