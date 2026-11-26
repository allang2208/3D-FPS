"""Scene-local migration from the old fixed study rig to the UDS sky."""
import unreal as u

SKY_CLASS = '/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C'
LEGACY = {'DirectionalLight_0': u.DirectionalLight,
          'SkyLight_0': u.SkyLight, 'SkyAtmosphere_0': u.SkyAtmosphere}

def configure_hills_sky():
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_name() != 'L_TemperateHills_Initial':
        raise RuntimeError('Hills sky migration only owns L_TemperateHills_Initial')
    cls = u.load_object(None, SKY_CLASS)
    if not cls:
        raise RuntimeError('UDS sky class is unavailable')
    scene = list(actors.get_all_level_actors())
    skies = [a for a in scene if a.get_class() == cls]
    if len(skies) > 1:
        raise RuntimeError('Multiple authored UDS skies require explicit resolution')
    sky = skies[0] if skies else actors.spawn_actor_from_class(cls, u.Vector())
    if not sky:
        raise RuntimeError('Cannot create the hills UDS sky')
    if not skies:
        sky.set_actor_label('Hills Dynamic Sky')
        for key, setting in {'Time Of Day': 900., 'Animate Time Of Day': False,
                             'Time Speed': 0., 'Replicate Time Of Day To Clients': False,
                             'Render Moon': True, 'Render Moon Directional Light': True,
                             'Sun Light Intensity': 5.6, 'Sky Light Intensity': .85}.items():
            sky.set_editor_property(key, setting)
        sky.set_replicates(True)
        fog = next((a for a in scene if a.get_name() == 'ExponentialHeightFog_0'
                    and isinstance(a, u.ExponentialHeightFog)), None)
        if fog:
            sky.set_editor_property('Custom Height Fog Actor', fog)
    retired = []
    for actor in scene:
        expected = LEGACY.get(actor.get_name())
        if expected and isinstance(actor, expected):
            retired.append({'name': actor.get_name(), 'class': actor.get_class().get_path_name()})
            if not actors.destroy_actor(actor):
                raise RuntimeError('Cannot retire fixed study light ' + actor.get_name())
        if actor.get_name() == 'PostProcessVolume_0' and isinstance(actor, u.PostProcessVolume):
            settings = actor.get_editor_property('settings')
            if (settings.get_editor_property('override_auto_exposure_min_brightness')
                and settings.get_editor_property('override_auto_exposure_max_brightness')
                and settings.get_editor_property('auto_exposure_min_brightness') == 1.
                and settings.get_editor_property('auto_exposure_max_brightness') == 1.):
                settings.set_editor_property('override_auto_exposure_min_brightness', False)
                settings.set_editor_property('override_auto_exposure_max_brightness', False)
                actor.set_editor_property('settings', settings)
    return sky, retired
