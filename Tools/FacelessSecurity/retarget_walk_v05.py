"""Retarget the more upright Zombie Walk_B as the new guard locomotion."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/retarget_male_v02.py').read_text(encoding='utf-8').replace('V02','V05')
start=src.index('sources={');end=src.index('\ncomponent=',start)
src=src[:start]+"sources={'Manny':('/Game/ZombieAnimationPack/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple',{'walk':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Walk_B'})}"+src[end:]
src=src.replace("result.set_preview_skeletal_mesh(target);result.set_editor_property('enable_root_motion',False);result.set_editor_property('force_root_lock',False);save(result)","result.set_preview_skeletal_mesh(target)\n        for prop in ['enable_root_motion','force_root_lock']:\n            if result.get_editor_property(prop):result.set_editor_property(prop,False)\n        save(result)")
exec(compile(src,__file__,'exec'))
