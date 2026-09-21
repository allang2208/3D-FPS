"""Read the existing view's post-process sources to locate the supplied rim.
Does not start gameplay, alter the scene, render or capture a screenshot.
"""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
rows=[]
def pp(label,settings,extra=None):
    r={'owner':label,'blendables':[], **(extra or {})}
    for entry in settings.get_editor_property('weighted_blendables').get_editor_property('array'):
        asset=entry.get_editor_property('object')
        item={'weight':entry.get_editor_property('weight'),'asset':asset.get_path_name() if asset else None}
        if isinstance(asset,u.MaterialInstance):
            item['parent']=asset.get_editor_property('parent').get_path_name()
        r['blendables'].append(item)
    for field in ['vignette_intensity','scene_fringe_intensity','bloom_dirt_mask_intensity','bloom_dirt_mask_tint']:
        r[field]=str(settings.get_editor_property(field))
        r['override_'+field]=settings.get_editor_property('override_'+field)
    rows.append(r)
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world() or sub.get_editor_world()
pawn=u.GameplayStatics.get_player_pawn(world,0)
if pawn:
    for camera in pawn.get_components_by_class(u.CameraComponent):
        pp(camera.get_path_name(),camera.get_editor_property('post_process_settings'))
for cls in [u.PostProcessVolume]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,cls):
        pp(actor.get_path_name(),actor.get_editor_property('settings'),{'enabled':actor.get_editor_property('enabled'),'weight':actor.get_editor_property('blend_weight')})
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    for component in actor.get_components_by_class(u.PostProcessComponent):
        pp(component.get_path_name(),component.get_editor_property('settings'),{'enabled':component.get_editor_property('enabled'),'weight':component.get_editor_property('blend_weight')})
result={'world':world.get_path_name(),'post_process':rows}
(P/'screen-overlay-sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
