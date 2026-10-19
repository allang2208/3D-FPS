from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/Saiga12KClosure')
for name in ('refine_accessories.py','finish_coating.py','check_saved_assets.py'):
 exec(compile((T/name).read_text(),str(T/name),'exec'),{'__name__':'__main__'})
