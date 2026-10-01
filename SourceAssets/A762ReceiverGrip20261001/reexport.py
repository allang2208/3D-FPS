import bpy,json,sys
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ReceiverGrip08.blend'));bpy.context.preferences.filepaths.save_version=0
parts=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];OUT=O/'Exports';h=G.read('Body')[0];plan=json.loads((O/'authoring.json').read_text())
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
exec(compile((O/'author.py').read_text().split('# Export indexed buffers with all surviving UV channels and corner normals.')[1],str(O/'author.py')+' export','exec'))
