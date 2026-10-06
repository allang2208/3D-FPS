"""Save the five-round loader mesh and profiles to the active RSH family."""
from pathlib import Path
import sys
O=Path(__file__).parent;sys.path.insert(0,str(O))
from loader_materials import create as create_loader_materials
source=(O/'import_base.py').read_text()
source=source.replace("revision='native-715-contact-v2'", "revision='native-715-speedloader-5-v1'")
source=source.replace("metal=u.load_asset", "loader_materials=create_loader_materials(root,save)\nmetal=u.load_asset",1)
source=source.replace("slot.material_interface=bare if arm else metal", "slot.material_interface=bare if arm else loader_materials['LoaderPolymer'] if 'LoaderPolymer' in str(slot.material_slot_name) else loader_materials['LoaderSteel'] if 'LoaderSteel' in str(slot.material_slot_name) else metal")
source=source.replace('RSH12Native71520261003; native V7 grasp; real RSH yoke hinge; hand-relative cartridge pickup and shared insertion contact', 'RSH12Speedloader20261003; five real pockets; original 715 rear grasp and action; shared loader-hand insertion; contact-v2 singles retained')
source=source.replace('RSH12_CONTACT_REPAIR','RSH12_SPEEDLOADER')
# Preserve the later dual reload lowering when rebuilding the loader meshes.
source=source.replace("content=(src/'profile.json').read_text(encoding='utf8')", "latest_dual=O.parent/'RSH12DualReloadDrop20261004'/side/'profile.json'\n        content=(latest_dual if side in ('r','l') and latest_dual.exists() else src/'profile.json').read_text(encoding='utf8')")
exec(compile(source,str(O/'import_assets.py'),'exec'),globals())
