
float a=sin(UV.x*18.84956+T*8.1+sin(UV.y*12.56637-T*3.4));
float b=sin(UV.y*18.84956-T*6.2)*sin(UV.x*12.56637+T*2.7);
return Normal*Amplitude*(a*.65+b*.35);

