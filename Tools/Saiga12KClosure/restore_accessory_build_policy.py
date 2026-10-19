"""Keep the donor's degenerate-face policy on borrowed common geometry."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018');D='/Game/Weapons/Saiga12K/Closure20261018';C=json.loads((O/'Reports/baseline.json').read_text());SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);rows={}
for key,row in C['assets'].items():
 if key in ('native','ext12'):continue
 source=u.load_asset(row['path']);target=u.load_asset(D+'/Attachments/SM_Saiga12K_'+key);changed=[]
 for li in range(SM.get_lod_count(target)):
  a=SM.get_lod_build_settings(source,li);b=SM.get_lod_build_settings(target,li)
  if a.remove_degenerates!=b.remove_degenerates:b.remove_degenerates=a.remove_degenerates;SM.set_lod_build_settings(target,li,b);changed.append(li)
 if changed:
  if not u.EditorAssetLibrary.save_loaded_asset(target,False):raise RuntimeError('Save failed '+key)
 rows[key]=changed
(O/'Reports/accessory-build-policy.json').write_text(json.dumps(rows,indent=2));print('DONOR_FACE_POLICY_RETAINED')
