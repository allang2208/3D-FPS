"""A broad attached meniscus tapering to one lower point, with separate released drops."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';BASE='/Game/Dungeons/SlimeSheet20260922'
CFG=json.loads((ROOT.parent/'DungeonRoomShells20260922/Config/rooms.json').read_text(encoding='utf-8'));room=CFG['rooms'][1];tip=room['pipes'][0]['points'][-1];lip=[tip[0]+.012,tip[1],tip[2]-.17+.007]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
items=[]
def export(name,vs,fs,uvs,colors,material):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();uv=me.uv_layers.new();vc=me.color_attributes.new(name='FluidMeta',type='FLOAT_COLOR',domain='CORNER');me.materials.append(bpy.data.materials.new('CF_'+material))
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            # UE's FBX importer changes V to 1-V. Store the inverse so shader UV
            # recovers the exact parametric coordinate used to author these vertices.
            vi=me.loops[li].vertex_index;uv.data[li].uv=(uvs[vi][0],1-uvs[vi][1]);vc.data[li].color=colors[vi]
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    path=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    items.append(dict(name=name,fbx=str(path),destination=BASE+'/Meshes',materials={'CF_'+material:BASE+'/Materials/'+material},collision=False,room='Drainage',local_m=lip,half_size_cm=None))
def sheet(u,v):
    a=2*u-1;y=a*(.105*(1-v)**1.12+.0017)
    top=.17-math.sqrt(max(.001,.17**2-(a*.105)**2))+.003
    return (-.010+.012*v+.006*math.sin(math.pi*v),y,top*(1-v)-.112*v)
vs=[];fs=[];uv=[];colors=[];nx,ny=36,48
for j in range(ny+1):
    v=j/ny
    for i in range(nx+1):
        u=i/nx;vs.append(sheet(u,v));uv.append((u,v));colors.append((1,0,0,1))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i;b=a+1;fs.append((a,a+nx+1,b+nx+1,b))
export('SM_PipePusTongue',vs,fs,uv,colors,'M_PusConvergingSheet')
vs=[];fs=[];uv=[];colors=[];sides=24;rows=20
for phase,size in ((0,1),(.98,.48)):
    base=len(vs)
    for j in range(rows+1):
        v=j/rows;theta=math.pi*v
        for i in range(sides+1):
            u=i/sides;a=math.tau*u;vs.append((.01*math.sin(theta)*math.cos(a),.01*math.sin(theta)*math.sin(a),.01*math.cos(theta)));uv.append((u,v));colors.append((phase,size,0,1))
    for j in range(rows):
        for i in range(sides):
            a=base+j*(sides+1)+i;b=a+1;fs.append((a,a+sides+1,b+sides+1,b))
export('SM_PipePusDrops',vs,fs,uv,colors,'M_PusConvergedDrops')
falltime=math.sqrt(2*(lip[2]-.014-.112)/5)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ConvergingPipeSlime.blend'))
(OUT/'fluids.json').write_text(json.dumps(dict(objects=items,falltime=falltime,release_time=1.48,period=2.35,lip_local_m=lip),indent=2))
for item in room['pipe_slime']['objects']:
    replacement=next((r for r in items if r['name']==item['name']),None)
    if replacement:item.update(replacement)
    elif item['name']=='SM_PipePusPuddle':item['material_override']=BASE+'/Materials/MI_PusPuddleSingleImpact'
(ROOT.parent/'DungeonRoomShells20260922/Config/rooms.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
print('CONVERGING_SLIME_AUTHORED',len(items))
