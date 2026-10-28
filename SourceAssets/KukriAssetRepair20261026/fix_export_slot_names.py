"""Keep the revised blade FBX material names identical to their runtime slot contract."""
import bpy,json,sys,shutil
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriAssetRepair20261026')
V=P.parent/'KukriBladeSurfaceV220261026'
sys.path.insert(0,str(P.parent/'KukriComponentVariants20261026'))
from asset_tools import export
backup=P/'Before';backup.mkdir(exist_ok=True)
master=V/'Kukri_Blade_SurfaceV2_Editable.blend'
if not (backup/master.name).exists():shutil.copy2(master,backup/master.name)
bpy.ops.wm.open_mainfile(filepath=str(master))
for entry in json.loads((V/'surfaces.json').read_text(encoding='utf-8'))['variants']:
    obj=bpy.data.objects[entry['object']]
    name='M_Kukri_'+entry['kind']
    current=obj.data.materials[0];old=bpy.data.materials.get(name)
    if old and old!=current:old.name=name+'_LegacySource'
    current.name=name
    filename=Path(entry['fbx'])
    if not (backup/filename.name).exists():shutil.copy2(filename,backup/filename.name)
    export(obj,filename)
bpy.ops.wm.save_as_mainfile(filepath=str(master))
print('KUKRI_STABLE_SLOT_EXPORT_COMPLETE')
