float along=saturate(UV.x),theta=UV.y*6.2831853;
float eddy=sin(theta*5+along*18-Phase*24)+.5*sin(theta*9-along*31+Phase*17);
float ribbons=smoothstep(-.35,.75,eddy);
float edge=smoothstep(0,.12,along)*(1-smoothstep(.72,1,along));
float opacity=edge*(.13+.52*ribbons)*Alpha;
return float4(lerp(float3(.32,.34,.35),float3(.94,.97,.98),ribbons),saturate(opacity));
