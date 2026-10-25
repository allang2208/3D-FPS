"""Regenerate arcane wear LODs, pickup and icon from the corrected ModelR2."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import prepare_delivery as delivery
delivery.R=delivery.P/'SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2'
delivery.BELTS['arcane']['editable_directory']=str(delivery.P/'SourceAssets/ArcaneConduitBelt20261025/ModelR2/Exports')
delivery.produce('arcane')
