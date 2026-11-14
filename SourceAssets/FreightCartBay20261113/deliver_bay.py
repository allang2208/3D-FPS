"""Use the rendered platform coating, anchored leaks and the sheltered dust layer."""
from pathlib import Path
import runpy,unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightCartBay20261113'
def apply(w,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    c=actors['CartBay_PlatformJointRubberDust'].get_component_by_class(u.DecalComponent);c.modify()
    c.set_decal_material(u.load_asset(BASE+'/Materials/M_PlatformWeathering'))
    overlay=actors.get('CartBay_FacadeMineralFilm')
    if overlay:
        api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        api.destroy_actor(overlay)
