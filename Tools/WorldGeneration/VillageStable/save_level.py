import json
import os
import sys
from pathlib import Path
import unreal as ue

sys.path.insert(0,str(Path(__file__).resolve().parent))
from install_stable import install_stable
from stable_perimeter import install_stable_perimeter
from stable_ground_detail import install_ground_detail

level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
run=Path(os.environ['STABLE_RUN'])
phase=os.environ.get('STABLE_PHASE')
world=ue.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not open '+level)
actors=ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
if phase=='GroundDetail':
    from stable_ground_materials import author
    author()
    report=install_ground_detail(actors)
elif phase=='Riding':
    from stable_horses import install_horses
    report=install_horses(actors,upgrade_placed=True)
elif phase=='Horses':
    from stable_horses import install_horses
    report=install_horses(actors)
    report['horse_assets']=json.loads((run/'horse-assets.json').read_text(encoding='utf-8'))
elif phase=='Perimeter':
    report=install_stable_perimeter(actors)
else:
    report=install_stable(actors)
if not ue.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save '+level)
report.update(level=level,previous_package=os.environ['STABLE_PREVIOUS'],runtime_tested=False)
(run/'level-saved.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
ue.log('STABLE_LEVEL_SAVED '+level)
