"""Restore only Blizzard's copied cloud bindings; retain the existing cloud artwork."""
import json
import unreal as u
from build_fireball_assets import API, ref, emitters, setdata, assignments
from build_fireball_flames import VEC2, VEC3

E = u.EditorAssetLibrary
SYSTEM = '/Game/Skills/StormClouds/RollingV1/NS_BlizzardStormCloud'
LAYERS = ('DenseDarkBase', 'RollingCloudBody', 'SlateCloudCrown', 'ElectricCloudRim', 'SoftCloudFringe')
TAG = 'Blizzard.CloudVisibility20261115'


def apply(system):
    missing = set(LAYERS)-set(emitters(system))
    if missing:
        raise RuntimeError('Missing Blizzard cloud layers: '+str(sorted(missing)))
    for name in LAYERS:
        renderer = ref(system, name, renderer=0)
        values = json.loads(API.call_method('GetRendererData', (renderer,)).get_editor_property('property_values'))
        bindings = {}
        for key, attribute in [('SpriteAlignmentBinding', 'SpriteAlignment'), ('UVScaleBinding', 'SpriteUVScale')]:
            binding = values[key]
            binding.update(rootName=attribute, dataSetName=attribute,
                           cachedDisplayName='Particles.'+attribute, bindingSourceMode='ImplicitFromSource')
            binding['paramMapVariable']['name'] = 'Particles.'+attribute
            bindings[key] = binding
        setdata('SetRendererData', u.NiagaraExt_RendererData, renderer, bindings)
        # Discard the copied explosion emitter's +/-100 cm box. The actor keeps
        # its existing storm-sized system bounds; these CPU sprites may exceed
        # the explosion template's bounds while rolling over the target area.
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
                {'CalculateBoundsMode': 'Dynamic', 'InterpolatedSpawnMode': 'NoInterpolation'})
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            tag = 'Fireball.Assignments.'+name+'.'+stage
            owned = TAG+'.'+name+'.'+stage
            module = E.get_metadata_tag(system, owned)
            topology = API.call_method('GetEmitterTopology', (ref(system, name),))
            field = 'particle_spawn_script' if stage == 'ParticleSpawnScript' else 'particle_update_script'
            available = {str(m.get_editor_property('module_name')) for m in topology.get_editor_property(field).get_editor_property('modules')}
            if module and module in available:
                E.set_metadata_tag(system, tag, module)
            else:
                E.remove_metadata_tag(system, tag)
            assignments(system, name, stage, {'Particles.SpriteAlignment': (VEC3, 'User.SurfaceNormal'),
                                              'Particles.SpriteUVScale': (VEC2, 'float2(1,1)')})
            E.set_metadata_tag(system, owned, E.get_metadata_tag(system, tag))
    E.set_metadata_tag(system, TAG, '1')
    return {'layers': list(LAYERS), 'alignment': 'Particles.SpriteAlignment',
            'uv_scale': 'Particles.SpriteUVScale=(1,1)', 'emitter_bounds': 'Dynamic',
            'cloud_artwork_and_lifetimes_preserved': True}
