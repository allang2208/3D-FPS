"""Index the already completed prototype's exact cloth inputs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write,np,input_signature
data=np.load(C/'Simulation/FP_M4.npz');body=read(C/'Read/Native_M4.json');evidence=read(C/'Review/FP_M4-anchors.json')
evidence['input_signature']=input_signature(data['before'],data['triangles'],data['pins'],body,36,.12)
write(C/'Review/FP_M4-anchors.json',evidence);print('M4_CLOTH_CACHE_INDEXED',flush=True)
