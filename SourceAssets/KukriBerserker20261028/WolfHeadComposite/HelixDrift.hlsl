        // Reuse the existing 22 wisp slots. Each is born ON the rotating helix,
        // then leaves it with outward drift, buoyant rise and a soft fade.
        float lifetime=2.6+seed*1.8;
        float cycle=Age/lifetime+Fn.Hash(mote*31.2);
        float life=frac(cycle);
        float birthTime=Age-life*lifetime;
        float birthSeed=Fn.Hash(mote*13.9+floor(cycle)*7.31);
        float birthAlpha=lerp(.08,.92,birthSeed)*amax;
        float birthTheta=birthAlpha+birthTime*.45;
        float2 anchor=float2(HudCenter-HudRibbon.x*sin(birthTheta),HudRibbon.w+helixPitch*birthAlpha);
        float outward=-sin(birthTheta);
        float driftX=outward*(28.0+seed*30.0);
        float rise=30.0+birthSeed*50.0;
        float sway=Age*(.85+seed*.4)+phase;
        pos=anchor+float2(driftX*life+5.0*sin(sway)*life,-rise*life+4.0*sin(sway*.7)*life);
        velocity=float2(driftX/lifetime+4.0*cos(sway)*life,-rise/lifetime);
        visibility=Fn.SS(0.0,.16,life)*Fn.SS(1.0,.55,life);
        visibility*=cos(birthTheta)>=0.0?1.0:.42*(1.0-.60*sil);
