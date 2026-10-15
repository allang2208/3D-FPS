float distanceCm=Layer.r<.5?0:(Layer.g<.5?18:55);
distanceCm=min(distanceCm,Radius*.45);
return -normalize(NormalWS)*distanceCm;
