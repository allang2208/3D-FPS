"""Store reusable Nurse source actions in the authoring file, without playback."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/attach_source_actions_v02.py').read_text(encoding='utf-8-sig')
src=src.replace('FacelessReceptionist20261007/V02','FacelessSecurity20261008/V01')
src=src.replace('FacelessReceptionist_V02.blend','FacelessSecurity_V01.blend').replace('Receptionist_','Security_').replace('RECEPTIONIST_','SECURITY_')
exec(compile(src,__file__,'exec'))
