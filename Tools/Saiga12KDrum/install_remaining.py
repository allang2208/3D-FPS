from pathlib import Path
for step in ('install_surface','install_profiles','install_icon'):
    path=Path('D:/FPS3D/FPSGAME/Tools/Saiga12KDrum')/(step+'.py')
    exec(compile(path.read_text(encoding='utf-8-sig'),str(path),'exec'),{'__name__':'__main__'})
