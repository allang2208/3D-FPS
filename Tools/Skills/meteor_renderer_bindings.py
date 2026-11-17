"""Bindings owned by the meteor impact, independent of the NE_Core template."""
import json
import unreal as u
from build_fireball_assets import API, ref, emitters, setdata

def bind_impact_attributes(system, emitter_names=None):
    for en in (emitters(system) if emitter_names is None else emitter_names):
        r=ref(system,en,renderer=0)
        values=json.loads(API.call_method('GetRendererData',(r,)).get_editor_property('property_values'))
        corrected={}
        for key,attribute in [('SpriteAlignmentBinding','SpriteAlignment'),('UVScaleBinding','SpriteUVScale')]:
            binding=values[key]
            binding['rootName']=attribute
            binding['paramMapVariable']['name']='Particles.'+attribute
            binding['dataSetName']=attribute
            binding['cachedDisplayName']='Particles.'+attribute
            binding['bindingSourceMode']='ImplicitFromSource'
            corrected[key]=binding
        setdata('SetRendererData',u.NiagaraExt_RendererData,r,corrected)

def binding_receipt(system):
    rows={}
    for en in emitters(system):
        values=json.loads(API.call_method('GetRendererData',(ref(system,en,renderer=0),)).get_editor_property('property_values'))
        rows[en]={key:{'attribute':values[key]['paramMapVariable']['name'],
            'exists_on_source':values[key]['bBindingExistsOnSource']} for key in ['SpriteAlignmentBinding','UVScaleBinding','DynamicMaterialBinding']}
    return rows
