from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist')
s=(p/'import_assets.py').read_text(encoding='utf-8-sig').replace("FacelessReceptionist20261007')","FacelessReceptionist20261007/V02')").replace('V01','V02')
s=s.replace("'Saved candidate; not gameplay or visually tested'","'V02: anatomical skin repair and continuous outfit. Blender reference rendered; no gameplay test.'")
s=s.replace("str(t)!='NurseZombie'","str(t) not in ['NurseZombie','FacelessReceptionist']")
s=s.replace("report.update(stage='saved'","report.update(version='V02',stage='saved'")
(p/'import_assets_v02.py').write_text(s,encoding='utf-8')
