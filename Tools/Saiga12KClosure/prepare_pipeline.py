from pathlib import Path
import shutil,json
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';T=P/'Tools/Saiga12KClosure'
for name in ('bake.py','check_source.py','install_assets.py','read_baseline.py','check_saved_assets.py','mesh_contract.py'):
 s=(P/'Tools/Saiga12KDetail'/name).read_text(encoding='utf-8-sig').replace('SourceAssets/Saiga12KDetail20261018','SourceAssets/Saiga12KClosure20261018').replace('Tools/Saiga12KDetail','Tools/Saiga12KClosure').replace('/Detail20261018','/Closure20261018').replace('Authoring/Saiga12K_SurfaceRebuilt.blend','Authoring/Saiga12K_ClosedShell.blend')
 if name=='read_baseline.py':s=s.replace('Saiga12KSurface20261018','Saiga12KDetail20261018').replace('/SurfaceRebuild20261018','/Detail20261018')
 if name=='install_assets.py':
  s=s.replace("sk.regenerate_lod(mesh,sk.get_lod_count(native),True,False)","settings=sk.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.remove_degenerates=False;sk.set_lod_build_settings(mesh,0,settings)\n sk.regenerate_lod(mesh,sk.get_lod_count(native),True,False)")
  s=s.replace("if not r['complete']", "if not r['complete']")
  # Static ext magazine must retain the authored normals and fine shell faces too.
  s=s.replace("SM.set_lods(mesh,opts);save(mesh)","SM.set_lods(mesh,opts)\n for li in range(SM.get_lod_count(mesh)):\n  bs=SM.get_lod_build_settings(mesh,li);bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True;bs.remove_degenerates=False;SM.set_lod_build_settings(mesh,li,bs)\n save(mesh)")
 (T/name).write_text(s,encoding='utf-8')
shutil.copy2(P/'SourceAssets/Saiga12KDetail20261018/finish.json',O/'finish.json')
print('CLOSURE_PIPELINE_PREPARED')
