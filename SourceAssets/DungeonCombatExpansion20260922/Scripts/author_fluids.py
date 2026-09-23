"""Dense fluid surfaces and independently moving geometric drops. No scene rendering."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';BASE='/Game/Dungeons/CombatExpansion20260922'
CFG=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'));room=CFG['rooms'][1];pipe=room['pipes'][0];tip=pipe['points'][-1];lip=[tip[0]+.012,tip[1],tip[2]-pipe['radius']+.007]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
items=[]
def export(name,vs,fs,uvs,colors,material,origin,half=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();uv=me.uv_layers.new();vc=me.color_attributes.new(name='FluidMeta',type='FLOAT_COLOR',domain='CORNER');me.materials.append(bpy.data.materials.new('CF_'+material))
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            vi=me.loops[li].vertex_index;uv.data[li].uv=uvs[vi];vc.data[li].color=colors[vi]
    obj=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(obj);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    items.append(dict(name=name,fbx=str(path),destination=BASE+'/Meshes',materials={'CF_'+material:BASE+'/Materials/'+material},collision=False,room=room['id'],local_m=origin,half_size_cm=half))
    obj.location=origin

# The trench surface remains below the bridge; two-dimensional tessellation carries waves.
def surface(name,hx,hy,depth,puddle,origin,material):
    nx=48 if not puddle else 54;ny=132 if not puddle else 44;vs=[];fs=[];uv=[];col=[]
    for j in range(ny+1):
        y=-hy+2*hy*j/ny
        for i in range(nx+1):
            x=-hx+2*hx*i/nx
            if puddle:
                q=max(abs(x/hx),abs(y/hy));a=math.atan2(y/hy,x/hx);r=(abs(math.cos(a))**6+abs(math.sin(a))**6)**(-1/6)
                norm=math.hypot(x/hx,y/hy);fac=(r*q/max(norm,.0001))*(1+.035*math.sin(a*5)+.021*math.sin(a*9+.4))
                xx=x*fac if norm else 0;yy=y*fac if norm else 0;coverage=min(1,max(0,(1-q)/.13))
            else:xx,yy=x,y;coverage=min(1,max(0,min(hx-abs(x),hy-abs(y))/.1))
            vs.append((xx,yy,depth*(.30+.70*coverage)));uv.append((xx,yy));col.append((coverage,0,0,1))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
    export(name,vs,fs,uv,col,material,origin,[hx*100,hy*100])
t=room['trench'];x0,y0,x1,y1=t['rect']
surface('SM_PusChannelFluid',1.41,3.91,.064,False,[(x0+x1)/2,(y0+y1)/2,-t['depth']],'MI_PusChannelFluid')
impact=[lip[0]+.11,lip[1],0]
surface('SM_PipePusPuddle',.67,.51,.012,True,impact,'MI_PusPuddleFluid')

# Droplet UV = (cycle phase, fall time). Each sphere is translated intact by the shader.
# Gravity 5 m/s^2 and slow intermittent release give visible viscous drops at a 68 cm fall.
vs=[];fs=[];uv=[];col=[];fallheight=lip[2]-.012;falltime=math.sqrt(2*fallheight/5);period=1.55
for n,(phase,yoff,radius) in enumerate([(0,0,.014),(.34,.037,.009),(.73,-.032,.011)]):
    base=len(vs);sides=12;rings=10
    for j in range(rings+1):
        theta=math.pi*j/rings
        for i in range(sides):
            a=math.tau*i/sides;x=radius*math.sin(theta)*math.cos(a);y=yoff+radius*math.sin(theta)*math.sin(a);z=radius*math.cos(theta)*1.8
            vs.append((x,y,z));uv.append((phase,falltime));col.append((1,0,0,1))
    for j in range(rings):
        for i in range(sides):
            a=base+j*sides+i;b=base+j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
export('SM_PipePusDrops',vs,fs,uv,col,'M_PusDrops',lip)

# Attached narrowing wet tongue at the mouth, with a fixed upper end.
vs=[];fs=[];uv=[];col=[]
for j in range(25):
    z=-.16*j/24;radius=.012*(1-j/24*.65)
    for i in range(16):
        a=math.tau*i/16;vs.append((.025*j/24+radius*math.cos(a),radius*math.sin(a),z));uv.append((i/16,j/24));col.append((j/24,0,0,1))
for j in range(24):
    for i in range(16):
        a=j*16+i;b=j*16+(i+1)%16;fs.append((a,b,b+16,a+16))
export('SM_PipePusTongue',vs,fs,uv,col,'M_PusTongue',lip)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonFluidSource.blend'))
(OUT/'fluids.json').write_text(json.dumps(dict(objects=items,drop_period=period,falltime=falltime,lip_local_m=lip,impact_local_m=impact),indent=2),encoding='utf-8')
room['trench']['hazard']['mesh']=BASE+'/Meshes/SM_PusChannelFluid'
room['pipe_slime']={'objects':[i for i in items if i['name']!='SM_PusChannelFluid'],'damage':8,'interval':.5}
for path in [ROOT/'Config/rooms.json',ROOT.parent/'DungeonRoomShells20260922/Config/rooms.json']:
    path.write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
print('FLUID_GEOMETRY_AUTHORED',len(items))
