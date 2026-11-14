from pathlib import Path
import runpy,unreal as u
root=Path(__file__).resolve().parent
lib=runpy.run_path(str(root/'build_bay.py'))
base=lib['BASE'];H=lib['H'];L=lib['L'];E=lib['E']
def apply(w,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    master=u.load_asset(base+'/Materials/M_PlatformWeathering')
    for name,kind in [('CartBay_PlatformJointRubberDust','Platform'),('CartBay_FacadeMineralFilm','Wall')]:
        if row.get('load_only'):mi=u.load_asset(base+'/Materials/MI_'+kind+'Calibrated')
        else:
            mi=H.own('Materials/MI_'+kind+'Calibrated',u.MaterialInstanceConstant)
            L.set_material_instance_parent(mi,master)
            for param,suffix in [('PatinaColor','FinishCoverage'),('PatinaRoughness','PatinaRoughness')]:
                tex=u.load_asset(base+'/Textures/T_'+kind+suffix)
                if not L.set_material_instance_texture_parameter_value(mi,param,tex):raise RuntimeError('Unbound parameter '+param)
            H.save(mi)
        c=actors[name].get_component_by_class(u.DecalComponent);c.modify();c.set_decal_material(mi)
