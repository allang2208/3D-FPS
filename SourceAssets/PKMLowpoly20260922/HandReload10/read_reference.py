"""Decode the user-selected local video for animation authoring reference."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;R=O.parent;D=O/'ReferenceFrames';D.mkdir(exist_ok=True)
movie=R/'References/PKM_UserReloadReference.mp4'
clip=bpy.data.movieclips.load(str(movie));s=bpy.context.scene
s.render.resolution_x=720;s.render.resolution_y=404;s.render.resolution_percentage=100
s.render.fps=30;s.render.fps_base=1;s.render.image_settings.file_format='PNG'
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
seq=s.sequence_editor_create().strips.new_movie('User PKM Reference',str(movie),channel=1,frame_start=1)
s.render.use_sequencer=True
times=[10.5,10.7,10.9,11.1,11.3,11.5,11.7,11.9,12.1,12.3,12.5,12.7,13.1,13.5,14.1,14.5,14.7,14.9,15.1,15.3,15.5,15.7,15.9,16.1,18.3,18.7,19.1,19.5,24.1,24.5,24.9,25.3]
for t in times:
 s.frame_set(round(t*clip.fps)+1);s.render.filepath=str(D/(f'{t:04.1f}'+'.png'));bpy.ops.render.render(write_still=True)
(O/'reference_decode.json').write_text(json.dumps({'source':str(movie),'fps':clip.fps,'frames':clip.frame_duration,'size':list(clip.size),'sample_seconds':times},indent=2))
print('PKM10_REFERENCE_DECODED',clip.fps,clip.frame_duration,flush=True)
