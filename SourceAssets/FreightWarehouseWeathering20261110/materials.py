"""Subject-only weathered surfaces using the imported Underground Tunnel scans."""
from pathlib import Path
import json,types
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightWarehouseWeathering20261110'
REVISION='freight_warehouse_weathering_20261110'
helper=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
helper=helper.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','')
helper=helper.replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}")
helper=helper.replace('FacilitySurface.Owner','FreightWeathering.Owner')
scope=dict(ROOT=ROOT,BASE=BASE,REVISION=REVISION,canonical=lambda p:p.split('.')[0])
exec(compile(helper,'freight_weathering_material_helpers','exec'),scope)
H=types.SimpleNamespace(**scope)
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary

def tex(m,key,path,normal=False,color=False):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Imported surface texture missing '+path)
    sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if obj.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    return H.node(m,'TextureObjectParameter',parameter_name=key,texture=obj,sampler_type=sampler)

def build():
    # The user rejected both replacement surface passes. Keep the original
    # concrete bindings when rebuilding; environmental dressing remains active.
    original='/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete.MI_WallConcrete'
    if not u.load_asset(original):raise RuntimeError('Original concrete material unavailable')
    results=dict(Floor=original,Wall=original)
    # Keep the kit's authored rusty runoff texture and original decal graph.
    rust=H.own('Materials/MI_RustRunoff',u.MaterialInstanceConstant,'/Game/UndergroundTunnel/Materials/MI_Decal_RustStain01a')
    results['Rust']=H.save(rust).get_path_name()
    m=H.own('Materials/M_ContactGrime');L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    uv=H.node(m,'TextureCoordinate',coordinate_index=0)
    pins={'UV':uv,'Noise':tex(m,'Noise','/Game/UndergroundTunnel/Textures/Effects/T_Noise01a'),
          'Opacity':H.scalar(m,'Opacity',.28),'Stretch':H.scalar(m,'Stretch',1.)}
    code='''float2 q=UV*2-1;
float noise=Texture2DSample(Noise,NoiseSampler,UV*float2(2.7,3.8)+float2(.12,.37)).r;
float broad=Texture2DSample(Noise,NoiseSampler,UV*.9+float2(.52,.17)).r;
float edge=max(abs(q.x),abs(q.y));
float fade=1.-smoothstep(.55,.98,edge);
float patch=smoothstep(.27,.72,noise*.65+broad*.35);
return saturate(Opacity*fade*patch);'''
    alpha=H.custom(m,code,pins,1)
    H.output(alpha,'OPACITY')
    H.output(H.node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.1,.075,.045,1)),'BASE_COLOR')
    H.output(H.scalar(m,'Roughness',.9),'ROUGHNESS')
    H.save(m)
    for name,tint,rough,opacity in [('Dust',(.19,.16,.11),.95,.3),('Oil',(.025,.028,.024),.35,.47),('Scuff',(.09,.08,.065),.72,.23),('Damp',(.08,.09,.075),.48,.26)]:
        results[name]=H.instance(name,m,dict(Roughness=rough,Opacity=opacity),{'Tint':tint}).get_path_name()
    results['saved_assets']=list(dict.fromkeys(H.SAVED))
    return results
