"""Scoped source inspection for the user's cuff, waist and ground-hem report."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from render_polish_review import setup,ROOT
s,c,aim=setup('Idle');s.frame_set(1)
c.location=(-3,-5,1.7);aim(c,(0,0,1.0));c.data.ortho_scale=2.12
s.render.resolution_x=850;s.render.resolution_y=1000;s.cycles.samples=20
s.render.filepath=str(ROOT/'Revision07/source07_front.png');bpy.ops.render.render(write_still=True)
c.location=(3,5,1.8);aim(c,(0,0,1.0))
s.render.filepath=str(ROOT/'Revision07/source07_back.png');bpy.ops.render.render(write_still=True)
print('Cuff, waist and hem source inspection only; Chaos and gameplay not run.')
