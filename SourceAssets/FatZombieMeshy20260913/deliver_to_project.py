"""Place newly authored assets in FPSGAME without overwriting existing folders."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).parent
contract=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8'))
base='/Game/Monsters/FatZombieMeshy'
skel=base+'/SK_FatZombie_Meshy_Skeleton.SK_FatZombie_Meshy_Skeleton'
delivery={'mesh':base+'/SK_FatZombie_Meshy.SK_FatZombie_Meshy','skeleton':skel,
          'content_folder':base,'stage_project':str(ROOT/'UEAuthoring/FatZombieAuthoring.uproject'),
          'clips':{role:{'asset':base+'/Animations/A_FatZombie_'+role+'.A_FatZombie_'+role,
                         'skeleton':skel,**clip} for role,clip in contract['clips'].items()},
          'import_record':'native_retarget_final.log: final animation save operations completed; manifest written by delivery script'}
src=ROOT/'UEAuthoring/Content/Monsters/FatZombieMeshy'
dest=ROOT.parents[1]/'Content/Monsters/FatZombieMeshy'
shutil.copytree(src,dest)
delivery['delivered_directory']=str(dest)
delivery['state']='Copied to FPSGAME Content; visual/runtime testing left to user.'
(ROOT/'ue_delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print('FAT_ZOMBIE_DELIVERED '+str(dest))
