// Original procedural lens droplets. UV is viewport space; center is undistorted.
float edge=max(abs(UV.x*2-1),abs(UV.y*2-1));
float guard=smoothstep(lerp(.72,.86,Aim),.98,edge);
float strength=guard*saturate(Strength)*lerp(1,.55,Aim);
if(strength<.0001 || Wet<.0001)return Scene.rgb;
float aspect=View.ViewSizeAndInvSize.x/View.ViewSizeAndInvSize.y;
float2 slope=0;float coverage=0;
[unroll] for(int layer=0;layer<2;layer++)
{
    float scale=layer==0?28:13;
    float2 q=UV*float2(scale*aspect,scale);
    q.y-=layer==1?Time*.095:0;
    float2 id=floor(q);
    float3 h=frac(sin(float3(dot(id,float2(127.1,311.7)),dot(id,float2(269.5,183.3)),dot(id,float2(419.2,371.9)))+layer*17)*43758.5453);
    float2 p=frac(q)-lerp(.26,.74,h.xy);
    float radius=lerp(.10,.24,h.z);
    float2 shape=p/float2(radius,radius*(layer==1?1.4:1.05));
    float r2=dot(shape,shape);
    float birth=smoothstep(h.z-.08,h.z+.08,Wet*.92);
    float bead=(1-smoothstep(.66,1,r2))*birth;
    slope+=shape*sqrt(saturate(1-r2))*bead*(layer==0?2.1:4.0);
    coverage=max(coverage,bead);
    if(layer==1)
    {
        float trail=exp(-p.x*p.x*7000)*smoothstep(.02,.12,p.y)*(1-smoothstep(.12,.48,p.y))*birth*.12;
        slope.x+=sin(p.x*250)*trail;
        coverage=max(coverage,trail);
    }
}
float2 bufferUV=GetDefaultSceneTextureUV(Parameters,14);
float2 offset=slope*InvSize*strength;
float3 refracted=SceneTextureLookup(clamp(bufferUV+offset,InvSize,1-InvSize),14,false).rgb;
float highlight=saturate(-slope.y)*.024-saturate(slope.y)*.010;
return lerp(Scene.rgb,refracted+highlight,coverage*strength);
