// Original ward implementation inspired by NDD's authored-fragment/WPO split.
// UV1 = normalized pane-space centroid; UV2.x = a per-fragment seed.
// Cosmetic flight/bounce only: gameplay collision belongs to the intact pane.
struct WardShardMath
{
    float H(float n){return frac(sin(n*127.13+13.7)*43758.5453);}
    float3 Rotate(float3 p,float3 axis,float angle)
    {float s=sin(angle),c=cos(angle);return p*c+cross(axis,p)*s+axis*dot(axis,p)*(1-c);}
};
WardShardMath F;
float seed=Shard.x*71.91;
float3 X=normalize(cross(PaneY,PaneZ));
float3 center=PaneOrigin+PaneY*((CenterUV.x-.5)*PaneSize.x)+PaneZ*((CenterUV.y-.5)*PaneSize.y);
float3 rel=Position-center;
float distanceToHit=length(center-HitPoint);
float t=max(0,Clock-Born-.012-distanceToHit/3200);
float impact=lerp(.4,1,exp(-distanceToHit/180));
float3 axis=normalize(X*(F.H(seed+1)-.5)+PaneY*(F.H(seed+2)-.5)+PaneZ*(F.H(seed+3)-.5));
float3 radial=(center-HitPoint)/max(15,distanceToHit);
float3 velocity=ShotDirection*(150+F.H(seed+4)*240)*impact+radial*(35+F.H(seed+5)*70)+axis*32;
velocity.z+=18+F.H(seed+6)*45;
float height=max(1,center.z-FloorZ-1);
float flight=(velocity.z+sqrt(velocity.z*velocity.z+1960*height))/980;
float air=min(t,flight);
float grounded=max(0,t-flight);
float bounce=min(110,abs(velocity.z-980*flight)*.16);
float bounceTime=2*bounce/980;
float settle=smoothstep(0,bounceTime+.16,grounded);
float3 movingCenter=center+velocity*air-float3(0,0,490*air*air);
if(t>flight)
{
    movingCenter.xy+=velocity.xy*.18*(1-exp(-grounded*5));
    movingCenter.z=FloorZ+1+max(0,bounce*grounded-490*grounded*grounded);
}
float angle=t*(3+F.H(seed+7)*11);
float flatAngle=F.H(seed+8)*6.283185;
float2 flatY=float2(cos(flatAngle),sin(flatAngle));
float2 flatZ=float2(-flatY.y,flatY.x);
if(Mode>.5)
{
    float3 rotated=F.Rotate(Normal,axis,angle);
    float3 flat=float3(flatY*dot(Normal,PaneY)+flatZ*dot(Normal,PaneZ),dot(Normal,X));
    return normalize(lerp(rotated,flat,settle));
}
float3 rotated=F.Rotate(rel,axis,angle);
float3 flat=float3(flatY*dot(rel,PaneY)+flatZ*dot(rel,PaneZ),dot(rel,X));
return movingCenter+lerp(rotated,flat,settle)-Position;
