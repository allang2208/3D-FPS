from pathlib import Path
import runpy,unreal as u
r=Path(__file__).resolve().parent
lib=runpy.run_path(str(r/'build_bay.py'))
H,L,E,BASE=(lib[k] for k in ('H','L','E','BASE'))
def finished(kind):
    m=H.own('Materials/M_'+kind+'Finish');L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    tex=lib['import_file']('T_'+kind+'FinishCoverage')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT);tex.set_editor_property('srgb',True);E.save_loaded_asset(tex,False)
    uv=H.node(m,'TextureCoordinate',coordinate_index=0)
    col=lib['sample'](m,'CoverageColor',tex,lib['mask_sampler'](tex))
    roughtex=u.load_asset(BASE+'/Textures/T_'+kind+'PatinaRoughness')
    rough=lib['sample'](m,'CoverageRough',roughtex,lib['mask_sampler'](roughtex))
    if kind=='Wall':uv=H.custom(m,'return 1.-UV;',dict(UV=uv),2)
    H.wire(uv,col,'UVs');H.wire(uv,rough,'UVs')
    H.output(col,'BASE_COLOR','RGB');H.output(col,'OPACITY','A');H.output(rough,'ROUGHNESS','R')
    return H.save(m)
def apply(w,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    def decal(label,pos,rot,size,mat,order):
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.DecalActor,u.Vector(*pos),rot);a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
        a.modify();a.set_actor_location_and_rotation(u.Vector(*pos),rot,False,False)
        c=a.get_component_by_class(u.DecalComponent);c.modify();c.set_editor_property('decal_size',u.Vector(*size));c.set_decal_material(mat)
        c.set_editor_property('fade_screen_size',.0001);c.set_editor_property('sort_order',order);c.set_visibility(True,True)
    mats={k:(u.load_asset(BASE+'/Materials/M_'+k+'Finish') if row.get('load_only') else finished(k)) for k in ('Platform','Wall')}
    a=actors['CartBay_ConcreteDadoAndCoping'];a.modify();a.set_actor_location(u.Vector(8317,-332,-2.04),False,False)
    decal('CartBay_PlatformJointRubberDust',(8517,-400,-2),u.Rotator(pitch=-90),(.22,200,200),mats['Platform'],8)
    decal('CartBay_FacadeMineralFilm',(8319,-332,116),u.Rotator(yaw=180),(5.35,216,118),mats['Wall'],5)
    stock='/Game/SceneTests/FreightStationUnifiedPatina20261111/Materials/'
    decal('CartBay_DripAndToe',(8321.8,-264.8,54),u.Rotator(yaw=180),(.95,12,31),u.load_asset(stock+'MI_LeakSoft'),9)
    decal('CartBay_FarCopingDrip',(8321.8,-402,46),u.Rotator(yaw=180),(.95,8,38),u.load_asset(stock+'MI_LeakSoft'),9)
    decal('CartBay_ShelteredWallToe',(8334,-332,-2),u.Rotator(pitch=-90),(.22,195,17),u.load_asset(stock+'MI_DustEdge'),10)
