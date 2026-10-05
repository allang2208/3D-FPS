#pragma once
#include <algorithm>

// Source-animation seconds, never a second wall-clock playback timer.
// The hooked V9 gesture gathers during windup, then rakes inside the contact window.
namespace AzureDragonStrikeClock
{
struct Pose { float Sweep=0.f,Grab=0.f,Reveal=0.f; bool Visible=false; };
inline float Unit(float V){return std::clamp(V,0.f,1.f);}
inline float Ease(float V){V=Unit(V);return V*V*(3.f-2.f*V);}
inline Pose Contact(float Source,float Start,float End)
{
    Pose P;
    const float Span=std::max(.001f,End-Start);
    const float Lead=std::min(.12f,std::max(0.f,Start));
    const float Tail=.12f;
    if(Source<Start-Lead||Source>=End+Tail)return P;
    P.Visible=true;
    P.Sweep=Unit((Source-Start)/Span);
    if(Source<Start)
    {
        const float U=Unit((Source-Start+Lead)/std::max(.001f,Lead));
        P.Grab=(11.f/36.f)*U;P.Reveal=Ease(U);
    }
    else if(Source<=End)
    {
        // Frame 11 is gathered already; frame 20 adds the strongest hooked rake.
        P.Grab=(11.f+16.f*P.Sweep)/36.f;P.Reveal=1.f;
    }
    else
    {
        const float U=Unit((Source-End)/Tail);
        P.Grab=.75f+.25f*U;P.Reveal=1.f-Ease(U);
    }
    return P;
}
inline Pose Revolution(float Phase)
{
    Pose P;
    if(Phase<=0.f||Phase>=1.f)return P;
    const float Turn=Phase<.5f?Phase*2.f:(Phase-.5f)*2.f;
    P.Visible=true;P.Sweep=Turn;P.Grab=Turn;
    P.Reveal=Ease(Turn/.08f)*(1.f-Ease((Turn-.88f)/.12f));
    return P;
}
}
