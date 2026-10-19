from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/Saiga12KClosure')
code=(T/'check_saved_assets.py').read_text()
code=code.replace("D='/Game/Weapons/Saiga12K/Closure20261018'","D='/Game/Weapons/Saiga12K/Detail20261018'")
for name in ('mesh','ext12'):
 code=code.replace("receipt['"+name+"']","receipt['"+name+"'].replace('/Closure20261018/','/Detail20261018/')")
code=code.replace('saved-assets-check.json','active-assets-check.json').replace('saved_ue_gun.json','active_ue_gun.json')
code=code.replace("old=u.load_asset(C['assets'][key]['path'])","old=u.load_asset('/Game/Weapons/Saiga12K/Closure20261018/Attachments/SM_Saiga12K_'+key)")
exec(compile(code,str(T/'check_saved_assets.py'),'exec'),{'__name__':'__main__'})
