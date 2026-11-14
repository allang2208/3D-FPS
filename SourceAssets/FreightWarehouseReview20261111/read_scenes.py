"""Read saved scene composition for the requested warehouse review. Never save assets."""
from pathlib import Path
from collections import Counter
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
MAPS={'current':'/Game/GameMaps/Design/L_FreightTransit_Theme_Subject',
      'baseline':'/Game/GameMaps/Design/L_FreightTransit_BeforeWeathering',
      'reference':'/Game/UndergroundTunnel/Maps/Demonstration'}
L=u.MaterialEditingLibrary
def v(x):return list(x.to_tuple())
def prop(obj,key):
    try:
        x=obj.get_editor_property(key)
        if isinstance(x,u.Object):return x.get_path_name()
        if isinstance(x,u.LinearColor):return [x.r,x.g,x.b,x.a]
        if isinstance(x,u.Color):return [x.r,x.g,x.b,x.a]
        if isinstance(x,(u.Vector,u.Rotator)):return v(x)
        if isinstance(x,(str,int,float,bool)) or x is None:return x
        return str(x)
    except Exception:return None
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
if any('/__ExternalActors__/' in p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved scene actors')
previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
report={'maps':{},'materials':{},'assets_saved':False,'game_run':False,'rendered':False}
def mat(m):
    if not m:return None
    path=m.get_path_name()
    if path in report['materials']:return path
    b=m.get_base_material()
    report['materials'][path]={'parent':prop(m,'parent'),'base':b.get_path_name(),
        'domain':prop(b,'material_domain'),'blend_mode':prop(b,'blend_mode')}
    return path
for label,path in MAPS.items():
    w=u.EditorLoadingAndSavingUtils.load_map(path)
    if not w:raise RuntimeError('Scene unavailable '+path)
    actors=list(u.GameplayStatics.get_all_actors_of_class(w,u.Actor))
    rows=[];lights=[];decals=[];post=[];fogs=[]
    for a in actors:
        p=a.get_actor_location();center,extent=a.get_actor_bounds(False)
        row={'name':a.get_name(),'label':a.get_actor_label(),'class':a.get_class().get_name(),
             'position':v(p),'rotation':v(a.get_actor_rotation()),'scale':v(a.get_actor_scale3d()),
             'center':v(center),'extent':v(extent),'tags':[str(t) for t in a.tags],'meshes':[]}
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            t=c.get_world_transform();box=c.static_mesh.get_bounding_box()
            row['meshes'].append({'name':c.get_name(),'mesh':c.static_mesh.get_path_name(),'position':v(t.translation),
                'rotation':v(t.rotation.rotator()),'scale':v(t.scale3d),'local_min':v(box.min),'local_max':v(box.max),
                'materials':[mat(c.get_material(i)) for i in range(c.get_num_materials())],
                'collision':str(c.get_collision_enabled()),'cast_shadow':prop(c,'cast_shadow'),
                'visible':prop(c,'visible'),'hidden_in_game':prop(c,'hidden_in_game'),
                'instances':c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1})
        if row['meshes']:rows.append(row)
        for c in a.get_components_by_class(u.LightComponent):
            t=c.get_world_transform()
            lights.append({'actor':a.get_name(),'label':a.get_actor_label(),'class':c.get_class().get_name(),
                'position':v(t.translation),'rotation':v(t.rotation.rotator()),
                **{key:prop(c,key) for key in ('intensity','intensity_units','attenuation_radius','cast_shadows','mobility','light_color','indirect_lighting_intensity','visible','inner_cone_angle','outer_cone_angle','source_width','source_height')}})
        for c in a.get_components_by_class(u.DecalComponent):
            t=c.get_world_transform()
            decals.append({'actor':a.get_name(),'label':a.get_actor_label(),'position':v(t.translation),'rotation':v(t.rotation.rotator()),
                'material':mat(c.get_decal_material()),'size':prop(c,'decal_size'),'sort_order':prop(c,'sort_order')})
        if isinstance(a,u.PostProcessVolume):
            settings=a.get_editor_property('settings')
            post.append({'actor':a.get_name(),'label':a.get_actor_label(),'unbound':prop(a,'unbound'),'priority':prop(a,'priority'),'enabled':prop(a,'enabled'),'blend_weight':prop(a,'blend_weight'),
                **{key:prop(settings,key) for key in ('override_auto_exposure_method','override_auto_exposure_min_brightness','override_auto_exposure_max_brightness','override_auto_exposure_bias','override_bloom_intensity','override_color_saturation','color_saturation','auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','bloom_intensity','override_dynamic_global_illumination_method','dynamic_global_illumination_method','override_reflection_method','reflection_method')}})
        if isinstance(a,u.ExponentialHeightFog):
            for c in a.get_components_by_class(u.ExponentialHeightFogComponent):
                fogs.append({key:prop(c,key) for key in ('fog_density','fog_height_falloff','volumetric_fog','volumetric_fog_scattering_distribution')})
    report['maps'][label]={'path':path,'classes':dict(Counter(a.get_class().get_name() for a in actors)),
        'actors':rows,'lights':lights,'decals':decals,'post_process':post,'fog':fogs}
    (ROOT/'scene-inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('WAREHOUSE_REVIEW_READ '+label+' meshes='+str(len(rows))+' lights='+str(len(lights))+' decals='+str(len(decals)),flush=True)
if previous and not previous.startswith('/Temp/') and previous not in MAPS.values():u.EditorLoadingAndSavingUtils.load_map(previous)
print('WAREHOUSE_SCENE_REVIEW_READ_COMPLETE',flush=True)
