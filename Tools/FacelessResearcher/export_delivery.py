"""Export full body, independent garments and morph-enabled runtime assembly."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/export_v04.py').read_text(encoding='utf-8')
src=src.replace('FacelessReceptionist20261007/V04','FacelessResearcher20261009/V01')
src=src.replace('FacelessReceptionist','FacelessResearcher').replace('Receptionist_','Researcher_').replace('V04','V01')
exec(compile(src,'researcher_export_v01','exec'))
