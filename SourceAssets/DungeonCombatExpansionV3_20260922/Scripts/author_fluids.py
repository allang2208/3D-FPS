"""Radial puddle and short cyclic gathering necks; no permanently extruded liquid strand."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];V2=ROOT.parent/'DungeonCombatExpansion20260922';OUT=ROOT/'Authored';BASE='/Game/Dungeons/CombatExpansionV3_20260922'
CFG=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'));room=CFG['rooms'][1];pipe=room['pipes'][0];tip=pipe['points'][-1];lip=[tip[0]+.012,tip[1],tip[2]-pipe['radius']+.007]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
items=[]
def export(name,vs,fs,uvs,colors,material,origin,half=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();uv=me.uv_layers.new();vc=me.color_attributes.new(name='FluidMeta',type='FLOAT_COLOR',domain='CORNER');me.materials.append(bpy.data.materials.new('CF_'+material))
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            vi=me.loops[li].vertex_index;uv.data[li].uv=uvs[vi];vc.data[li].color=colors[vi]
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    path=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    items.append(dict(name=name,fbx=str(path),destination=BASE+'/Meshes',materials={'CF_'+material:BASE+'/Materials/'+material},collision=False,room=room['id'],local_m=origin,half_size_cm=half,radial_footprint=half is not None))
    ob.location=origin
t=room['trench'];x0,y0,x1,y1=t['rect']
channel=json.loads((V2/'Authored/fluids.json').read_text())['objects'][0];channel['local_m']=[(x0+x1)/2,(y0+y1)/2,-t['depth']];channel['reuse_asset']=channel['destination']+'/'+channel['name'];items.append(channel)
impact=[lip[0]+.085,lip[1],0];hx,hy=.72,.67
vs=[(0,0,.014)];uv=[(0,0)];col=[(1,0,0,1)];fs=[];segments=112;rings=38
for j in range(1,rings+1):
    q=j/rings;wet=min(1,(1-q)/.11)
    for i in range(segments):
        a=math.tau*i/segments;outline=1+.035*math.sin(5*a)+.022*math.sin(9*a+.4)
        x=hx*q*outline*math.cos(a);y=hy*q*outline*math.sin(a)
        vs.append((x,y,.004+.010*wet));uv.append((x,y));col.append((wet,0,0,1))
for i in range(segments):fs.append((0,1+i,1+(i+1)%segments))
for j in range(rings-1):
    for i in range(segments):
        a=1+j*segments+i;b=1+j*segments+(i+1)%segments;fs.append((a,a+segments,b+segments,b))
export('SM_PipePusPuddle',vs,fs,uv,col,'MI_PusPuddleRadial',impact,[72,67])
period=2.35;release=1.48;falltime=math.sqrt(2*(lip[2]-.014-.035)/5)
for attached in (False,True):
    vs=[];fs=[];uv=[];col=[];sides=28;rows=26
    for index,phase in enumerate((0,.37,.73)):
        base=len(vs)
        for j in range(rows+1):
            v=j/rows;theta=math.pi*v
            for i in range(sides+1):
                u=i/sides;a=math.tau*u
                p=(.008*math.cos(a),.008*math.sin(a),-.05*v) if attached else (.01*math.sin(theta)*math.cos(a),.01*math.sin(theta)*math.sin(a),.01*math.cos(theta))
                vs.append(p);uv.append((u,v));col.append((phase,index/2,0,1))
        for j in range(rows):
            for i in range(sides):
                a=base+j*(sides+1)+i;b=a+1
                # Outward winding: axial/polar direction crossed with azimuth.
                fs.append((a,a+sides+1,b+sides+1,b))
    export('SM_PipePusTongue' if attached else 'SM_PipePusDrops',vs,fs,uv,col,'M_PusGatheringNeck' if attached else 'M_PusReleasedDrops',lip)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonFluidRadialSource.blend'))
(OUT/'fluids.json').write_text(json.dumps(dict(objects=items,drop_period=period,release_time=release,falltime=falltime,lip_local_m=lip,impact_local_m=impact),indent=2))
room['pipe_slime']={'objects':[i for i in items if i['name']!='SM_PusChannelFluid'],'damage':8,'interval':.5}
for path in [ROOT/'Config/rooms.json',ROOT.parent/'DungeonRoomShells20260922/Config/rooms.json']:
    path.write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
print('RADIAL_FLUID_SOURCE_AUTHORED',len(items))
