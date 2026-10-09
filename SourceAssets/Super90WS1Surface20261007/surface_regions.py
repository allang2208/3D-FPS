"""Register the source PNG atlas, then assign semantic WS1 materials."""
import bpy,numpy as np
from pathlib import Path
from collections import defaultdict
O=Path(__file__).parent;T=O.parent/'BenelliM4Super9020261006/Original/Source/textures'
ROLES={'TTI_Benelli_M4':('CleanAnodized',(.020,.021,.022),.46,1.),'S90_BarrelSteel':('CleanSatinSteel',(.034,.035,.037),.42,1.),
       'S90_MovingSteel':('CleanSatinSteel',(.065,.067,.069),.34,1.),'S90_AccentMetal':('CleanPolishedSteel',(.24,.17,.085),.35,1.),
       'S90_Polymer':('CleanPolymer',(.019,.019,.018),.55,0.),'S90_Rubber':('Rubber',(.0103,.0103,.0103),.70,0.),
       'FactorySights':('CleanSatinSteel',(.034,.035,.037),.43,1.),'matchsaverz':('CleanPolymer',(.019,.019,.018),.55,0.)}
def pixels(stem):
    im=bpy.data.images.load(str(T/(stem+'.png')),check_existing=True);im.colorspace_settings.name='Non-Color'
    return np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],4)
def apply_surface_regions(parts):
    import sys
    sys.path.insert(0,str(O.parent/'Super90Mapping20261007'))
    from mapping import correct_weapon_uv
    correct_weapon_uv(parts)
    # Rebuild the old atlas-derived regions from the registered source UVs.
    for ob in parts:
        source=ob.data.materials.find('TTI_Benelli_M4')
        for face in ob.data.polygons:
            if ob.data.materials[face.material_index].name.startswith('S90_'):face.material_index=source
    metal=pixels('TTI_Benelli_M4_Metallic_brand_friendly');base=pixels('TTI_Benelli_M4_BaseColor_brand_friendly')
    h,w=metal.shape[:2];stats=defaultdict(lambda:{'faces':0,'area_m2':0.,'uv_area':0.});islands=[]
    for ob in parts:
        me=ob.data;uv=me.uv_layers[0].data;faces=[f for f in me.polygons if me.materials[f.material_index].name=='TTI_Benelli_M4']
        parent={f.index:f.index for f in faces};corners={}
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for f in faces:
            for li in f.loop_indices:
                co=me.vertices[me.loops[li].vertex_index].co;xy=uv[li].uv
                k=tuple(round(v,6) for v in (*co,*xy))
                if k in corners:parent[find(f.index)]=find(corners[k])
                else:corners[k]=f.index
        groups=defaultdict(list)
        for f in faces:groups[find(f.index)].append(f)
        for group in groups.values():
            mids=[sum((uv[li].uv for li in f.loop_indices),uv[f.loop_start].uv*0)/len(f.loop_indices) for f in group]
            indices=[(min(h-1,max(0,int(p.y*h))),min(w-1,max(0,int(p.x*w)))) for p in mids]
            a=np.array([max(f.area,1e-12) for f in group]);m=np.array([metal[y,x,0] for y,x in indices]);c=np.array([base[y,x,:3] for y,x in indices])
            gold=(c[:,0]>c[:,1]*1.10)&(c[:,1]>c[:,2]*1.12)&(c[:,0]>.28)
            avg=float(np.average(m,weights=a));gold_fraction=float(np.average(gold,weights=a))
            points=[me.vertices[vi].co for f in group for vi in f.vertices];lo=[min(p[k] for p in points) for k in range(3)];hi=[max(p[k] for p in points) for k in range(3)]
            role='TTI_Benelli_M4'
            if avg<.12:role='S90_Rubber' if hi[1]<-.425 else 'S90_Polymer'
            elif gold_fraction>.5:role='S90_AccentMetal'
            elif ob.name in ('Super90_bolt','Super90_loading_gate','Super90_trigger'):role='S90_MovingSteel'
            elif lo[1]>.035:role='S90_BarrelSteel'
            if me.materials.find(role)<0:
                material=bpy.data.materials.get(role)
                if not material:material=bpy.data.materials['TTI_Benelli_M4'].copy();material.name=role
                me.materials.append(material)
            index=me.materials.find(role)
            for f in group:f.material_index=index
            islands.append({'object':ob.name,'faces':len(group),'source_metal_average':avg,'gold_fraction':gold_fraction,'role':role,'lo':lo,'hi':hi})
        for f in me.polygons:
            role=me.materials[f.material_index].name
            if role not in ROLES:continue
            stats[role]['faces']+=1;stats[role]['area_m2']+=f.area
            pts=[uv[li].uv for li in f.loop_indices];stats[role]['uv_area']+=abs(sum(pts[i].x*pts[(i+1)%len(pts)].y-pts[(i+1)%len(pts)].x*pts[i].y for i in range(len(pts))))*.5
    for name,(_,color,rough,metallic) in ROLES.items():
        mat=bpy.data.materials.get(name)
        if not mat:continue
        mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for pin,value in [('Base Color',(*color,1)),('Roughness',rough),('Metallic',metallic)]:
            for link in list(bs.inputs[pin].links):mat.node_tree.links.remove(link)
            bs.inputs[pin].default_value=value
        if name=='TTI_Benelli_M4':
            n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(O/'Textures/T_Super90_CleanReceiver.png'),check_existing=True);n.image.colorspace_settings.name='sRGB'
            mat.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color'])
        if name!='matchsaverz':
            # The gun PNG is DirectX; Blender's Normal Map node expects OpenGL.
            # UE consumes the same file without a green-channel flip.
            def named(kind,label):
                node=mat.node_tree.nodes.get(label)
                if not node:node=mat.node_tree.nodes.new(kind);node.name=label
                return node
            tex=named('ShaderNodeTexImage','S90 Source DirectX Normal')
            tex.image=bpy.data.images.load(str(T/'TTI_Benelli_M4_Normal_brand_friendly.png'),check_existing=True)
            tex.image.colorspace_settings.name='Non-Color'
            convert=named('ShaderNodeVectorMath','S90 DirectX To Blender');convert.operation='MULTIPLY_ADD'
            convert.inputs[1].default_value=(1,-1,1);convert.inputs[2].default_value=(0,1,0)
            normal=named('ShaderNodeNormalMap','S90 Registered Normal');normal.inputs['Strength'].default_value=1.
            mat.node_tree.links.new(tex.outputs['Color'],convert.inputs[0])
            mat.node_tree.links.new(convert.outputs['Vector'],normal.inputs['Color'])
            mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        mat['Super90SurfaceStandard']='WS1.1 Clean; source PNG V-origin conversion only; gun normal is DirectX'
    return {'slots':dict(stats),'islands':islands}
