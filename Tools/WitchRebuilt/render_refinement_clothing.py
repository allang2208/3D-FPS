"""Inspect the reported leg/skirt overlap in editable source poses (no game test)."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from render_polish_review import setup,ROOT
OUT=ROOT/'Refinement20260922'
s,c,aim=setup('Idle');s.frame_set(1)
c.location=(2,-5,1.55);aim(c,(0,0,1.03));c.data.ortho_scale=2.3
s.render.filepath=str(OUT/'clothing_front.png');bpy.ops.render.render(write_still=True)
s,c,aim=setup('DeathBackward');s.frame_set(round((s.frame_end-1)*.60)+1)
c.location=(3,-4,2);aim(c,(0,.25,.7));c.data.ortho_scale=2.6
s.render.filepath=str(OUT/'clothing_death_handoff.png');bpy.ops.render.render(write_still=True)
