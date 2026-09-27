"""Rebuild and save only the three persistent grip material packages.

Uses the package-save API, which is also available during material editing in
Play. Does not save a map, change equipment, stop Play, or start a test.
"""
import unreal as u,json,sys,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];D='/Game/Weapons/SharedSwordGrips20260927'
sys.path.insert(0,str(P))
from grip_materials import build_material
before=P/'BeforeSubstrateRepair';before.mkdir(exist_ok=True)
receipt=[];packages=[]
for key in ['Leather','Steel','Textile']:
    name='M_SharedGrip_'+key;path=D+'/Materials/'+name
    file=ROOT/'Content/Weapons/SharedSwordGrips20260927/Materials'/(name+'.uasset')
    if file.exists() and not (before/file.name).exists():shutil.copy2(file,before/file.name)
    material=u.load_asset(path)
    if material is None:raise RuntimeError('Missing grip material '+path)
    maps={suffix:u.load_asset(D+'/Textures/T_SharedGrip_'+key+'_'+suffix) for suffix in ['BaseColor','Normal','Roughness']}
    if any(t is None for t in maps.values()):raise RuntimeError('Missing authored grip PBR textures '+key)
    receipt.append(build_material(material,key,maps));packages.append(material.get_outer())
if not u.EditorLoadingAndSavingUtils.save_packages(packages,False):
    raise RuntimeError('The three grip material packages were not saved; preserve editor state.')
for row in receipt:row['saved']=True
(P/'material_repair_receipt.json').write_text(json.dumps({'materials':receipt,'save':'only the three grip material packages','game_test':'not run'},ensure_ascii=False,indent=2),encoding='utf-8')
print('GRIP_SUBSTRATE_PBR_SAVED '+json.dumps(receipt,ensure_ascii=False))
