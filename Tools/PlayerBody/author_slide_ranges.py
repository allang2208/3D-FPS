"""Author playback cuts from source-poses.json; keep the complete recordings editable."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonSlide20261005'
path=OUT/'assets-saved.json'
receipt=json.loads(path.read_text(encoding='utf-8'))
# Seconds at 30 fps. Entries omit the approach strides and stop once seated;
# exits omit settled idle/running tails. The complete loop already closes.
ranges={
    'Enter.L':(22/30,48/30), 'Enter.R':(24/30,48/30),
    'Enter.Sprint.L':(16/30,39/30), 'Enter.Sprint.R':(19/30,39/30),
    'Loop':(0,12.5), 'Exit.Stand':(3/30,40/30),
    'Exit.Crouch':(3/30,45/30), 'Exit.CrouchMove':(3/30,23/30),
    'Exit.Walk':(3/30,35/30), 'Exit.Run':(3/30,40/30),
    'Exit.Sprint':(3/30,32/30),
}
for role,(begin,end) in ranges.items():
    clip=u.load_asset(receipt['runtime_clips']['Slide.'+role])
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    u.AnimationLibrary.add_animation_notify_track(clip,'SlidePlayback')
    u.AnimationLibrary.add_animation_sync_marker(clip,'SlideBegin',begin,'SlidePlayback')
    u.AnimationLibrary.add_animation_sync_marker(clip,'SlideEnd',min(end,clip.get_play_length()),'SlidePlayback')
    if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+role)
receipt['playback_ranges']=ranges
path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SLIDE_RANGES_SAVED',len(ranges))
