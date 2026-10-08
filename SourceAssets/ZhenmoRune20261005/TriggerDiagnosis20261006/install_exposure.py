from pathlib import Path
import importlib.util,shutil
import unreal as u
ROOT=Path(__file__).resolve().parent.parent
backup=Path(__file__).resolve().parent/'Before'/'Exposure'
backup.mkdir(parents=True,exist_ok=True)
for name,folder in [('M_ZhenmoSoftGround','SoftGroundV3'),('M_ZhenmoGoldMote','Particles')]:
    source=Path(u.Paths.project_dir())/'Content/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005'/folder/(name+'.uasset')
    if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
for file,function in ((ROOT/'SoftGroundV3/author_soft_ground.py','build'),(ROOT/'RisingMotes/author_rising_motes.py','material')):
    spec=importlib.util.spec_from_file_location('zhenmo_'+file.stem,str(file))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    getattr(m,function)()
spec=importlib.util.spec_from_file_location('zhenmo_rebuild',str(ROOT/'RisingMotes/rebuild_runtime.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.rebuild()
