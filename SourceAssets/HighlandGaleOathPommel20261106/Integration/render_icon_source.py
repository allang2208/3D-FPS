from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector

P=Path(__file__).resolve().parent
S=P.parent/'SurfaceR2'
bpy.ops.wm.open_mainfile(filepath=str(S/'Review20261106/GaleOath_Review.blend'))
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
s=bpy.context.scene;model=bpy.data.objects['SM_Highland_Pommel_GaleOath_R2']
apply_grayscale([model]);neutral_output(s)
s.render.resolution_x=1024;s.render.resolution_y=1024
s.render.film_transparent=True;s.view_settings.exposure=-.45
c=s.camera;c.location=Vector((0,-.45,-.059))
c.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler();c.data.ortho_scale=.15
s.render.filepath=str(P/'GaleOath_icon_model_source.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GaleOath_icon_model_source.blend'))
