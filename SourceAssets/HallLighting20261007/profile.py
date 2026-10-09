"""Abandoned reception/concourse lighting, shared by saved maps and author recipes."""
import copy
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/HallLighting20261007'
REVISION='abandoned_halls_20261008_brightness_v3'
PORTAL_CANOPY_LUMENS=672
PORTAL_TUNNEL_LUMENS=448
BOTANICAL_LUMENS=168
FAULTS={
 'Reception':{'Atrium_-14_6':'flicker','Atrium_0_6':'dead','Atrium_14_-6':'flicker',
              'Ground_-20_-13.25':'dead','Ground_4_13.25':'flicker',
              'Upper_7_-13.2':'flicker','Upper_21.4_7.6':'dead'},
 'Transit':{'Atrium_-12_-10':'dead','Atrium_13_10':'dead','Atrium_-12_10':'flicker',
            'Atrium_13_-10':'flicker','UnderGallery-12':'flicker','Gallery13':'flicker'},
}
EXPOSURE=dict(auto_exposure_min_brightness=.95,auto_exposure_max_brightness=.95,
              auto_exposure_bias=-.25,indirect_lighting_intensity=.8,bloom_intensity=.08,
              vignette_intensity=.25)


def material(name):return BASE+'/Materials/'+name


def revise_light(raw,group):
    p=copy.deepcopy(raw);key=p['id'];state=FAULTS[group].get(key,'steady')
    p.setdefault('original_intensity',p['intensity']);p.setdefault('original_radius',p['radius'])
    if group=='Reception':
        intensity=3000 if p['type']=='spot' else 680 if key.startswith('Upper') else 650
        if key.startswith('Vestibule'):intensity=500
    else:
        intensity=1900 if p['type']=='spot' else 600
        if key.startswith('Approach'):intensity=500
    # Absolute targets make recipe replay idempotent. Raise readable walking
    # light while keeping dead lamps, fault phases and exposure unchanged.
    intensity*=1.35 if p['type']=='spot' else 1.5 if key.startswith(('Upper','Gallery')) else 1.4
    p.update(intensity=0 if state=='dead' else intensity,radius=p['original_radius']*.88,
        fault=state,phase=(int(hashlib.sha1((group+key).encode()).hexdigest()[:6],16)%1970)/100.,
        # Keep the established faulty tube contrast and GPU timing.
        emission=(2.2 if p['type']=='spot' else 1.8) if state=='flicker' else (.8 if p['type']=='spot' else .65),
        color=[.72,.84,.80] if p['type']=='spot' else [.91,.82,.64],
        indirect_lighting_intensity=.08 if state=='flicker' else .32,
        volumetric_scattering_intensity=.06,
        max_draw_distance_cm=5000 if p['type']=='spot' else 3200,fade_range_cm=650)
    if state=='flicker':
        keyhash=hashlib.sha1((group+key).encode()).hexdigest()[:10]
        p['light_function']=material('MI_Fault_'+keyhash)
        p['light_function_fade_distance']=6000
    else:p.pop('light_function',None)
    return p


def revise_layout(cfg,group):
    cfg=copy.deepcopy(cfg)
    cfg['lights']=[revise_light(p,group) for p in cfg['lights']]
    cfg['lighting_revision']=REVISION
    cfg['lighting_profile_source']=str(ROOT/'profile.py')
    cfg['postprocess_lighting']=EXPOSURE
    return cfg


def diffuser_for_mesh(path):
    name=path.rsplit('/',1)[-1].split('.')[0]
    if name=='SM_Reception_LightDiffusers':return material('M_ReceptionDiffusers')
    if name=='SM_FT_Hall_Diffusers':return material('M_TransitDiffusers')
    if 'Diffuser' in name or name.endswith(('SecurityDetails','PanelIndicators','SconceShade')):
        return material('M_SteadyDiffuser')
    return None


def extend_draft(doc,group,layout):
    doc=copy.deepcopy(doc)
    module=doc['modules'][0] if 'modules' in doc else doc
    if group=='Reception':
        for light,p in zip(module['lights'],layout['lights']):
            for key in ('color','indirect_lighting_intensity','volumetric_scattering_intensity',
                        'light_function','light_function_fade_distance','max_draw_distance_cm','fade_range_cm'):
                if key in p:light[key]=p[key]
        module['postprocess_lighting']=EXPOSURE
    else:
        module['lights']=layout['lights']
        module['portal_lighting']=dict(canopy_lumens=PORTAL_CANOPY_LUMENS,tunnel_lumens=PORTAL_TUNNEL_LUMENS,
            indirect_lighting_intensity=.25,color=[.91,.82,.64],fault='steady')
        if module.get('central_display'):
            for p in module['central_display']['assembly']['lights']:p['intensity']=BOTANICAL_LUMENS
    assets=set()
    families=[module.get('parts',[])]+list(module.get('portal_families',{}).values())
    for parts in families:
        for p in parts:
            m=diffuser_for_mesh(p.get('mesh',''))
            if m and ('Diffuser' in p['mesh'] or p['mesh'].endswith(('PanelIndicators','SconceShade'))):
                p['materials']=[m];assets.add(m)
    assets.update(p['light_function'] for p in layout['lights'] if p.get('light_function'))
    module['lighting_revision']=REVISION
    module['runtime_assets']=sorted(set(module.get('runtime_assets',[]))|assets)
    if 'module_asset_paths' in doc:doc['module_asset_paths']=sorted(set(doc['module_asset_paths'])|assets)
    return doc


def apply_world():
    """Replay this lighting revision after a future scoped hall rebuild. No save here."""
    import json
    import unreal as u
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    layouts={g:json.loads((PROJECT/'SourceAssets'/folder/'Config/layout.json').read_text('utf8'))
             for g,folder in [('Reception','DungeonReceptionHall20261006'),('Transit','DungeonFacilityTransit20261007')]}
    bylabel={}
    for g,cfg in layouts.items():
        prefix='Reception_' if g=='Reception' else 'FacilityTransit_Hall_'
        for p in revise_layout(cfg,g)['lights']:bylabel[prefix+p['id']]=p
    changed=dict(lights=0,flicker=0,dead=0,diffusers=0,postprocess=0)
    cache={}
    def load(path):
        if path not in cache:
            cache[path]=u.load_asset(path)
            if not cache[path]:raise RuntimeError('Missing hall lighting asset '+path)
        return cache[path]
    for a in actors.get_all_level_actors():
        label=a.get_actor_label()
        if not label.startswith(('Reception_','FacilityTransit_')):continue
        p=bylabel.get(label)
        light=a.get_component_by_class(u.PointLightComponent)
        if light and (p or label.startswith('FacilityTransit_')):
            if not p:
                botanical='Botanical_Canopy' in label
                p=dict(intensity=BOTANICAL_LUMENS if botanical else PORTAL_CANOPY_LUMENS if label.endswith('_0') else PORTAL_TUNNEL_LUMENS,
                    indirect_lighting_intensity=.22 if botanical else .25,
                    volumetric_scattering_intensity=0.,color=[.72,.88,.70] if botanical else [.91,.82,.64],
                    fault='steady')
            a.modify();light.modify();light.set_mobility(u.ComponentMobility.MOVABLE)
            light.set_intensity(p['intensity'])
            if 'radius' in p:light.set_editor_property('attenuation_radius',p['radius']*100)
            light.set_light_color(u.LinearColor(*p['color'],1))
            for key in ('indirect_lighting_intensity','volumetric_scattering_intensity'):
                light.set_editor_property(key,p[key])
            if 'max_draw_distance_cm' in p:
                light.set_editor_property('max_draw_distance',p['max_draw_distance_cm'])
                light.set_editor_property('max_distance_fade_range',p['fade_range_cm'])
            light.set_light_function_material(load(p['light_function']) if p.get('light_function') else None)
            if p.get('light_function'):light.set_editor_property('light_function_fade_distance',p['light_function_fade_distance'])
            changed['lights']+=1
            if p['fault'] in ('flicker','dead'):changed[p['fault']]+=1
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            replacement=diffuser_for_mesh(c.static_mesh.get_path_name())
            if not replacement:continue
            for i in range(c.get_num_materials()):
                old=c.get_material(i)
                if old and ('M_Reception_Glow' in old.get_path_name() or old.get_path_name().startswith(BASE+'/')):
                    a.modify();c.modify();c.set_material(i,load(replacement));changed['diffusers']+=1
        if isinstance(a,u.PostProcessVolume) and label=='Reception_ExposureAndContainerOutline':
            a.modify();settings=a.get_editor_property('settings')
            for key,value in EXPOSURE.items():
                settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,value)
            # Preserve container outline blendables and all unrelated postprocessing.
            a.set_editor_property('settings',settings);changed['postprocess']+=1
    return changed


def reapply_if_installed():
    import json
    receipt=ROOT/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':
        return apply_world()
    return None
