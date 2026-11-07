// UV.x is the baked cut progression; Mask already carries reveal, edge and fade.
float v = UV.y;
float rim = exp2(-310.0*(v-.72)*(v-.72));
float echo = exp2(-580.0*(v-.39)*(v-.39));
float threads = pow(.5+.5*cos(77.*v+2.*sin(6.28*UV.x)),8.);
return Mask*(float3(1.70,.55,.055)*(.52+.48*threads)
           + float3(5.0,2.55,.39)*rim + float3(2.0,.86,.12)*echo);
