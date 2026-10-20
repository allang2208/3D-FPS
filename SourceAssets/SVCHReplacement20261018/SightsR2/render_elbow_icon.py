"""Publish the inventory icon only after this revision's UE assets were saved."""
import json
from pathlib import Path
O=Path(__file__).parent
if not json.loads((O/'elbow_install_receipt.json').read_text()).get('complete'):raise RuntimeError('Save the UE revision first')
code=(O.parent/'render_inventory_icon.py').read_text().replace('P=O.parents[1]','P=O.parents[2]').replace('SVCH_Replacement_Editable.blend','SVCH_SightsR2_ElbowFit_Editable.blend')
exec(compile(code,str(O.parent/'render_inventory_icon.py'),'exec'),globals())
