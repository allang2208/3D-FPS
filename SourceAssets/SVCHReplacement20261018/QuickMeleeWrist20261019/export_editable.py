"""Editable 120 Hz source: installed weapon/V9 native rigs and repaired action."""
from pathlib import Path
O=Path(__file__).resolve().parent
source=O.parent/'RootClearance20261019/export_editable.py'
code=source.read_text(encoding='utf-8')
code=code.replace("code=source.read_text().replace('profile_reload_grip.json','profile_root_clearance.json')", "code=source.read_text().replace('profile_reload_grip.json','Profiles/base.json')")
code=code.replace("'SVCH_RootClearance_'", "'SVCH_QuickMeleeWrist_'")
code=code.replace("O/'seat_calibration.json'", "O.parent/'MagazineSeat20261019/seat_calibration.json'")
inject='''
code=code.replace("I = O / 'Inputs'", "I = O.parent / 'ForegripFit20261019/Inputs'")
code=code.replace("for role in ('reload', 'reload_empty'):", "for role in ('quick_melee',):")
code=code.replace("if role == 'reload_empty':", "if role == 'quick_melee':")
code=code.replace('scene.frame_end = 400','scene.frame_end = 108')
code=code.replace('scene.frame_set(325)','scene.frame_set(68)')
'''
code=code.replace("exec(compile(code,str(source),'exec'),globals())",inject+"\nexec(compile(code,str(source),'exec'),globals())")
exec(compile(code,str(source),'exec'),globals())
