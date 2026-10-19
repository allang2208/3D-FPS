"""Author blade-following rune coordinates from the six existing blade meshes."""
import bpy,json
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;P.mkdir(parents=True,exist_ok=True)
base=P.parent
bpy.ops.wm.read_factory_settings(use_empty=True)
sources=[('factory','Zhanmadao_Modular_Editable.blend','SM_Zhanmadao_Blade_V1')]
sources += [(key,'CommonModsV2/Zhanmadao_CommonVariants_Editable.blend','SM_Zhanmadao_Blade_'+key+'_V2')
            for key in ['extended_edge','heavy_spine','feather_edge']]
sources += [(key,'TangDaoBladesV1/Zhanmadao_TangDaoBlades_Editable.blend','SM_Zhanmadao_Blade_'+key+'_V1_LOD0')
            for key in ['yanling_edge','tengyun_dragon']]
layouts={}
def slopes(x,y):
    h=np.diff(x);d=np.diff(y)/h;m=np.zeros_like(y)
    for i in range(1,len(y)-1):
        if d[i-1]*d[i]>0:
            a=2*h[i]+h[i-1];b=h[i]+2*h[i-1]
            m[i]=(a+b)/(a/d[i-1]+b/d[i])
    m[0]=d[0];m[-1]=d[-1]
    return m
def expression(x,y,z='ZhanZ'):
    m=slopes(x,y);segments=[]
    for i in range(len(x)-1):
        h=x[i+1]-x[i];a=2*y[i]-2*y[i+1]+h*(m[i]+m[i+1])
        b=-3*y[i]+3*y[i+1]-h*(2*m[i]+m[i+1]);c=h*m[i]
        segments.append((x[i],x[i+1],[a,b,c,y[i]]))
    return segments
def emit_curve(name,segments):
    lines=['float '+name+' = 0.0;']
    for i,(a,b,c) in enumerate(segments):
        gate=('if' if i==0 else 'else if')+' ('+('true' if i==len(segments)-1 else 'ZhanZ <= %.9f'%b)+')'
        lines.extend([gate+' {','  float s = saturate((ZhanZ - %.9f) / %.9f);'%(a,b-a),
          '  '+name+' = ((%.9f*s + %.9f)*s + %.9f)*s + %.9f;'%tuple(c),'}'])
    return '\n'.join(lines)
for key,relative,name in sources:
    with bpy.data.libraries.load(str(base/relative),link=False) as (available,loaded):
        loaded.objects=[name]
    obj=loaded.objects[0];mesh=obj.data;mesh.calc_loop_triangles()
    pts=np.asarray([tuple(v.co) for v in mesh.vertices],dtype=float)*100
    faces=np.asarray([tuple(t.vertices) for t in mesh.loop_triangles]);tri=pts[faces]
    low=float(pts[:,2].min());high=float(pts[:,2].max())
    z=np.linspace(low+.14*(high-low),low+.90*(high-low),9)
    centers=[];widths=[]
    for station in z:
        cuts=[]
        for a,b in [(0,1),(1,2),(2,0)]:
            pa=tri[:,a];pb=tri[:,b];dz=pb[:,2]-pa[:,2]
            valid=(np.abs(dz)>1e-8)&((pa[:,2]-station)*(pb[:,2]-station)<=0)
            t=(station-pa[valid,2])/dz[valid]
            cuts.append(pa[valid]+(pb[valid]-pa[valid])*t[:,None])
        section=np.concatenate(cuts);left=float(section[:,0].min());right=float(section[:,0].max())
        centers.append((left+right)*.5);widths.append((right-left)*.82)
    centers=np.asarray(centers);widths=np.asarray(widths)
    code='''// ZHANMADAO_BLADE_CONTOUR_V1: private coordinates; original PBR UVs are unchanged.
if (RuneMode < -.5) return float4(0,0,0,0);
float ZhanZ = P.z;
float ZhanFaceCoverage = smoothstep(.25,.70,abs(normalize(N.xyz).y));
RuneOpacity *= ZhanFaceCoverage;
HaloOpacity *= ZhanFaceCoverage;
'''
    code+=emit_curve('ZhanCenter',expression(z,centers))+'\n'
    code+=emit_curve('ZhanWidth',expression(z,widths))+'\n'
    code+='''float ZhanAlong = (ZhanZ - %.9f) / %.9f;
P = float3((P.x-ZhanCenter)*Dimensions.x/max(ZhanWidth,.1),0,Dimensions.y+ZhanAlong*Dimensions.z);
N = float3(0,N.y>=0?1:-1,0);
BladeOrigin = float3(0,0,0);
BladeAxis = float3(0,0,1);
// END_ZHANMADAO_BLADE_CONTOUR_V1
'''%(z[0],z[-1]-z[0])
    (P/(key+'_placement.hlsl')).write_text(code,encoding='utf-8')
    layouts[key]={'source':str(base/relative),'mesh_object':name,'z_cm':z.tolist(),
        'center_x_cm':centers.tolist(),'rune_width_cm':widths.tolist(),
        'blade_z_cm':[low,high],'width_fraction':.82,'longitudinal_fraction':[.14,.90],
        'curve':'monotone cubic Hermite','side_policy':'Readable on both broad faces; bevels fade out',
        'geometry_modified':False}
(P/'layouts.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_SIX_RUNE_LAYOUTS_AUTHORED',flush=True)
