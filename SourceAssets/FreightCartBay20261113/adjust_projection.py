import unreal as u
from pathlib import Path
import runpy
def apply(w,row):
    base=runpy.run_path(str(Path(__file__).with_name('project_layers.py')))
    marks={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    c=marks['CartBay_DripAndToe'].get_component_by_class(u.DecalComponent);c.modify()
    mat=u.load_asset(base['BASE']+'/Materials/M_WallWeathering') if row.get('load_only') else base['direct']('Wall')
    c.set_decal_material(mat);c.set_visibility(True,True)
    c=marks['CartBay_PlatformJointRubberDust'].get_component_by_class(u.DecalComponent)
    c.modify();c.set_editor_property('decal_size',u.Vector(1.3,200,200));c.set_visibility(True,True)
