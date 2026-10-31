"""Final placements in engine centimetres, aligned to captured support surfaces."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
def placements():
    rows=json.loads((R.parent/'RefinementV2/installed.json').read_text('utf8'))['actors']
    rows=[dict(r) for r in rows if r['actor']!='AP_Bed2_Bed']
    by={r['actor']:r for r in rows}
    by['BP_Headwall']['position_cm']=[2550.,-1006.7,1.8]
    by['BP_WallShelf']['position_cm']=[2153.,-390.,140.]
    by['BP_BedRug']['position_cm']=[2550.,-591.5,1.83]
    by['BP_Slippers']['position_cm']=[2678.,-601.,3.25]
    by['BP_Headphones']['position_cm']=[2456.,-100.,81.1]
    by['BP_DeskLife']['position_cm']=[2490.,-118.,1.55]
    by['BP_DeskCableTray']['position_cm']=[2490.,-118.,1.8]
    # Reading fixture bases use their authored wall standoffs; source light follows diffuser.
    by['BP_ReadingFixture_Left']['position_cm']=[2352.,-1005.5,136.8]
    by['BP_ReadingFixture_Right']['position_cm']=[2748.,-1005.5,136.8]
    by['BP_DeskRail']['position_cm']=[2490.,-88.,179.55]
    rows.append(dict(actor='AP_Bed2_Bed',key='BedRefined',position_cm=[2550.,-835.3,1.8],rotation=dict(yaw=0,pitch=0,roll=0),scale=[1.4,1.4,1.0],collision=True))
    return rows
