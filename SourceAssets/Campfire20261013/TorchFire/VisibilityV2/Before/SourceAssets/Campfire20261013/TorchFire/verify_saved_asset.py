"""Load saved packages only; no actors, world tick, preview or gameplay."""
import unreal as u
import sys,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,emitters
HELP=getattr(u,'CampfireAssetTools',getattr(u,'RainAssetEditor',None))
base='/Game/Building/Campfire20261013/TorchFire'
path=base+'/NS_CampfireTorchFire'
s=u.load_asset(path);assert s
assert HELP.compile_rain(s),'Saved Niagara is not valid'
names=emitters(s);assert set(names)=={'Fire','Smoke','Sparks'}
system=json.loads(API.call_method('GetSystemData',(s,)).get_editor_property('property_values'))
assert system['bFixedBounds'] is True
report={'asset':path,'system_fixed_bounds':system['FixedBounds'],'system_fixed_bounds_enabled':True,'emitters':{},'materials':[],'loaded_from_disk':True,'niagara_valid':True,'runtime_tested':False,'visual_preview_performed':False,'gpu_shader_or_render_validation':False}
for name in names:
    settings=json.loads(API.call_method('GetEmitterData',(ref(s,name),)).get_editor_property('property_values'))
    assert settings['bLocalSpace'] and settings['CalculateBoundsMode']=='Fixed'
    top=API.call_method('GetEmitterTopology',(ref(s,name),))
    classes=[str(x) for x in top.get_editor_property('renderer_classes')]
    assert len(classes)==1 and 'SpriteRenderer' in classes[0]
    renderer=json.loads(API.call_method('GetRendererData',(ref(s,name,renderer=0),)).get_editor_property('property_values'))
    assignments={}
    for stage in ('ParticleSpawnScript','ParticleUpdateScript'):
        mod=u.EditorAssetLibrary.get_metadata_tag(s,'Fireball.Assignments.'+name+'.'+stage)
        if mod:
            keys=['Particles.SpriteSize'] if stage=='ParticleUpdateScript' else ['Particles.Position','Particles.Lifetime','Particles.SpriteSize','Particles.Velocity']
            assignments[stage]={k:HELP.read_input(s,name,stage,mod,k) for k in keys}
    report['emitters'][name]={'local_space':settings['bLocalSpace'],'bounds':settings['FixedBounds'],'renderers':classes,'material':renderer['Material'],'sub_image_size':renderer.get('SubImageSize'),'rate':HELP.read_input(s,name,'EmitterUpdateScript','SpawnRate','SpawnRate'),'assignments':assignments}
for name,fade in [('M_CampfireTorchFire',4.),('M_CampfireTorchSmoke',8.)]:
    mat=u.load_asset(base+'/'+name);assert mat
    nodes=u.MaterialEditingLibrary.get_material_expressions(mat)
    fades=[n for n in nodes if isinstance(n,u.MaterialExpressionDepthFade)]
    assert len(fades)==1 and abs(fades[0].get_editor_property('fade_distance_default')-fade)<.01
    report['materials'].append({'asset':mat.get_path_name(),'contact_fade_cm':fade})
reg=u.AssetRegistryHelpers.get_asset_registry();reg.scan_paths_synchronous([base,'/Game/TorchFire'],True)
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
todo=[path];seen=set();deps={}
while todo:
    p=todo.pop()
    if p in seen:continue
    seen.add(p);ds=[str(x) for x in reg.get_dependencies(p,opts)];deps[p]=ds
    for v in ds:
        if v.startswith('/Game/') and v not in seen:todo.append(v)
assert all(u.EditorAssetLibrary.does_asset_exist(p) for p in seen)
assert not any('CampfireAssetTools' in x for ds in deps.values() for x in ds)
report['all_game_dependencies_exist']=True;report['dependencies']=deps
(OUT/'final-asset-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CAMPFIRE_SAVED_READBACK_OK',len(seen))
