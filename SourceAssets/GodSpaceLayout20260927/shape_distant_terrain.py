import bpy, math
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927');bpy.ops.wm.open_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'));s=bpy.context.scene
ob=bpy.data.objects['NEW remote earth backdrop'];me=ob.data;col=me.color_attributes['EarthTint']
for v in me.vertices:
 x,y,_=v.co; river=250*math.sin(y*.00037)+650*math.sin(y*.00012);d=abs(x-river)
 ridge=.5+.22*math.sin(x*.0012+1.5*math.sin(y*.0006))+.16*math.cos(y*.001+.6*math.cos(x*.0008))+.1*math.sin(x*.002+y*.0013)
 h=520*max(0,min(1,ridge))**2*(1-math.exp(-(d/800)**2));v.co.z=-1500+h
 if d<170:rgb=(.07,.22,.26)
 elif d<480:rgb=(.19,.29,.12)
 else:rgb=(.13+h*.00022,.25+h*.00013,.11+h*.00025)
 haze=min(.6,math.hypot(x,y)/22000+.07);sky=(.40,.53,.60);col.data[v.index].color=(*(rgb[i]*(1-haze)+sky[i]*haze for i in range(3)),1)
me.update()
# Reduce distant deck bump to retain only broad cloud relief, with visible ground openings.
ma=bpy.data.materials['NEW distant cloud deck prototype']
for n in ma.node_tree.nodes:
 if n.type=='BUMP':n.inputs['Distance'].default_value=8
 if n.type=='VALTORGB':n.color_ramp.elements[0].position=.55;n.color_ramp.elements[1].position=.66
c=bpy.data.objects['Preview overlook'];c.location=(8,46.5,2.4);c.rotation_euler=(Vector((0,1600,-1100))-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=22
s.cycles.samples=40;s.cycles.volume_bounces=1;s.camera=bpy.data.objects['Preview aerial']
bpy.ops.wm.save_as_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'))
for name,cam in [('godspace_overlook',c),('godspace_aerial',bpy.data.objects['Preview aerial'])]:
 s.camera=cam;s.render.filepath=str(R/'Preview'/(name+'.png'));bpy.ops.render.render(write_still=True)
