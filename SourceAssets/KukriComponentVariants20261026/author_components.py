"""Produce 9 interchangeable physical parts; roots and lanyard mount stay fixed."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from asset_tools import *
BASE=P.parent/'KukriModules20261026'
TEXTURES=P.parent/'Kukri20261020/Textures'
ROOT='/Game/Weapons/Kukri20261020/ComponentVariants20261026'
plans=json.loads((P/'design-prompts.json').read_text(encoding='utf-8'))['plans']
for folder in ('Export','Textures','Icons'):(P/folder).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Kukri_Modules_Editable.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
source={s:bpy.data.objects['SM_Kukri_'+n+'_Factory'].data for s,n in [('grip','Grip'),('pommel','Pommel'),('lanyard','Lanyard')]}
for o in scene.objects:o.hide_render=True;o.hide_set(True)

def deformation(kind):
    def apply(p):
        q=p.copy()
        if kind.startswith('Grip'):
            f=smooth(-.071,-.061,p.z)*(1-smooth(.035,.050,p.z))*smooth(.004,.0075,abs(p.y))
            if kind=='GripCheckered':
                groove=(1-abs(math.sin((p.x+p.z)*800))*abs(math.sin((p.x-p.z)*800)))**3
                q.y-=math.copysign(.00012*f*groove,p.y)
            elif kind=='GripLeather':
                groove=math.exp(-(math.sin((p.z+p.x*.65)*480)/.2)**2)
                q.y-=math.copysign(.00012*f*groove,p.y)
        elif kind.startswith('Pommel'):
            f=(1-smooth(-.007,-.003,p.z))*smooth(.0045,.0075,abs(p.y))
            if kind=='PommelFaceted':
                panel=max(0.,1-abs(p.x-.004)/.026)
                q.y-=math.copysign(.00065*f*panel,p.y)
            if kind=='PommelRinged':
                bands=sum(math.exp(-((p.z-z)/.00055)**2) for z in (-.028,-.031,-.034))
                q.y-=math.copysign(.00025*f*bands,p.y)
        elif kind in ('LanyardTassel','LanyardTag') and p.z<-.010:
            q.z=-.010+(p.z+.010)*.52
        return q
    return apply

def material(kind):
    m,nt,bs,out=make_mat('Author_'+kind)
    tc=node(nt,'ShaderNodeTexCoord');sep=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Object'],sep.inputs[0])
    x,y,z=sep.outputs
    noise=node(nt,'ShaderNodeTexNoise');noise.inputs['Scale'].default_value=850;noise.inputs['Detail'].default_value=2
    nt.links.new(tc.outputs['Object'],noise.inputs['Vector'])
    original=tex(nt,TEXTURES/'T_Kukri_BaseColor.png',True,'SourceUV')
    orm=tex(nt,TEXTURES/'T_Kukri_ORM.png',False,'SourceUV');old=node(nt,'ShaderNodeSeparateColor');nt.links.new(orm.outputs[0],old.inputs[0])
    attr=node(nt,'ShaderNodeVertexColor',layer_name='SurfaceMask');mask=node(nt,'ShaderNodeSeparateColor');nt.links.new(attr.outputs[0],mask.inputs[0])
    region=mask.outputs[0]
    grain=noise.outputs['Fac']
    if kind=='GripCheckered':
        a=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'ADD',x,z),800)))
        b=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'SUBTRACT',x,z),800)))
        grain=op(nt,'POWER',op(nt,'MULTIPLY',a,b),.3)
        color=mix(nt,grain,(.012,.016,.017,1),(.038,.043,.044,1));metal=0.;rough=.67
    elif kind=='GripLeather':
        seam=op(nt,'POWER',op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'ADD',z,op(nt,'MULTIPLY',x,.65)),480))),.22)
        grain=op(nt,'MULTIPLY',seam,op(nt,'ADD',op(nt,'MULTIPLY',grain,.25),.75))
        color=mix(nt,grain,(.022,.009,.004,1),(.15,.056,.019,1));metal=0.;rough=.60
    elif kind=='GripLaminate':
        wave=node(nt,'ShaderNodeTexWave',wave_type='BANDS',bands_direction='X')
        wave.inputs['Scale'].default_value=190;wave.inputs['Distortion'].default_value=7;wave.inputs['Detail Scale'].default_value=1.2
        nt.links.new(tc.outputs['Object'],wave.inputs['Vector']);grain=wave.outputs['Fac']
        color=mix(nt,grain,(.035,.012,.005,1),(.25,.105,.034,1));metal=0.;rough=.34
    elif kind=='PommelFaceted':
        color=mix(nt,grain,(.12,.055,.019,1),(.27,.15,.054,1));metal=.94;rough=.34
    elif kind=='PommelRinged':
        wave=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',z,1050)))
        band=op(nt,'MULTIPLY',mask.outputs[1],op(nt,'GREATER_THAN',wave,.87))
        color=mix(nt,band,(.085,.09,.095,1),(.38,.39,.40,1));grain=wave;metal=.96;rough=.32
    elif kind=='PommelSteel':
        color=mix(nt,grain,(.22,.24,.25,1),(.34,.35,.36,1));metal=.97;rough=.29
    else:
        uv=node(nt,'ShaderNodeUVMap',uv_map='SourceUV');uvsep=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(uv.outputs[0],uvsep.inputs[0])
        a=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'ADD',uvsep.outputs[0],uvsep.outputs[1]),180)))
        b=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',op(nt,'SUBTRACT',uvsep.outputs[0],uvsep.outputs[1]),180)))
        grain=op(nt,'MULTIPLY',a,b)
        dark,light=((.018,.023,.009,1),(.10,.12,.05,1)) if kind=='LanyardBraid' else ((.012,.008,.005,1),(.075,.036,.014,1))
        color=mix(nt,grain,dark,light);metal=0.;rough=.72
    if kind.startswith('Grip'):
        # Retain the source's metal rivets and the true mating seams.
        region=op(nt,'MULTIPLY',region,op(nt,'SUBTRACT',1,op(nt,'GREATER_THAN',old.outputs[2],.5)))
    base=mix(nt,region,original.outputs[0],color)
    roughness=mix(nt,region,old.outputs[1],(rough,rough,rough,1))
    metallic=mix(nt,region,old.outputs[2],(metal,metal,metal,1))
    packed=node(nt,'ShaderNodeCombineColor');nt.links.new(old.outputs[0],packed.inputs[0]);nt.links.new(roughness,packed.inputs[1]);nt.links.new(metallic,packed.inputs[2])
    bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=.00016 if kind.startswith('Grip') else .00008
    nt.links.new(op(nt,'MULTIPLY',region,.45),bump.inputs['Strength']);nt.links.new(grain,bump.inputs['Height'])
    nt.links.new(base,bs.inputs['Base Color']);nt.links.new(roughness,bs.inputs['Roughness']);nt.links.new(metallic,bs.inputs['Metallic']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
    return m,{'BaseColor':base,'ORM':packed.outputs[0]},bs,out

receipt={'source':str(BASE/'Kukri_Modules_Editable.blend'),'stats_authored':False,'runtime_tested':False,'variants':[]}
objects=[]
for plan in plans:
    slot=plan['slot'];kind=plan['kind']
    if slot=='blade_2':continue
    obj=derived_mesh(source[slot],'SM_Kukri_'+kind,deformation(kind),2 if slot=='grip' else 1,slot=='lanyard')
    activate(obj)
    layer=obj.data.color_attributes.new(name='SurfaceMask',type='FLOAT_COLOR',domain='CORNER')
    for i,loop in enumerate(obj.data.loops):
        co=obj.data.vertices[loop.vertex_index].co
        if slot=='grip':f=smooth(-.074,-.067,co.z)*(1-smooth(.043,.055,co.z))
        elif slot=='pommel':f=1-smooth(-.005,-.001,co.z)
        else:f=1.
        layer.data[i].color=(f,1-smooth(-.026,-.023,co.z),0,1)
    mat=material(kind);obj.data.materials.clear();obj.data.materials.append(mat[0]);mats=[mat]
    if kind in ('LanyardTassel','LanyardTag'):
        coords=[v.co for v in obj.data.vertices];lowest=min(v.z for v in coords)
        bottom=[v for v in coords if v.z<lowest+.002]
        end=sum(bottom,Vector())/len(bottom)
        metal=constant_material('CharmMetal_'+kind,(.28,.15,.055) if kind=='LanyardTassel' else (.24,.25,.26),.95,.32);mats.append(metal)
        link=torus('Connector',end+Vector((0,0,-.0035)),.0045,.0011,metal[0]);parts=[obj,link]
        if kind=='LanyardTassel':
            ringcenter=end+Vector((0,0,-.013))
            parts.append(torus('BrassRing',ringcenter,.006,.00125,metal[0]))
            leather=constant_material('TasselLeather',(.065,.024,.009),0,.72);mats.append(leather)
            for i in range(4):
                strip=cube('LeatherStrip',ringcenter+Vector(((i-1.5)*.003,0,-.013)),(.0027,.0012,.019-(i%2)*.002),leather[0],.0004)
                strip.rotation_euler.y=(i-1.5)*.085;parts.append(strip)
        else:
            center=end+Vector((0,0,-.018))
            tag=cube('Tag',center,(.015,.0023,.024),metal[0],.002)
            bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0022,depth=.012,location=center+Vector((0,0,.008)),rotation=(math.pi/2,0,0))
            cutter=bpy.context.object;activate(tag);mod=tag.modifiers.new('Eyelet','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
            bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
            parts.append(tag)
            inlay=constant_material('TagInlay',(.48,.48,.48),.97,.24);mats.append(inlay)
            for side in (-1,1):
                for offset in (-.002,.002):
                    band=cube('TagStripe',center+Vector((offset,side*.00119,-.003)),(.00065,.00012,.012),inlay[0],.00008);parts.append(band)
        obj=join(parts,obj)
    unwrap(obj)
    maps=bake(obj,mats,'T_Kukri_'+kind,P/'Textures',2048 if slot=='grip' else 1024)
    obj.name=obj.data.name='SM_Kukri_'+kind
    fbx=P/'Export'/(obj.name+'.fbx');export(obj,fbx)
    entry={k:plan[k] for k in ('id','name','kind','slot')}
    entry.update(object=obj.name,mesh=ROOT+'/'+obj.name+'.'+obj.name,fbx=str(fbx),textures=maps,
        material=ROOT+'/Materials/M_Kukri_'+kind+'.M_Kukri_'+kind,
        icon_key=slot+'_'+plan['id'],icon=str(P/'Icons'/(slot+'_'+plan['id']+'.png')),
        triangles=sum(len(p.vertices)-2 for p in obj.data.polygons))
    receipt['variants'].append(entry);objects.append(obj);obj.hide_render=True;obj.hide_set(True)
    (P/'components.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COMPONENT_AUTHORED '+plan['id'],flush=True)
objects[0].hide_set(False);objects[0].hide_render=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Components_Editable.blend'))
print('KUKRI_COMPONENTS_PRODUCTION_COMPLETE',flush=True)
