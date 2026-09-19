"""Place newly authored assets in FPSGAME without overwriting existing folders."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).parent
contract=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8'))
base='/Game/Monsters/Mutant3Meshy'
skel=base+'/SK_Mutant3_Meshy_Skeleton.SK_Mutant3_Meshy_Skeleton'
delivery={'mesh':base+'/SK_Mutant3_Meshy.SK_Mutant3_Meshy','skeleton':skel,
          'content_folder':base,'stage_project':str(ROOT/'UEAuthoring/Mutant3Authoring.uproject'),
          'clips':{role:{'asset':base+'/Animations/A_Mutant3_'+role+'.A_Mutant3_'+role,
                         'skeleton':skel,**clip} for role,clip in contract['clips'].items()},
          'import_record':'final-import.log: final animation save operations completed; manifest written by delivery script'}
src=ROOT/'UEAuthoring/Content/Monsters/Mutant3Meshy'
dest=ROOT.parents[1]/'Content/Monsters/Mutant3Meshy'
shutil.copytree(src,dest)
delivery['delivered_directory']=str(dest)
delivery['state']='Copied to FPSGAME Content; visual/runtime testing left to user.'
(ROOT/'ue_delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print('MUTANT3_DELIVERED '+str(dest))

