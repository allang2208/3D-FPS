import bpy
from pathlib import Path
O=Path(__file__).parent
for variant in ['prism','angled']:
 for path in sorted((O/variant).glob('*.blend')):
  bpy.ops.wm.open_mainfile(filepath=str(path))
  names=['SM_AKM_angled','SM_AKM_optic']
  existing={n:bpy.data.objects[n] for n in names}
  with bpy.data.libraries.load(str(O/'AKM_Attachments_Editable.blend')) as (src,dst):dst.objects=list(names)
  for name,updated in zip(names,dst.objects):existing[name].data=updated.data;bpy.data.objects.remove(updated,do_unlink=True)
  bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('EDITABLE_PARTS_REFRESH_PASS')
