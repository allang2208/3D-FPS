import unreal as u,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04/Records')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
own=[p for p in dirty if p.get_path_name().startswith('/Game/Monsters/HangingBellM09/V04')]
print('M09_PENDING_PACKAGES '+json.dumps([p.get_path_name() for p in own]))
if own:
 if not u.EditorLoadingAndSavingUtils.save_packages(own,False):raise RuntimeError('Pending M09 packages not saved')
 print('M09_PENDING_SAVED')
print('UNRELATED_DIRTY_COUNT '+str(len(dirty)-len(own)))
