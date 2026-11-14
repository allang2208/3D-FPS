"""Bind photographed color/opacity and registered roughness to the decal projection UV."""
from pathlib import Path
import runpy,unreal as u
r=Path(__file__).resolve().parent
lib=runpy.run_path(str(r/'build_bay.py'))
H=lib['H'];E=lib['E'];L=lib['L'];BASE=lib['BASE']
def direct(kind):
    m=H.own('Materials/M_'+kind+'Weathering');L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    uv=H.node(m,'TextureCoordinate',coordinate_index=0)
    for suffix,iscolor in [('PatinaColor',True),('PatinaRoughness',False)]:
        tex=lib['import_file']('T_'+kind+suffix);tex.modify()
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if iscolor else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('srgb',iscolor)
        if not E.save_loaded_asset(tex,False):raise RuntimeError(tex.get_name())
        s=lib['sample'](m,suffix,tex,lib['mask_sampler'](tex))
        if kind=='Wall':
            # Compensate the baked atlas rotation, mapping UE local +Z,+Y to +Z,-Y.
            orient=H.custom(m,'return float2(1.-UV.x,1.-UV.y);',dict(UV=uv),2);H.wire(orient,s,'UVs')
        else:H.wire(uv,s,'UVs')
        if iscolor:H.output(s,'BASE_COLOR','RGB');H.output(s,'OPACITY','A')
        else:H.output(s,'ROUGHNESS','R')
    return H.save(m)
def apply(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    for name,kind in [('CartBay_PlatformJointRubberDust','Platform'),('CartBay_DripAndToe','Wall')]:
        c=actors[name].get_component_by_class(u.DecalComponent)
        mat=u.load_asset(BASE+'/Materials/M_'+kind+'Weathering') if row.get('load_only') else direct(kind)
        c.modify();c.set_decal_material(mat);c.set_visibility(True,True)
