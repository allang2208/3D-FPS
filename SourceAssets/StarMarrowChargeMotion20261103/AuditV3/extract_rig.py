from pathlib import Path
import bpy,sys,json,numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parent.parents[1]
sys.path.insert(0,str(ROOT/'SourceAssets/RuneSword20260913/InspectReverseV85'));import v85_keys,v85_setup
c=v85_setup.load('Standard')
def pack(m):return np.array(m).tolist()
out={'rest':{n:pack(m) for n,m in c.rest.items()},'source_idle':{n:pack(m) for n,m in c.idle.items()},'parents':c.parent,'names':c.names}
(P/'rig.json').write_text(json.dumps(out));print('RIG_EXTRACTED',len(c.names))
