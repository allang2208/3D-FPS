// Zhenmo mode 8: approved BladeTalismanV4 brushwork and width-correct Bagua seal.
if (RuneMode > 7.5 && RuneMode < 8.5)
{
    float3 axis=normalize(BladeAxis.xyz);
    float3 offset=P.xyz-BladeOrigin.xyz;
    float along=dot(offset,axis);
    // Viewed from either face with the tip up, U runs from left to right.
    float3 widthAxis=cross(axis,normalize(N.xyz));
    widthAxis*=rsqrt(max(dot(widthAxis,widthAxis),.0001));
    float2 uv=float2(.5+dot(offset,widthAxis)/Dimensions.x,1-(along-Dimensions.y)/Dimensions.z);
    float inside=smoothstep(0,.025,uv.x)*(1-smoothstep(.975,1,uv.x));
    inside*=smoothstep(0,.025,uv.y)*(1-smoothstep(.975,1,uv.y));
    inside*=1-smoothstep(Dimensions.x*.48,Dimensions.x*.56,length(offset-along*axis));
    // Sample the approved 724x2172 image directly, retaining every brush stroke.
    // Crop black side margins in UVs. The seal's source-pixel aspect is preserved
    // for every blade width/length; the two surrounding strips fill the blade.
    float sourceTop=12./2172.;
    float sourceBottom=2142./2172.;
    float sourceCenter=1765./2172.;
    float sourceHalf=165./2172.;
    float centerV=.78;
    float physicalHalfV=165./380.*Dimensions.x/Dimensions.z;
    float v=uv.y;
    if(abs(v-centerV)<physicalHalfV)v=sourceCenter+(v-centerV)*sourceHalf/physicalHalfV;
    else if(v<centerV)v=lerp(sourceTop,sourceCenter-sourceHalf,v/max(centerV-physicalHalfV,.001));
    else v=lerp(sourceCenter+sourceHalf,sourceBottom,(v-centerV-physicalHalfV)/max(1-centerV-physicalHalfV,.001));
    float2 artworkUV=float2((361.5+(uv.x-.5)*380.)/724.,saturate(v));
    float ink=Texture2DSample(RuneTexture,RuneTextureSampler,artworkUV).r;
    ink=saturate((ink-.025)/.85);
    float time=PreviewTime>=0?PreviewTime:T;
    float breath=.5+.5*sin(time*.85-along*.027);
    float current=pow(saturate(.5+.5*sin(time*1.2-along*.12)),6);
    float3 gold=lerp(float3(.88,.40,.045),float3(1.,.72,.23),current*.6);
    float brightness=.52+.18*breath+.18*current;
    return float4(gold*brightness,ink*inside*RuneOpacity);
}
