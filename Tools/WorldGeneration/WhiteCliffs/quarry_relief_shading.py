"""Pixel-shader bodies for the placed quarry stone materials.

P is translated world position in centimetres and V points from the surface
to the camera. UV is the original stone UV for PARALLAX and its result for
GRAIN_NORMAL. HeightTex, GrainTex and the roughness inputs must be linear.

PARALLAX Tune = (peak-to-peak depth cm, max UV shift, height channel G vs R,
fade end cm). A centred, bounded ray serves both UV atlases and tiling stone.
GRAIN_NORMAL Tune = (grain strength, physical tile size cm, fade end cm,
original UV0 tiling; 0 means 1). A starting range for limestone is strength
0.4–0.95 and tile size 12–30 cm. The seal on the scan uses UV0 times three.
ROUGHNESS Tune = (dry roughness, wet roughness, scan contrast, pore lift).
Typical values fall in (0.72–0.88, 0.41–0.60, 0.50–0.95, 0.06–0.16).
"""


PARALLAX = r"""
float3 px = ddx(P), py = ddy(P);
float2 ux = ddx(UV), uy = ddy(UV);
float3 area = cross(px, py);
float areaSq = dot(area, area);
float fadeEnd = max(Tune.w, 1.0);
float proximity = 1.0 - smoothstep(0.43 * fadeEnd, fadeEnd, length(P));
[branch] if (proximity <= 0.0 || areaSq < 1.e-12) return UV;

float incidence = abs(dot(V, area) * rsqrt(areaSq));
float depth = Tune.x * proximity * smoothstep(0.10, 0.36, incidence);
// Express a one-cm change along the view tangent in the two screen-space
// surface derivatives. This handles mirroring, vertical faces and UV scale.
float a = dot(cross(V, py), area) / areaSq;
float b = dot(cross(px, V), area) / areaSq;
float2 travel = (a * ux + b * uy) * (depth / max(0.20, incidence));
float span = max(abs(travel.x), abs(travel.y));
travel *= min(1.0, 2.0 * Tune.y / max(span, 1.e-8));
[branch] if (span < 1.e-6 || Tune.y <= 0.0) return UV;

// Start half the depth above the authored plane and walk towards the rock.
// The original UV derivatives keep the height mip independent of ray steps.
float4 top = Texture2DSampleGrad(HeightTex, HeightTexSampler,
    UV + 0.5 * travel, ux, uy);
float previousGap = 1.0 - saturate(lerp(top.r, top.g, Tune.z));
float previousDepth = 1.0;
int steps = proximity > 0.6 ? 4 : 2;
[loop] for (int i = 1; i <= steps; ++i)
{
    float rayDepth = 1.0 - (float)i / (float)steps;
    float2 at = UV + (rayDepth - 0.5) * travel;
    float4 texel = Texture2DSampleGrad(HeightTex, HeightTexSampler, at, ux, uy);
    float gap = rayDepth - saturate(lerp(texel.r, texel.g, Tune.z));
    if (gap <= 0.0)
    {
        float mixHit = saturate(previousGap / max(previousGap - gap, 1.e-6));
        float hit = lerp(previousDepth, rayDepth, mixHit);
        return UV + (hit - 0.5) * travel;
    }
    previousDepth = rayDepth;
    previousGap = gap;
}
return UV;
"""


GRAIN_NORMAL = r"""
float tile = max(Tune.y, 1.0);
float3 px = ddx(P), py = ddy(P);
float end = max(Tune.z, 1.0);
float fade = 1.0 - smoothstep(0.35 * end, end, length(P));
// Mip filtering removes fine pores well before their normals alias.
float pixelCm = max(length(px), length(py));
fade *= 1.0 - smoothstep(tile * 0.035, tile * 0.17, pixelCm);
float3 area = cross(px, py);
float areaSq = dot(area, area);
[branch] if (fade <= 0.0 || areaSq < 1.e-12) return BaseN;

// All stone base samples take UV0; only the cap material tiles it by three.
// Convert the chief ray's UV shift back to a position on the surface so
// that grain follows the visible hit without crossing neighbouring UV islands.
float3 shift = 0.0;
#if NUM_TEX_COORD_INTERPOLATORS
float2 sourceUV = Parameters.TexCoords[0].xy * (Tune.w > 0.0 ? Tune.w : 1.0);
float2 ux = ddx(sourceUV), uy = ddy(sourceUV), delta = UV - sourceUV;
float det = ux.x * uy.y - ux.y * uy.x;
if (abs(det) > 1.e-12)
{
    shift = (px * (delta.x * uy.y - delta.y * uy.x) +
             py * (ux.x * delta.y - ux.y * delta.x)) / det;
    shift *= min(1.0, 1.25 / max(length(shift), 1.e-5));
}
#endif

// Unreal's periodic pre-view translation recovers a stable world projection
// at full near-camera precision, even when the viewpoint crosses tile edges.
float3 q = (P - GetPeriodicWorldOrigin(tile.xxx) + shift) / tile;
float3 dx = px / tile, dy = py / tile;
float3 w = saturate(abs(Parameters.TangentToWorld[2]) - 0.12);
w *= w;
w *= w;
w /= max(dot(w, float3(1, 1, 1)), 1.e-4);
float3 h;
h.x = Texture2DSampleGrad(GrainTex, GrainTexSampler, q.yz + float2(.13,.67), dx.yz, dy.yz).g;
h.y = Texture2DSampleGrad(GrainTex, GrainTexSampler, q.zx + float2(.47,.21), dx.zx, dy.zx).g;
h.z = Texture2DSampleGrad(GrainTex, GrainTexSampler, q.xy + float2(.72,.39), dx.xy, dy.xy).g;
// A projected height field gives the correct handedness on mirrored UVs.
// Differentiate the three heights before blending so that curved normals
// don't acquire a false ridge solely from a change in projection weights.
float hx = dot(ddx(h), w), hy = dot(ddy(h), w);
float3 slope = (cross(py, area) * hx + cross(area, px) * hy) / areaSq;
slope *= min(tile * 0.012, 0.24) * max(Tune.x, 0.0);
slope *= fade * min(1.0, 0.48 / max(length(slope), 1.e-5));
float2 ts = float2(dot(slope, Parameters.TangentToWorld[0]),
                   dot(slope, Parameters.TangentToWorld[1]));
float3 detail = normalize(float3(-ts, 1.0));
float3 t = BaseN + float3(0,0,1);
float3 u = detail * float3(-1,-1,1);
return normalize(t * (dot(t, u) / max(t.z, 1.e-4)) - u);
"""


ROUGHNESS = r"""
float wet = saturate(Wet);
float pore = 1.0 - smoothstep(0.18, 0.98, saturate(Occlusion));
float variance = clamp((saturate(MapR) - 0.75) * Tune.z, -0.18, 0.14);
float rock = lerp(Tune.x, Tune.y, wet) + variance * lerp(1.0, 0.85, wet);
// The existing finish already responds to weather. Preserve its broad
// variation once, then give sheltered pores a weaker wet highlight.
float result = lerp(rock, saturate(OldR), 0.20);
result += pore * Tune.w * lerp(0.40, 1.0, wet);
return clamp(result, 0.30, 0.97);
"""

# Broad fresh fractures often share a UV tile with the whole parent scan.
# Resolve break planes and small pits at the size of the detached stone.
BREAK_FIELD = r"""
float3 dx=ddx(P), dy=ddy(P);
float3 geom=Parameters.TangentToWorld[2];
float3 weight=abs(geom)/max(max(max(abs(geom.x),abs(geom.y)),abs(geom.z)),1.e-9);
weight=saturate((weight-.68)/.32);
weight*=weight;
weight/=max(dot(weight,float3(1,1,1)),1.e-6);
float fade=1.-smoothstep(580.,1350.,length(P));
[branch] if(fade<=0.) return float3(0.,0.,0.);
float tile=57.;
float3 q=(P-GetPeriodicWorldOrigin(tile.xxx))/tile;
dx/=tile; dy/=tile;
float relief=0.;
float3 gradient=0.;
[unroll] for(int i=0;i<3;++i){
    [branch] if(weight[i]>.001){
        float2 uv=i==0?q.yz:(i==1?q.xz:q.xy);
        float2 gx=i==0?dx.yz:(i==1?dx.xz:dx.xy);
        float2 gy=i==0?dy.yz:(i==1?dy.xz:dy.xy);
        float2 center=uv+.37;
        float2 sx=gx*1.45, sy=gy*1.45;
        float bedding=Texture2DSampleGrad(StoneTex,StoneTexSampler,center,sx,sy).g;
        float2x2 spin=float2x2(3.,1.,-1.,3.);
        float grain=Texture2DSampleGrad(StoneTex,StoneTexSampler,mul(spin,uv)+float2(.31,.72),mul(spin,sx),mul(spin,sy)).g;
        relief+=weight[i]*(.66*bedding+.34*grain);
        // A filtered difference taken in the rock surface itself is continuous
        // across render quads and independent of the screen's pixel-grid axes.
        float e=clamp(max(length(gx),length(gy)),.025,.12);
        float right=Texture2DSampleGrad(StoneTex,StoneTexSampler,center+float2(e,0.),sx,sy).g;
        float up=Texture2DSampleGrad(StoneTex,StoneTexSampler,center+float2(0.,e),sx,sy).g;
        float2 g=(float2(right,up)-bedding)*(.66*4.8/(e*tile));
        gradient+=weight[i]*(i==0?float3(0.,g.x,g.y):(i==1?float3(g.x,0.,g.y):float3(g,0.)));
    }
}
return float3(clamp((relief-.48)*4.8,-1.,1.),
              dot(gradient,Parameters.TangentToWorld[0]),
              dot(gradient,Parameters.TangentToWorld[1]))*fade;
"""

BREAK_NORMAL = r"""
float2 cutSlope=BreakDepth*BreakField.yz;
cutSlope*=min(1.,.64/max(length(cutSlope),.0001));
BaseN=normalize(float3(BaseN.xy-cutSlope*BaseN.z,BaseN.z));
"""
