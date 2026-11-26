"""Worn ground around placed masonry, sampled from the chapel earth scans."""
import sys
from pathlib import Path

import unreal as u
import import_kit as kit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'OldChapel'))
from chapel_ground_materials import MUD, node, shader, texture


def make_ground_wear(dest):
    mat=kit.A.create_asset('M_DefenseGroundWear',dest,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    pos=node(mat,'WorldPosition')
    uv=node(mat,'TextureCoordinate')
    size=node(mat,'DecalColor')
    scan_uv=shader(mat,'EarthScale','return P.xy/154.;',{'P':pos},2)
    patch_uv=shader(mat,'PatchScale','return P.yx/453.+float2(.23,.71);',{'P':pos},2)
    earth=texture(mat,MUD+'B',scan_uv)
    packed=texture(mat,MUD+'ORM',scan_uv)
    breakup=texture(mat,MUD+'H',patch_uv)
    wear=shader(mat,'FootTraffic',"""
float2 halfSize=Shape.rg*1024.;
float margin=Shape.b*256.;
bool wall=Shape.a<.25;
bool gate=Shape.a>.75;
float2 p=(UV*2.-1.)*(halfSize+float2(wall?0.:margin,margin));
float2 q=abs(p)-halfSize;
float outside=wall?q.y:length(max(q,0.))+min(max(q.x,q.y),0.);
float variation=saturate(.5+1.8*(Patch-.5)+.16*sin(P.x*.013+P.y*.018));
float edge=lerp(22.,72.,variation);
float contact=(1.-smoothstep(2.,edge,outside))*smoothstep(-13.,-2.,outside);
float approach=0.;
if(!wall)
{
    // Both gate mouths lead onto the road. Only the courtyard side of the tower has a ground door.
    float distance=gate?q.y:p.y-halfSize.y;
    float opening=gate?halfSize.x-188.:94.;
    float x=abs(p.x+11.*sin(P.x*.017+P.y*.009));
    float width=opening*(gate?.88:.74)+variation*18.;
    float centre=1.-smoothstep(width*.60,width+17.,x);
    float shoulder=gate?exp2(-pow((x-opening*.55)/17.,2.)):.0;
    float reach=margin*(.60+.32*variation);
    approach=(.49*centre+.25*shoulder)*smoothstep(-19.,2.,distance)*(1.-smoothstep(9.,reach,distance));
    // Break the wall-foot band across the actual opening.
    float doorSide=gate?1.:step(0.,p.y);
    contact*=1.-doorSide*(1.-smoothstep(opening-9.,opening+8.,abs(p.x)));
}
float3 face=cross(ddy(P),ddx(P));
float up=abs(face.z)*rsqrt(max(dot(face,face),1.e-12));
return saturate(max(contact*(.44+.25*variation),approach)*smoothstep(.48,.86,up));
""",{'Shape':(size,'RGBA'),'UV':uv,'P':pos,'Patch':(breakup,'R')},1)
    tint=shader(mat,'PackedEarth',
        'return lerp(E,dot(E,float3(.299,.587,.114))*float3(1.06,.91,.74),.45)*(.90+.10*H);',
        {'E':(earth,'RGB'),'H':(breakup,'R')},3)
    for prop,src,pin in [('BASE_COLOR',tint,''),('ROUGHNESS',packed,'G'),('OPACITY',wear,'')]:
        if not kit.L.connect_material_property(src,pin,getattr(u.MaterialProperty,'MP_'+prop)):
            raise RuntimeError('Ground wear output '+prop)
    errors=kit.L.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    kit.save(mat)
    return mat
