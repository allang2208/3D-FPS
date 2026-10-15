float edge=smoothstep(.22,.71,length(UV-.5));
float breathing=.90+.10*sin(Phase*4.8);
float strength=saturate(Strength)*edge*breathing;
float3 color=SceneColor.rgb*(1-.23*strength);
color+=float3(.014,.003,.021)*strength;
return color;
