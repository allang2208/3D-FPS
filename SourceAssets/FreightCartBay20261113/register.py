import unreal as u
from pathlib import Path
import runpy
def apply(w,row):
    lib=runpy.run_path(str(Path(__file__).with_name('build_bay.py')))
    H=lib['H'];L=lib['L'];base=lib['BASE']
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    floor=actors['CartBay_PlatformJointRubberDust'];floor.modify();floor.set_actor_location(u.Vector(8517,-400,-2.0),False,False)
    floor.get_component_by_class(u.DecalComponent).set_editor_property('decal_size',u.Vector(.22,200,200))
    actor=actors['CartBay_DripAndToe'];c=actor.get_component_by_class(u.DecalComponent);c.modify()
    donor='/Game/SceneTests/FreightStationUnifiedPatina20261111/Materials/MI_LeakSoft'
    c.set_decal_material(u.load_asset(donor))
    # Keep the legacy receiver and align the source to the cap's near joint.
    actor.modify();actor.set_actor_location(u.Vector(8321.8,-264.8,58.),False,False)
    c.set_editor_property('decal_size',u.Vector(.9,16.,29.))
