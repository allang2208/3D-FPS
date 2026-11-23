// Proxy and scene depth are in cm. Only the exit face is rasterized, including with the camera inside.
float3 ray = normalize(LocalExit - LocalEye);
float3 invRay = rcp(float3(ray.x >= 0 ? max(ray.x,1.e-5) : min(ray.x,-1.e-5),
                           ray.y >= 0 ? max(ray.y,1.e-5) : min(ray.y,-1.e-5),
                           ray.z >= 0 ? max(ray.z,1.e-5) : min(ray.z,-1.e-5)));
float3 t0 = (float3(-16.5,-16.5,-2.) - LocalEye) * invRay;
float3 t1 = (float3(16.5,16.5,40.5) - LocalEye) * invRay;
float3 enter = min(t0,t1);
float first = max(0.,max(enter.x,max(enter.y,enter.z)));
float exitDistance = length(LocalExit-LocalEye);
float last = min(exitDistance, BehindDepth * exitDistance / max(.01,ExitDepth));
if (last <= first) return float4(0,0,0,0);

float time = TimeSeconds + Phase;
float2 lean = clamp(UpLocal.xy / max(.62,UpLocal.z),float2(-.35,-.35),float2(.35,.35));
int steps = clamp((int)ceil((last-first)*.68),6,18);
float stepCm = (last-first)/steps;
float transmission = 1.;
float3 light = 0.;
[loop] for (int i=0; i<steps; ++i)
{
    float3 p = LocalEye + ray*(first + (i+.5)*stepCm);
    float z = p.z;
    if (z<.10 || z>38.5) continue;
    float plume = smoothstep(7.,29.,z);
    float2 centre = lean * max(z-10.,0.) * .82;
    centre += plume*float2(1.75*sin(z*.15-time*2.5)+.70*sin(z*.32-time*3.9),
                           1.15*cos(z*.20-time*2.2)+.55*sin(z*.40-time*3.6));
    float2 xy = p.xy-centre;
    float radial = length(xy);
    float r = 4.4 + 2.8*smoothstep(.2,7.4,z);
    r *= 1.-.83*smoothstep(12.,37.,z);
    if (radial>r+3.1) continue;

    // Advect a continuous 3D field up through the burning cloth and crown.
    float angle = z*.041 + .31*sin(z*.18-time*1.8);
    float ss, cc; sincos(angle,ss,cc);
    float2 turned = float2(cc*xy.x-ss*xy.y,ss*xy.x+cc*xy.y);
    float3 uvw = frac(float3(turned*.052 + float2(.041*time,-.032*time),
                             z*.030-time*.38));
    float slice = uvw.z*64.;
    float k = floor(slice), next = fmod(k+1.,64.);
    float2 tile0=float2(fmod(k,8.),floor(k/8.));
    float2 tile1=float2(fmod(next,8.),floor(next/8.));
    float2 inTile=(1.5+uvw.xy*62.)/512.;
    float3 flow=lerp(Texture2DSampleLevel(FlowTex,FlowTexSampler,tile0*.125+inTile,0).rgb,
                     Texture2DSampleLevel(FlowTex,FlowTexSampler,tile1*.125+inTile,0).rgb,frac(slice));
    float edge = r-radial+(flow.r-.5)*lerp(2.,5.5,plume)+(flow.g-.5)*1.45;
    float base = smoothstep(.15,2.75,z+(flow.b-.5)*2.3);
    float top = 1.-smoothstep(27.,37.8,z+(1.-flow.r)*4.-flow.g*2.);
    float skin = smoothstep(-.6,1.35,edge) * base * top;
    float filaments = smoothstep(.12,.70,flow.r*.68+flow.g*.32+max(edge,0.)*.055);
    float density = skin * lerp(.46,1.,filaments) * lerp(1.,.68,plume);
    float hot = saturate(.16+.46*flow.b+.22*flow.r+.28*smoothstep(.15,4.3,edge)
                         -.22*plume-.20*(1.-base));
    float3 rim = float3(2.65,.30,.027);
    float3 amber = float3(6.8,1.76,.16);
    float3 straw = float3(9.9,5.0,1.23);
    float3 emission=lerp(lerp(rim,amber,smoothstep(.18,.66,hot)),straw,smoothstep(.64,.97,hot));
    float absorption=1.-exp(-density*stepCm*.29);
    light += transmission*absorption*emission;
    transmission *= 1.-absorption;
    if (transmission<.018) break;
}
float alpha=1.-transmission;
return float4(light/max(alpha,.001),alpha);
