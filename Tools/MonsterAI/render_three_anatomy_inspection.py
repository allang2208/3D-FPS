"""Render the requested geometric comparisons from cached, read-only snapshots."""
import bpy,numpy as np,json,sys
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME')
ROOT=P/'SourceAssets/AlienGeometry20261006/AnatomyInspection20261007'
species=sys.argv[sys.argv.index('--')+1];OUT=ROOT/species
report=json.loads((OUT/'inspection.json').read_text(encoding='utf8'))

def render(name,cases,region,target,view,scale,parts=None):
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    target=Vector(target);direction=Vector(view).normalized();right=Vector((0,0,1)).cross(direction).normalized()
    for ci,case in enumerate(cases):
        offset=right*((ci-(len(cases)-1)*.5)*scale)
        for key,info in report['cases'][case]['meshes'].items():
            if parts and not any(t in key for t in parts):continue
            a=np.load(info['geometry_file']);p=a['p'];f=a['f'];c=p[f].mean(1)
            fs=f[region(c)]
            if not len(fs):continue
            ids,inv=np.unique(fs,return_inverse=True);mesh=bpy.data.meshes.new(key)
            mesh.from_pydata((p[ids]+np.asarray(offset)).tolist(),[],inv.reshape(-1,3).tolist());mesh.update()
            mesh.polygons.foreach_set('use_smooth',np.ones(len(mesh.polygons),bool))
            obj=bpy.data.objects.new(case+'_'+key,mesh);scene.collection.objects.link(obj)
            mat=bpy.data.materials.new(key);mat.diffuse_color=(.57,.55,.52,1)
            if 'Teeth' in key or 'HookFinger' in key:mat.diffuse_color=(.74,.68,.55,1)
            elif 'Gum' in key:mat.diffuse_color=(.43,.24,.21,1)
            elif 'Liner' in key:mat.diffuse_color=(.20,.13,.12,1)
            elif 'Eye_' in key:mat.diffuse_color=(.65,.52,.38,1)
            mat.use_nodes=True;shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.63
            mesh.materials.append(mat)
        for li,(rel,energy,size) in enumerate([(direction*2.2+Vector((-.6,0,1.2)),110,1.0),(direction+right*.8+Vector((0,0,.3)),45,1.)]):
            ld=bpy.data.lights.new('Light','AREA');ld.energy=energy*scale;ld.shape='DISK';ld.size=size*scale
            light=bpy.data.objects.new('Light',ld);scene.collection.objects.link(light);light.location=target+offset+rel*scale
            light.rotation_euler=(target+offset-light.location).to_track_quat('-Z','Y').to_euler()
    camd=bpy.data.cameras.new('InspectionCamera');cam=bpy.data.objects.new('InspectionCamera',camd);scene.collection.objects.link(cam)
    cam.location=target+direction*8;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.type='ORTHO';camd.ortho_scale=scale*len(cases);scene.camera=cam
    scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.color=(.10,.10,.10)
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=720*len(cases);scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('ANATOMY_RENDER '+species+' '+name+' '+','.join(cases),flush=True)

all_faces=lambda c:np.ones(len(c),bool)
if species=='M10Mawcrawler':
    render('mouth_source_lod0_lod3',['source','lod0','lod3'],lambda c:c[:,0]>1.28,(1.75,0,.33),(1,-.20,.10),1.12)
    render('teeth_source_lod0_lod3',['source','lod0','lod3'],all_faces,(1.82,0,.33),(1,-.20,.20),.90,parts=['OralTeeth','OralGum','OralLiner'])
    render('body_lod0_lod3',['lod0','lod3'],all_faces,(0,0,.48),(1,-1,.65),4.9)
elif species=='LurkerM08':
    render('mouth_source_lod0_lod3',['source','lod0','lod3'],lambda c:(c[:,1]<-.80)&(abs(c[:,0])<.29),(0,-1.08,.40),(.20,-1,.12),.66)
    render('arch_source_lod0',['source','lod0'],all_faces,(0,0,.60),(.3,-1,.38),2.70)
else:
    render('hooks_source_lod0',['source','lod0'],lambda c:c[:,2]>2.28,(0,0,2.53),(.5,-1,.25),1.40)
    render('crown_source_lod0',['source','lod0'],lambda c:(c[:,2]<1.36)&(c[:,2]>.27),(0,-.15,.80),(.25,-1,.05),1.27)
    render('membranes_source_lod0',['source','lod0'],all_faces,(0,0,1.38),(.5,-1,.15),3.2)
