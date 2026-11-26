"""Publish the restored original face and its correctly fitting collar, then rebind hair."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');script=P/'Tools/ChapelNun/save_final_collar.py'
code=script.read_text(encoding='utf-8').replace("R=P/'SourceAssets/ChapelNun20261115/RefinementR4'","R=P/'SourceAssets/ChapelNun20261115/FaceOriginalRestoreR6'")
code=code.replace('u.FPSModularOutfitComponent.configure_outfit_lods(mesh)',"""if surface_file=='head.json':
 for lod in range(ss.get_lod_count(mesh)):
  build=ss.get_lod_build_settings(mesh,lod)
  for key,value in {'recompute_normals':False,'recompute_tangents':True,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True}.items():build.set_editor_property(key,value)
  ss.set_lod_build_settings(mesh,lod,build)
else:u.FPSModularOutfitComponent.configure_outfit_lods(mesh)""")
original='/Game/Characters/ChapelNun20261115/OriginalMeshyFaceR3/Materials/M_Nun_OriginalMeshy'
for file,name,mats in [('head.json','SK_Nun_OriginalMeshyFace_Final',[original]*3),('trim.json','SK_Nun_CollarCross_Final',None)]:
 state={'SURFACE_FILE':file,'SURFACE_NAME':name}
 if mats:state['SURFACE_MATS']=mats
 exec(compile(code,str(script),'exec'),state)
u=state['u'];head=u.load_asset('/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_OriginalMeshyFace_Final')
for prefix,suffix in [('RefinementR4','_Final_Binding'),('HairReferenceR5','_R5_Binding')]:
 for part in ('Core','Loose'):
  binding=u.load_asset('/Game/Characters/ChapelNun20261115/'+prefix+'/Grooms/Nun_LowBun_'+part+suffix)
  if binding:
   binding.build(u.OnGroomBindingAssetBuildComplete())
   if not u.EditorAssetLibrary.save_loaded_asset(binding,False):raise RuntimeError('Binding save failed')
print('RESTORED_FACE_AND_COLLAR_SAVED',flush=True)
