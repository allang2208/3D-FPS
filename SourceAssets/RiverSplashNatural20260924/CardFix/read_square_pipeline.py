"""Bounded read of the reported square's active asset and available pixel-read API."""
import json
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_dir())/'SourceAssets/RiverSplashNatural20260924/CardFix'
api = u.get_default_object(u.NiagaraToolset_System)
s = u.load_asset('/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash')
m = u.load_asset('/Game/Fluids/RiverPilot20260923/M_RiverCrown')
t = u.load_asset('/Game/Fluids/RiverSplashNatural20260924/T_RiverSplashPacked')
result = {'emitters': [], 'material': {}, 'texture': {}, 'api': {}}
def ref(e, renderer=-1):
    r=u.NiagaraExt_StackItemReference()
    r.set_editor_property('system',s); r.set_editor_property('emitter_name',e)
    r.set_editor_property('renderer_index',renderer)
    return r
for emitter in api.call_method('GetSystemSummary',(s,)).get_editor_property('emitters'):
    name=str(emitter.get_editor_property('emitter_name'))
    topology=api.call_method('GetEmitterTopology',(ref(name),))
    result['emitters'].append({'name':name,'topology':topology.export_text(),
        'renderer0':json.loads(api.call_method('GetRendererData',(ref(name,0),)).get_editor_property('property_values'))})
for key in ('allow_front_layer_translucency','blend_mode','translucency_lighting_mode','refraction_method'):
    result['material'][key]=str(m.get_editor_property(key))
for key in ('compression_settings','compression_no_alpha','adjust_min_alpha','adjust_max_alpha','lod_bias','never_stream'):
    result['texture'][key]=str(t.get_editor_property(key))
result['material']['custom']=[n.get_editor_property('code') for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
for cls, names in [(u.RenderingLibrary, ['create_render_target2d','draw_material_to_render_target','read_render_target_raw','read_render_target_raw_pixel','export_render_target']),
                   (u.MaterialEditingLibrary, ['get_material_statistics','recompile_material'])]:
    for name in names:
        f=getattr(cls,name,None)
        if f: result['api'][name]=f.__doc__
result['object_api']=[x for x in dir(u) if 'object' in x.lower() and ('iter' in x.lower() or 'class' in x.lower() or 'new_' in x.lower())]
(out/'pipeline-before-r2.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('SQUARE_PIPELINE '+json.dumps({'emitters':[e['name'] for e in result['emitters']], 'material':{k:v for k,v in result['material'].items() if k!='custom'}, 'texture':result['texture'],'api':result['api'],'object_api':result['object_api']}))
