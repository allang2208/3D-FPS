"""Read-only diagnosis of the assets actually bound to grass footstep feedback."""
import json
import re
from pathlib import Path
import unreal as u

OUT=Path(u.Paths.project_dir())/'Saved/FootstepBlocks20260926'
OUT.mkdir(parents=True,exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
root='/Game/WorldGeneration/GrassDeform/'
result={}
cfg=u.load_asset(root+'DA_GrassFootstepFeedback')
result['config']={name:str(cfg.get_editor_property(name)) for name in
    ['puff_system','decal_material','surfaces','decal_pool_size','puff_max_active']}
system=u.load_asset(root+'NS_GrassFootstepPuff')
api=u.get_default_object(u.NiagaraToolset_System)
summary=api.call_method('GetSystemSummary',(system,))
result['system']=summary.export_text()
result['emitters']=[]
materials={root+'M_GrassTrampleDecal'}
for emitter in summary.get_editor_property('emitters'):
    name=str(emitter.get_editor_property('emitter_name'))
    ref=u.NiagaraExt_StackItemReference()
    ref.set_editor_property('system',system)
    ref.set_editor_property('emitter_name',name)
    topo=api.call_method('GetEmitterTopology',(ref,))
    item={'name':name,'topology':topo.export_text()}
    ref.set_editor_property('renderer_index',0)
    data=api.call_method('GetRendererData',(ref,))
    raw=str(data.get_editor_property('property_values'))
    item['renderer']=json.loads(raw)
    result['emitters'].append(item)
    print('FOOTSTEP_RENDERER',name,raw,flush=True)
    materials.update(re.findall(r'/Game/[^"\s]+',raw))
    (OUT/'diagnosis-partial.json').write_text(json.dumps(result,indent=2),encoding='utf8')
result['materials']={}
for path in sorted(materials):
    m=u.load_asset(path)
    if not isinstance(m,u.MaterialInterface):continue
    if isinstance(m,u.MaterialInstance):m=m.get_base_material()
    result['materials'][path]={
        'base':m.get_path_name(),
        'domain':str(m.get_editor_property('material_domain')),
        'blend':str(m.get_editor_property('blend_mode')),
        'niagara_sprites':bool(m.get_editor_property('used_with_niagara_sprites')),
        'outputs':{p:str(L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+p)))
            for p in ['BASE_COLOR','EMISSIVE_COLOR','OPACITY','OPACITY_MASK','FRONT_MATERIAL']},
        'expressions':[{'class':n.get_class().get_name(),'name':n.get_name(),
            'inputs':[str(pin) for pin in L.get_material_expression_input_names(n)]}
            for n in L.get_material_expressions(m)]}
(OUT/'diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('FOOTSTEP_BLOCKS_DIAGNOSIS_SAVED',OUT,flush=True)
