import json
import sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_dragon_breath as a
OUT=ROOT/'SourceAssets/DragonBreath20261013/VisibilityFix'
OUT.mkdir(parents=True,exist_ok=True)
system=u.load_object(None,a.DEST+'/NS_DragonBreath.NS_DragonBreath')
def prop(obj,name):
    try:return str(obj.get_editor_property(name))
    except Exception as e:return str(e)
report={'system_loaded':bool(system),'editor_world':None,'game_world':None,'emitters':{},'runtime':{}}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
for key,world in [('editor_world',editor.get_editor_world()),('game_world',editor.get_game_world())]:
    report[key]=world.get_path_name() if world else None
game=editor.get_game_world()
if game:
    pawn=u.GameplayStatics.get_player_pawn(game,0)
    if pawn:
        fire=pawn.get_component_by_class(u.FPSFireMagicComponent)
        report['runtime']={'pawn':pawn.get_path_name(),'fire':fire.get_path_name() if fire else None}
        if fire:
            report['runtime']['dragon_members']=[x for x in dir(fire) if 'dragon' in x.lower()]
            for name in ['DragonState','DragonSystem','DragonFX']:
                report['runtime'][name]=prop(fire,name)
            try:fx=fire.get_editor_property('DragonFX')
            except Exception:fx=None
            if fx:
                report['runtime']['fx_location']=str(fx.get_world_location())
                report['runtime']['fx_active']=fx.is_active()
if system:
    report['summary']=a.API.call_method('GetSystemSummary',(system,)).export_text()
    try:report['system_topology']=a.API.call_method('GetSystemTopology',(system,)).export_text()
    except Exception as e:report['system_topology']=str(e)
    for name in a.emitters(system):
        r=a.ref(system,name)
        report['emitters'][name]={
            'data':a.API.call_method('GetEmitterData',(r,)).export_text(),
            'renderer':a.API.call_method('GetRendererData',(a.ref(system,name,renderer=0),)).export_text(),
            'topology':a.API.call_method('GetEmitterTopology',(r,)).export_text()}
(OUT/'inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRAGON_VISIBILITY_INSPECT '+json.dumps({k:v for k,v in report.items() if k not in ['summary','system_topology','emitters']}))
print('DRAGON_EMITTERS '+json.dumps(list(report['emitters'])))
