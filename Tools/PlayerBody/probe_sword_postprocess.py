"""Temporarily isolate the reported pawn's post-process layer, then restore it."""
import json
from pathlib import Path
import unreal as u

class SwordPostProbe:
    def __init__(self):
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        self.pawn=u.GameplayStatics.get_player_pawn(world,0)
        self.body=self.pawn.mesh
        self.original=self.body.get_editor_property('disable_post_process_blueprint')
        self.data={'original_disabled':self.original,'before':self.sample()}
        self.frames=0
        self.body.set_editor_property('disable_post_process_blueprint',True)
        self.handle=u.register_slate_post_tick_callback(self.tick)
    def sample(self):
        return {b:[t.translation.x,t.translation.y,t.translation.z]
                for b in ('upperarm_r','lowerarm_r','hand_r','upperarm_l','lowerarm_l','hand_l')
                for t in [self.body.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)]}
    def tick(self,delta):
        self.frames+=1
        try:
            if self.frames==4:
                self.data['without_postprocess']=self.sample()
                self.body.set_editor_property('disable_post_process_blueprint',self.original)
            if self.frames>=8:
                self.data['restored']=self.sample()
                self.data['restored_disabled']=self.body.get_editor_property('disable_post_process_blueprint')
                self.finish()
        except Exception as e:
            self.data['error']=str(e)
            self.finish()
    def finish(self):
        try:self.body.set_editor_property('disable_post_process_blueprint',self.original)
        finally:
            u.unregister_slate_post_tick_callback(self.handle)
            out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonTwoHandSword20261003/postprocess-isolation.json')
            out.write_text(json.dumps(self.data,indent=2),encoding='utf-8')

sword_post_probe=SwordPostProbe()
print('SWORD_POSTPROCESS_PROBE_QUEUED')
