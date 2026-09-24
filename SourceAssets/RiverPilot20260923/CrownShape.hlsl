float phase=Variant*6.2831853;
float y=1-UV.y;
float x=UV.x-.5;
float sway=sin(y*8+phase+Age*4)*y*.035;
float width=.075+.43*sqrt(saturate(y));
float edge=smoothstep(0,.055,width-abs(x+sway));
float rim=.68+.09*sin(UV.x*27+phase)+.055*sin(UV.x*61-phase*1.7);
float lip=exp(-pow((y-rim+.045)/.055,2));
float ribs=.5+.5*sin(UV.x*47+sin(y*11+phase)*1.5+phase);
float breakup=.5+.5*sin(UV.x*39+phase)*sin(y*31-Age*7-phase);
// Keep a readable body; breakup modulates its density rather than erasing it.
float holes=.72+.28*smoothstep(.10+Age*.18,.44+Age*.18,breakup);
float thickness=saturate((.70+.12*ribs)*holes+.16*lip);
float bottom=smoothstep(0,.065,y);
float top=1-smoothstep(rim-.025,rim+.055,y);
return saturate(edge*bottom*top*thickness*Alpha);
