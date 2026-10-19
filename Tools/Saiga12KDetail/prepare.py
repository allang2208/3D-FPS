"""Create the new detail revision from the completed surface pipeline."""
from pathlib import Path
import json,shutil
P=Path('D:/FPS3D/FPSGAME');T=P/'Tools/Saiga12KDetail';O=P/'SourceAssets/Saiga12KDetail20261018'
for d in ('Authoring','Textures','Preview','Reports','Receipts','SourceBefore'):(O/d).mkdir(parents=True,exist_ok=True)
for name in ('author.py','bake.py','render.py','mesh_contract.py','install_assets.py','read_baseline.py','check_source.py','check_saved_assets.py','build.ps1','render_mag_icon.py','import_icon.py'):
 s=(P/'Tools/Saiga12KSurface'/name).read_text(encoding='utf-8-sig').replace('SourceAssets/Saiga12KSurface20261018','SourceAssets/Saiga12KDetail20261018').replace('Tools/Saiga12KSurface','Tools/Saiga12KDetail').replace('/SurfaceRebuild20261018','/Detail20261018')
 if name=='author.py':
  s=s.replace("main=join('Saiga12K_SurfaceRebuilt',objects.copy())", "exec((P/'Tools/Saiga12KDetail/details.py').read_text(),globals())\nmain=join('Saiga12K_SurfaceRebuilt',objects.copy())")
  s=s.replace("magazine_ribs(ext,'ExtMagazine',-17.5);ext=join", "magazine_ribs(ext,'ExtMagazine',-17.5);magazine_detail(ext,'ExtMagazine',-17.5);ext=join")
  s=s.replace("export(main,'gun');export(ext,'ext12')", "exec((P/'Tools/Saiga12KDetail/finish_blender.py').read_text(),globals());export(main,'gun');export(ext,'ext12')")
 if name=='read_baseline.py':
  a=s.index('prior=');b=s.index("R={'assets'")
  s=s[:a]+"prior=json.loads((P/'SourceAssets/Saiga12KSurface20261018/Receipts/assets.json').read_text());root='/Game/Weapons/Saiga12K/SurfaceRebuild20261018'\npaths={'native':root+'/SK_Saiga12K_Manny','ext12':root+'/SM_Saiga12K_Ext12'}\npaths.update({k:root+'/Attachments/SM_Saiga12K_'+k for k in prior['bindings'] if k not in ('native','ext12')})\n"+s[b:]
 if name=='install_assets.py':
  s=s.replace("CLEAN={'GrainRoughness'", "FINISH=json.loads((O/'finish.json').read_text())\nCLEAN={'GrainRoughness'")
  s=s.replace("mi=load(path) if E.does_asset_exist(path) else AT.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent", "f=FINISH.get(part,{});color=tuple(f.get('color',color));rough=f.get('roughness',rough)\n mi=load(path) if E.does_asset_exist(path) else AT.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent",1)
  s=s.replace("'20261018; full gun surface reconstruction; native V9 hands and mechanical bones preserved'", "'20261018 detail revision; native V9 hands and mechanical bones preserved'")
 (T/name).write_text(s,encoding='utf-8')
shutil.copy2(P/'SourceAssets/Saiga12KSurface20261018/Authoring/source_components.json',O/'Authoring/source_components.json')
finish={
 'Body':([.027,.028,.030],.38),'ReceiverCover':([.029,.030,.032],.32),
 'Barrel':([.024,.025,.027],.29),'GasTube':([.028,.029,.031],.35),
 'Bolt':([.085,.089,.091],.27),'Fasteners':([.037,.038,.040],.30),
 'Safety':([.029,.030,.032],.37),'MagRelease':([.027,.028,.030],.40),
 'Trigger':([.037,.039,.041],.29),'LaserMark':([.12,.12,.115],.48),
 'Stock':([.014,.014,.0135],.56),'RearGrip':([.013,.013,.0125],.54),
 'Handguard':([.017,.017,.0165],.48),'Magazine':([.018,.018,.0175],.46),
 'ExtMagazine':([.018,.018,.0175],.46),'StockPad':([.008,.008,.008],.72)}
(O/'finish.json').write_text(json.dumps({k:{'color':v[0],'roughness':v[1]} for k,v in finish.items()},indent=2))
(O/'plan.json').write_text(json.dumps({'baseline':'Saiga12KSurface20261018','scope':['Rounded trigger guard and trigger silhouette','Receiver pin seats, selector and charging-handle contact details','Molded handguard, grip, magazine and buttpad details','Restrained part-specific clean finish and identification markings','Rebake structural normals/masks; preserve native arms, sockets and gameplay'],'review':'Offline same-camera comparison and saved-package readback, continuing the requested overall visual review','interactive_editor':False,'gameplay_test':False},indent=2))
print('DETAIL_REVISION_PREPARED')
