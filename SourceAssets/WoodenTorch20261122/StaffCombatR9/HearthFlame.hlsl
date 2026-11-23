// Inward-facing proxy. Clip the optical path to the nearest opaque surface, including the fuel.
float3 ray = normalize(LocalExit - LocalEye);
float3 invRay = rcp(float3(ray.x >= 0 ? max(ray.x,1.e-5) : min(ray.x,-1.e-5),
                           ray.y >= 0 ? max(ray.y,1.e-5) : min(ray.y,-1.e-5),
                           ray.z >= 0 ? max(ray.z,1.e-5) : min(ray.z,-1.e-5)));
float3 a=(float3(-16.5,-16.5,-2.)-LocalEye)*invRay;
float3 b=(float3(16.5,16.5,40.5)-LocalEye)*invRay;
float3 enter=min(a,b);
float first=max(0.,max(enter.x,max(enter.y,enter.z)));
float extent=length(LocalExit-LocalEye);
float last=min(extent,BehindDepth*extent/max(.01,ExitDepth));
if(last<=first) return 0.;

float2 up=clamp(UpLocal.xy/max(UpLocal.z,.60),-.58,.58);
// Restrict the march to a tilted cylinder around the plume. Empty box corners otherwise
// take samples away from the thin luminous folds, particularly on an oblique view.
float2 slope=up*.84;
float2 origin=LocalEye.xy-slope*(LocalEye.z-8.);
float2 axis=ray.xy-slope*ray.z;
float qa=dot(axis,axis), qb=dot(origin,axis), qc=dot(origin,origin)-12.9*12.9;
if (qa>1.e-5) {
    float disc=qb*qb-qa*qc;
    if(disc<=0.) return 0.;
    float halfChord=sqrt(disc);
    first=max(first,(-qb-halfChord)/qa);
    last=min(last,(-qb+halfChord)/qa);
    if(last<=first) return 0.;
}
float t=1.8*TimeSeconds+Phase;
int steps=clamp((int)ceil((last-first)*1.0),6,20);
float dx=(last-first)/steps;
float trans=1.;
float3 light=0.;
[loop] for(int i=0;i<steps;++i) {
    float3 p=LocalEye+ray*(first+(i+.5)*dx);
    float z=p.z;
    if(z<.25 || z>39.) continue;
    float free=smoothstep(8.,29.,z);
    float lift=t-z*.062;
    float2 centre=up*max(z-8.,0.)*.84 + 1.35*free*float2(
        2.65*sin(2.8*lift)+1.18*sin(4.45*lift+.7),
        2.05*sin(2.46*lift+1.1)+.98*cos(4.1*lift));
    float2 xy=p.xy-centre;
    float dist=length(xy);
    float radius=(3.35+3.0*smoothstep(.8,6.2,z))*(1.-.80*smoothstep(11.,39.,z));
    if(dist>radius+3.25) continue;
    // The stretched, upward-moving field wrinkles thin burning sheets without boiling the whole core.
    float2 dir=xy/max(dist,.25);
    float spin=.25*sin(lift*2.1)+z*.038;
    float sn,cs;sincos(spin,sn,cs);
    float2 swirl=float2(cs*xy.x-sn*xy.y,sn*xy.x+cs*xy.y);
    float3 uvw=frac(float3(swirl*.044+float2(.018*t,-.013*t),z*.0165-t*.34));
    float slice=uvw.z*64.,k=floor(slice),kn=fmod(k+1.,64.);
    float2 uv=(1.5+uvw.xy*62.)/512.;
    float3 n=lerp(Texture2DSampleLevel(FlowTex,FlowTexSampler,float2(fmod(k,8.),floor(k/8.))*.125+uv,0).rgb,
                  Texture2DSampleLevel(FlowTex,FlowTexSampler,float2(fmod(kn,8.),floor(kn/8.))*.125+uv,0).rgb,frac(slice));
    float2 d=float2(cs*dir.x-sn*dir.y,sn*dir.x+cs*dir.y);
    float3 lobes=float3(d.x*(d.x*d.x-3.*d.y*d.y),2.*d.x*d.y,d.y);
    float lobed=dot(lobes,float3(.52,.28,.20));
    float folds=(n.r-.5)*4.6+(n.g-.5)*1.75;
    float edge=radius-dist+folds+lobed*lerp(.48,1.6,free);
    float tip=27.7+7.4*lobed+9.7*(n.g-.42)+3.4*sin(lift*2.2+.8)+1.9*sin(lift*3.7);
    float crown=1.-smoothstep(tip-3.8,tip+1.6,z);
    float base=smoothstep(.8,4.5,z+(n.r-.5)*4.7+lobed*1.6);
    float nested=edge-(2.75+.85*lobed+1.9*(n.b-.5));
    float sheet=exp2(-.98*(edge-.48)*(edge-.48));
    float inner=exp2(-1.12*nested*nested);
    float seams=smoothstep(.20,.79,.56*n.g+.44*n.b+.16*lobed);
    float mantle=smoothstep(-.53,.90,edge);
    float density=(.038*mantle+(.32+.65*seams)*sheet+inner*(.06+.66*seams))*base*crown;
    float presence=lerp(1.,smoothstep(.13,.66,n.r*.58+n.b*.42+.18*lobed+.14*sheet),free);
    float opacity=1.-exp(-dx*.35*density*presence);
    // Thin orange-red edges and hotter straw-colored folds, with open space between them.
    float heat=saturate(.10+.43*inner+.37*seams+.18*n.r-.13*free);
    float3 outer=float3(1.32,.084,.012);
    float3 amber=float3(4.65,.88,.062);
    float3 core=float3(8.4,3.4,.62);
    float3 col=lerp(lerp(outer,amber,smoothstep(.17,.56,heat)),core,smoothstep(.55,.90,heat));
    light+=trans*opacity*col;
    trans*=1.-opacity;
    if(trans<.015) break;
}
float alpha=1.-trans;
return float4(light/max(alpha,.001),alpha);
