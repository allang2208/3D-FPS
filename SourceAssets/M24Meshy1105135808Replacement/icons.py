from pathlib import Path
root=Path(__file__).resolve().parent
original=root.parent/'M24CarbonSpineGame20261104/render_icon.py'
code=original.read_text(encoding='utf-8').replace('M24_CarbonSpine_Fitted.blend','M24_Meshy_Fitted.blend')
code=code.replace("P.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'","P/'Exports/Icons'")
exec(compile(code,str(original),'exec'))
