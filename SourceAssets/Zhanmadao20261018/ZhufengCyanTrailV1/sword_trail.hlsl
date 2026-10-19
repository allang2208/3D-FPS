// Reuse Beiwei's thin blade-following ribbon, with Zhufeng's cyan/silver palette.
float age=saturate(UV.x),blade=saturate(UV.y);
float fade=pow(1-age,1.8);
float taper=smoothstep(0,.20,blade)*(1-smoothstep(.92,1,blade));
float threads=pow(.5+.5*sin(blade*71.+age*19.+sin(blade*23.-age*7.)),10.);
float core=exp(-pow((age-.055)*13.,2.));
float opacity=fade*taper*(.10+.14*core+.16*threads);
float3 cyan=lerp(float3(.015,.34,.42),float3(.38,.95,1.),saturate(core*.65+threads*.35));
return float4(cyan*(1.05+.55*core),opacity);
