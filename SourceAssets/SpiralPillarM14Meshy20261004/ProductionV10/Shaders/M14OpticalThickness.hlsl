// Bounded chord approximation for the 25 x 19 x 19 cm stretched liquid.
// Not a scene-depth subtraction: foreground/background objects cannot turn it opaque.
float x=clamp(P.x/50,-1,1);
float taper=lerp(.16,1.02,smoothstep(-.86,.10,x));
float section=sqrt(max(.035,1-x*x));
float facing=pow(saturate(1-Facing),.7);
float chord=19*taper*section*facing;
return max(.025,chord*lerp(.75,1.2,Flow.z));
