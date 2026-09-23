from pathlib import Path
O=Path(__file__).parent
source=(O/'render_delivery.py').read_text().replace("O/'PKM_Gameplay_Editable.blend'","O/'PKM_Manny_Reload_Editable.blend'").replace("bpy.data.actions['PKM_Game_idle']","bpy.data.actions['PKM_Idle']").replace('s.cycles.samples=48','s.cycles.samples=16')
source=source[:source.index('visibility(False,False);shot')]+"\nvisibility(True,False);shot('grip_work_side',(.40,.38,.20),(0,-.075,.005))\nshot('grip_work_under',(.45,.22,-.23),(0,-.095,.005))\n"
exec(compile(source,str(O/'render_delivery.py'),'exec'))
