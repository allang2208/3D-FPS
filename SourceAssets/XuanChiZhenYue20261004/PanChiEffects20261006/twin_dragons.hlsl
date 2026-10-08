float t = saturate(Age);
float fade = smoothstep(0,.12,t)*(1-smoothstep(.58,1,t));
float travel = smoothstep(0,.86,t);
float2 p = float2(UV.x,(UV.y-.5)*2);
float2 end = float2(Converge.x,(Converge.y-.5)*2);
float3 color = 0;
float alpha = 0;
[unroll] for(int i=0;i<2;i++)
{
    float side = i==0?-1:1;
    float2 start = float2(.57,side*.72);
    float2 dir = normalize(end-start+float2(.0001,0));
    float2 right = float2(-dir.y,dir.x);
    float2 head = lerp(start,end,travel)+right*(side*.11*sin(travel*3.14159));
    float2 relative = p-head;
    float2 uv = float2(dot(relative,dir)/.64+.88,dot(relative,right)/.31+.5);
    if(i==1)uv.y=1-uv.y;
    float inside = step(0,uv.x)*step(uv.x,1)*step(0,uv.y)*step(uv.y,1);
    float4 dragon = Texture2DSample(Dragon,DragonSampler,saturate(uv));
    float a = dragon.a*inside*fade*.68;
    float3 tint = i==0?float3(1,.57,.13):float3(.86,.73,.34);
    color += dragon.rgb*tint*a*2.4;
    alpha = max(alpha,a);
}
// The mask has true alpha; feather the patch border as well.
float border = smoothstep(0,.045,UV.x)*(1-smoothstep(.955,1,UV.x))*smoothstep(0,.04,UV.y)*(1-smoothstep(.96,1,UV.y));
return float4(color*border,alpha*border);
