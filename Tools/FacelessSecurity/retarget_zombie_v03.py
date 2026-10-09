"""Reuse the native retarget pipeline with one coherent zombie donor set."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/retarget_male_v02.py').read_text(encoding='utf-8')
src=src.replace('V02','V03')
start=src.index('sources={');end=src.index('\ncomponent=',start)
src=src[:start]+'''sources={'Manny':('/Game/ZombieAnimationPack/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple',{
    'idle':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Idle_A',
    'walk':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Walk_A',
    'attack':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D'})}'''+src[end:]
src=src.replace("'rotation_xyzw':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]", "'rotation_xyzw':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'scale':[t.scale3d.x,t.scale3d.y,t.scale3d.z]")
exec(compile(src,__file__,'exec'))
