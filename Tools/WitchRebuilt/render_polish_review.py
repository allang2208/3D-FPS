"""Render the scoped user-requested garment/throw review; never starts gameplay."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Polish20260922'
def setup(role):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'Authoring/WitchRebuilt_{role}.blend'));s=bpy.context.scene
    for o in s.objects:
        if o.type=='MESH':o.hide_render='SimulationProxy' in o.name
    skin=bpy.data.objects['WitchRebuilt_CompleteBody'].data.materials[0]
    nodes=skin.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    skin.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Roughness'].default_value=.8
    texture=OUT/'skin_preview.png'
    if texture.exists():
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(texture));skin.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    else:bs.inputs['Base Color'].default_value=(.3,.23,.14,1)
    s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
    s.render.resolution_x=700;s.render.resolution_y=850;s.render.resolution_percentage=100
    s.world=bpy.data.worlds.new('Review');s.world.color=(.3,.3,.3);s.view_settings.view_transform='AgX'
    def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
    cd=bpy.data.cameras.new('Review');c=bpy.data.objects.new('Review',cd);s.collection.objects.link(c)
    c.location=(3,-5,2.2);aim(c,(0,0,1.05));cd.type='ORTHO';cd.ortho_scale=2.4;s.camera=c
    for loc,energy,size in [((1,-3,4),350,4),((-3,-1,2),240,3),((0,3,3),400,3)]:
        d=bpy.data.lights.new('Review','AREA');d.energy=energy;d.shape='DISK';d.size=size
        ob=bpy.data.objects.new('Review',d);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,0,1))
    return s,c,aim
if __name__=='__main__':
    for role,times in [('Idle',[0]),('ThrowPoisonBottle',[0,.3,.55,.75,.9,1.1,1.5])]:
        s,c,aim=setup(role)
        for t in times:
            s.frame_set(round(t*s.render.fps)+1);s.render.filepath=str(OUT/f'after_{role}_{round(t*100):03d}.png');bpy.ops.render.render(write_still=True)
        if role=='Idle':
            c.location=(3,5,2.2);aim(c,(0,0,1.05));s.render.filepath=str(OUT/'after_Idle_back.png');bpy.ops.render.render(write_still=True)
    print('Saved garment and throw comparison poses')
