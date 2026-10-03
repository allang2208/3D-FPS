"""Read the installed reload sources needed for PKM/SVD recovery authoring."""
import unreal as u,json,os
from pathlib import Path
O=Path(__file__).parent;out={'pid':os.getpid(),'clips':{}}
for weapon in ['SVD','PKM']:
 for family in ['base','vertical','canted','prism','angled']:
  for clip in ['idle','reload','reload_empty']:
   if weapon=='SVD':
    root='/Game/Weapons/SVDDragunov20260922/'+('Complete20260923/Animations/' if family=='base' else 'Accessories20260923/Animations/')
   else:root='/Game/Weapons/PKMLowpoly20260922/'+('Animations/' if family=='base' else 'Accessories14/Animations/'+family+'/')
   path=root+'A_'+weapon+'_'+('' if family=='base' else family+'_')+clip
   a=u.load_asset(path)
   if not a:raise RuntimeError('Missing current animation: '+path)
   out['clips'][weapon+'/'+family+'/'+clip]={'path':path,'source':a.get_editor_property('asset_import_data').get_first_filename(),'duration':a.get_play_length()}
(O/'recovery_inputs.json').write_text(json.dumps(out,indent=2))
print('RIFLE_RECOVERY_INPUTS',os.getpid(),len(out['clips']))
