"""Deferred import of Boss-owned PBR only. Execute through the project batch bridge."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/BossHall20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Different project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running game')
owned_incomplete=set(globals().get('OWNED_INCOMPLETE_MATERIALS',[]))
if any(p.get_name().startswith((BASE+'/Materials/',BASE+'/Textures/')) and p.get_name() not in owned_incomplete for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved Boss material edits')
specs=json.loads((ROOT/'Authored/polish-materials.json').read_text())['materials']
receipt={'materials':{},'textures':{},'scope':'Boss-owned PBR; no map or gameplay changes','tests_run':False}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

for key,spec in specs.items():
    if globals().get('MATERIAL_KEYS') and key not in MATERIAL_KEYS:continue
    imported={}
    for channel,filename in spec.get('maps',{}).items():
        name='T_'+key+'_'+channel
        task=u.AssetImportTask();task.filename=filename;task.destination_path=BASE+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(BASE+'/Textures/'+name)
        if not tex:raise RuntimeError('Texture import failed '+name)
        tex.set_editor_property('srgb',channel in ('BaseColor','RustColor'))
        if channel.endswith('Normal'):
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property('flip_green_channel',True)
        elif channel not in ('BaseColor','RustColor'):tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(tex);imported[channel]=tex;receipt['textures'][name]=tex.get_path_name()
    name='M_'+key;mat=u.load_asset(BASE+'/Materials/'+name)
    if mat:L.delete_all_material_expressions(mat)
    else:mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    def node(cls):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+cls))
    def link(a,pin,b,input_name):
        if not L.connect_material_expressions(a,pin,b,input_name):raise RuntimeError('Material wiring failed '+input_name)
    def out(a,prop,pin=''):
        if not L.connect_material_property(a,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output failed '+prop)
    def constant(value):
        if isinstance(value,(float,int)):
            n=node('Constant');n.r=value
        else:n=node('Constant3Vector');n.constant=u.LinearColor(*value,1)
        return n
    channels={}
    for channel,tex in imported.items():
        n=node('TextureSample');n.texture=tex
        n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel in ('BaseColor','RustColor') else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel.endswith('Normal') else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        channels[channel]=n
    base=channels['BaseColor'];metal=channels.get('Metallic') or constant(spec.get('metallic',0));metal_pin='R' if 'Metallic' in channels else ''
    if spec.get('vertex_wear'):
        vc=node('VertexColor');dirt=node('Multiply');link(base,'RGB',dirt,'A');link(constant([.24,.21,.17]),'',dirt,'B')
        mix=node('LinearInterpolate');link(base,'RGB',mix,'A');link(dirt,'',mix,'B');link(vc,'R',mix,'Alpha')
        edge=node('LinearInterpolate');link(mix,'',edge,'A');link(constant([.22,.24,.23]),'',edge,'B');link(vc,'G',edge,'Alpha');out(edge,'BASE_COLOR');base=edge
        expose=node('Max');link(metal,metal_pin,expose,'A');link(vc,'G',expose,'B');out(expose,'METALLIC')
    else:out(base,'BASE_COLOR','RGB');out(metal,'METALLIC',metal_pin)
    if 'Roughness' in channels:out(channels['Roughness'],'ROUGHNESS','R')
    else:out(constant(spec.get('roughness',.65)),'ROUGHNESS')
    if spec.get('vertex_wetness'):
        vc=node('VertexColor');dark=node('Multiply');link(base,'',dark,'A');link(constant([.48,.51,.46]),'',dark,'B')
        wet=node('LinearInterpolate');link(base,'',wet,'A');link(dark,'',wet,'B');link(vc,'B',wet,'Alpha');out(wet,'BASE_COLOR')
        rough=node('LinearInterpolate');link(channels['Roughness'],'R',rough,'A');link(constant(.22),'',rough,'B');link(vc,'B',rough,'Alpha');out(rough,'ROUGHNESS')
    if 'Normal' in channels:
        multiply=node('Multiply');link(channels['Normal'],'RGB',multiply,'A');link(constant([spec.get('normal_strength',.65)]*2+[1]),'',multiply,'B')
        normal=node('Normalize');link(multiply,'',normal,'VectorInput');out(normal,'NORMAL')
    if spec.get('vertex_pipe_weather'):
        vc=node('VertexColor');mask=node('Multiply');link(vc,'G',mask,'A');link(channels['Weather'],'R',mask,'B')
        scale=node('Multiply');link(mask,'',scale,'A');link(constant(1.8),'',scale,'B')
        factor=node('Saturate');link(scale,'',factor,'')
        def weather(a,a_pin,b,b_pin=''):
            n=node('LinearInterpolate');link(a,a_pin,n,'A');link(b,b_pin,n,'B');link(factor,'',n,'Alpha');return n
        rust_base=weather(channels['BaseColor'],'RGB',channels['RustColor'],'RGB')
        dirty=node('Multiply');link(rust_base,'',dirty,'A');link(constant([.26,.23,.19]),'',dirty,'B')
        finish=node('LinearInterpolate');link(rust_base,'',finish,'A');link(dirty,'',finish,'B');link(vc,'R',finish,'Alpha');out(finish,'BASE_COLOR')
        out(weather(channels['Roughness'],'R',constant(.91)),'ROUGHNESS')
        out(weather(channels['Metallic'],'R',constant(0)),'METALLIC')
        rust_scale=node('Multiply');link(channels['RustNormal'],'RGB',rust_scale,'A');link(constant([.65,.65,1]),'',rust_scale,'B')
        rust_normal=node('Normalize');link(rust_scale,'',rust_normal,'VectorInput')
        blended=weather(normal,'',rust_normal)
        final_normal=node('Normalize');link(blended,'',final_normal,'VectorInput');out(final_normal,'NORMAL')
    L.layout_material_expressions(mat);L.recompile_material(mat);save(mat);receipt['materials'][key]=mat.get_path_name()
(ROOT/'Receipts/polish-materials-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BOSS_MATERIALS_IMPORTED',len(receipt['materials']))
