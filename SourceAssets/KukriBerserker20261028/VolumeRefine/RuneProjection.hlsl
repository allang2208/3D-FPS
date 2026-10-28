// Local centimeters, one common scale in X/Z, exact source-image aspect.
// UV0 belongs exclusively to the existing blade PBR textures.
float s=sin(Center.z),c=cos(Center.z);
float2 p=LocalPos.xz-Center.xy;
float2 uv=float2((p.x*c-p.y*s)/Extent.x+.5,.5-(p.x*s+p.y*c)/Extent.y);
float inside=step(0,uv.x)*step(uv.x,1)*step(0,uv.y)*step(uv.y,1);
float3 face=normalize(cross(ddx(LocalPos),ddy(LocalPos))+1e-12);
float planar=smoothstep(.93,.98,abs(face.y));
float4 sigil=Texture2DSample(Glyph,GlyphSampler,saturate(uv));
float ink=dot(sigil.rgb,float3(.333333,.333333,.333333))*sigil.a;
return smoothstep(.25,.76,ink)*inside*planar;
