from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'inspect_front.py').read_text().split('scene=bpy.context.scene')[0],str(O/'extract_original.py'),'exec'),globals())
