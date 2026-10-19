from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/Saiga12KClosure')
for script in ('material_graph.py','orientation_candidate.py'):
 exec(compile((T/script).read_text(encoding='utf-8'),str(T/script),'exec'),{'__name__':'__main__'})
