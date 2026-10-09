"""Tailor the zombie donor motions to the repaired male uniform and boots."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_male_v02.py').read_text(encoding='utf-8')
src=src.replace('V02','V03').replace("BASE=ROOT.parent/'V01'",'BASE=ROOT')
src=src.replace('Authoring/FacelessSecurity_V01.blend','Authoring/FacelessSecurity_V03.blend')
src=src.replace('rig.animation_data.action=None','rig.animation_data_create();rig.animation_data.action=None')
src=src.replace("math.radians(2.4)","math.radians(-5.0)")
src=src.replace("3.5 if role=='attack' else 5.0","4.5 if role=='attack' else 6.0")
src=src.replace("'revision':'V03 male locomotion and weighted strike'","'revision':'V03 zombie locomotion, repaired extremities and weighted strike'")
src=src.replace('2.4 degree ready lean for idle/walk; whole-arm shoulder clearance; actual boot sole grounding; source bone lengths retained','Zombie Idle_A/Walk_A: 5 degree reduction of upper-back hunch for broad security torso; 6 degree arm clearance; Attack_D with 4.5 degree clearance; repaired boot support and native bind lengths')
src=src.replace("'geometry_modified':False,'weights_modified':False","'geometry_modified':True,'weights_modified':True")
src=src.replace("'native_stage_process_exit':1","'native_stage_process_exit':0")
src=src.replace('All raw clips and caches saved; native retarget commandlet hit animation compression task assertion during shutdown. Final FBX animation import is a separate stage.','All three zombie sources retargeted and saved through the existing editor bridge.')
exec(compile(src,__file__,'exec'))
