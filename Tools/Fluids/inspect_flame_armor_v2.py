"""Read the reported missing flame armor; never starts or changes PIE."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/FlameArmor20261016/VisibilityFix'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,ref

def safe(fn):
    try:return fn()
    except Exception as exc:return 'ERROR: '+str(exc)

report={'systems':{},'players':[],'components':[],'dirty':[]}
report['dirty']=[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
for leaf in ('Body','Weapon','Arrow'):
    path='/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmor'+leaf+'V2'
    s=u.load_asset(path)
    row={'loaded':bool(s)};report['systems'][leaf]=row
    if not s:continue
    row['summary']=safe(lambda:API.call_method('GetSystemSummary',(s,)).export_text())
    row['system']=safe(lambda:json.loads(API.call_method('GetSystemData',(s,)).get_editor_property('property_values')))
    row['emitters']=[]
    for e in API.call_method('GetSystemSummary',(s,)).get_editor_property('emitters'):
        name=str(e.get_editor_property('emitter_name'))
        row['emitters'].append({'name':name,'enabled':e.get_editor_property('enabled'),
            'data':safe(lambda:json.loads(API.call_method('GetEmitterData',(ref(s,name),)).get_editor_property('property_values'))),
            'renderer':safe(lambda:json.loads(API.call_method('GetRendererData',(ref(s,name,renderer=0),)).get_editor_property('property_values'))),
            'rate':safe(lambda:u.RainAssetEditor.read_input(s,name,'EmitterUpdateScript','SpawnRate','SpawnRate')),
            'state':safe(lambda:u.RainAssetEditor.read_input(s,name,'EmitterUpdateScript','EmitterState','Life Cycle Mode')),
            'topology':safe(lambda:API.call_method('GetEmitterTopology',(ref(s,name),)).export_text())})
worlds=u.EditorLevelLibrary.get_pie_worlds(False)
for world in worlds:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        fire=pawn.get_component_by_class(u.FPSFireMagicComponent)
        report['players'].append({'pawn':pawn.get_path_name(),'world':world.get_path_name(),
            'status':safe(lambda:fire.status_text('flameArmor')),
            'aura_asset':safe(lambda:str(fire.get_editor_property('aura_system'))),
            'weapon_asset':safe(lambda:str(fire.get_editor_property('weapon_system'))),
            'aura_fx':safe(lambda:str(fire.get_editor_property('aura_fx')))})
        for fx in pawn.get_components_by_class(u.NiagaraComponent):
            asset=fx.get_editor_property('asset')
            if not asset or not any(x in asset.get_path_name() for x in ('FlameArmor','NS_Armor')):continue
            report['components'].append({'name':fx.get_path_name(),'asset':asset.get_path_name(),
              'active':fx.is_active(),'visible':fx.is_visible(),'hidden':fx.get_editor_property('hidden_in_game'),
              'position':str(fx.get_world_location()),'scale':str(fx.get_world_scale()),
              'params':{x:safe(lambda x=x:fx.get_variable_float('User.'+x)) for x in ('Fade','Detail','Coverage','UpperVisibility','WeaponSize')},
              'debug_methods':[x for x in dir(fx) if 'particle' in x.lower() or 'debug' in x.lower()]})
(OUT/'initial-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('FLAME_ARMOR_INSPECT',json.dumps({'systems':list(report['systems']),'players':report['players'],'components':report['components']},ensure_ascii=False,default=str))
