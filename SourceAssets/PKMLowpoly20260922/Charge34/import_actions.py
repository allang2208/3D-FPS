"""Import the five empty-reload clips through the established scoped importer."""
from pathlib import Path
prior=Path(__file__).parent.parent/'EquipCharge31/import_actions.py'
script=prior.read_text().replace('PKM31','PKM34').replace('PKMEquipChargeRevision','PKMChargePushRevision')
script=script.replace('EquipCharge31: video raise/catch/settle; overhand pad contact, full-segment wrist support',
    'Charge34: held rearward pull, brief stop, manual forward push; release fingers only at front stop 5.82s')
# __file__ stays in Charge34, so manifests, FBX files, backups and receipts all
# belong to this revision. Only the five reload_empty manifest entries import.
exec(compile(script,str(prior),'exec'))
