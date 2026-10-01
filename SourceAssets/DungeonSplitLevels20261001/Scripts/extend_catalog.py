"""Append the authored ramps without redrawing themes or replacing room recipes."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def extend(catalog):
    result=copy.deepcopy(catalog)
    ramps=json.loads((ROOT/'Config/ramps.json').read_text('utf-8'))
    ids={m['id'] for m in ramps}
    result['modules']=[m for m in result['modules'] if m['id'] not in ids]+ramps
    result['themed_routes']['split_level_connections']=dict(version=1,rises_cm=[540,1080,1620],
        layout='whole_core_above_or_below_transition_floor',flat_connection_max_cm=2400,
        ramp_connection_max_cm=4600,spawn_connectors=False)
    return result
