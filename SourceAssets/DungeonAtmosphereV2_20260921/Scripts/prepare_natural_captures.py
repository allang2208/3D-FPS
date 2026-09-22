"""Prepare the previously requested real UE art screenshots for this revision."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'Scripts'
script=(S/'capture_v2.py').read_text(encoding='utf-8')
script=script.replace("Previews/DungeonAtmosphereV2_20260921'","Previews/DungeonAtmosphereV2_20260921/NaturalPass'")
script=script.replace('Receipts/capture-state.json','Receipts/natural-segment-capture-state.json')
start=script.index('VIEWS=[');end=script.index('\nAA=',start)
script=script[:start]+'''VIEWS=[
    ('01_corridor',[180,-210,165],[2050,-210,175],82),
    ('02_layered_fracture',[320,-245,142],[415,-385,107],63),
    ('03_fallen_fragments',[310,-273,105],[379,-364,18],68),
    ('04_maintenance_repair',[370,-165,148],[356,-15,82],68),
    ('05_impact_zone',[222,-132,136],[150,-15,90],65),
    ('06_leak_context',[420,-45,160],[380,-385,195],88),
]'''+script[end:]
(S/'capture_natural_segment.py').write_text(script,encoding='utf-8')
wrapper=(S/'capture_v2.ps1').read_text(encoding='utf-8')
wrapper=wrapper.replace('Receipts/capture-state.json','Receipts/natural-segment-capture-state.json').replace('bridge-capture-','bridge-natural-capture-').replace("'capture_v2.py'","'capture_natural_segment.py'")
(S/'capture_natural_segment.ps1').write_text(wrapper,encoding='utf-8')
