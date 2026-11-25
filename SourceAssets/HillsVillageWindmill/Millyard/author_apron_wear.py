"""Make a mesh decal for the flat mill apron using the authored traffic-mask coordinates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from author_work_tools import mesh, reset, save

reset()
# Blender Y is reversed on import. FBX V is measured from the bottom of the image.
corners = [(-850, -210, 0), (-850, -1330, 0), (760, -1330, 0), (760, -210, 0)]
surface = mesh('Mill apron traffic', corners, [(0, 1, 2, 3)], 'Wear')
uvs = [(0, 1), (0, 0), (1, 0), (1, 1)]
for loop in surface.data.loops:
    surface.data.uv_layers.active.data[loop.index].uv = uvs[loop.vertex_index]
save('ApronWear')
