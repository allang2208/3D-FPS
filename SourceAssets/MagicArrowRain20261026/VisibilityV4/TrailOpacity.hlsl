// Engine cylinder: V follows its length. Soft silhouette, bright axial core.
float ends=smoothstep(0,.07,UV.y)*(1-smoothstep(.86,1,UV.y));
float face=abs(dot(normalize(Normal),normalize(View)));
float silhouette=smoothstep(.04,.55,face);
float core=pow(face,3);
float flow=.88+.12*sin((UV.y*3-T*7)*6.283185);
return saturate(ends*silhouette*(.23+.69*core)*flow);
