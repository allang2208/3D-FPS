from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/Tools/StaffLivingShoulder')
for name in ['read_current_assets.py','install_repaired_assets.py']:
 exec(compile((root/name).read_text(encoding='utf-8-sig'),str(root/name),'exec'),{'__name__':'__main__'})
