#pragma once
#include "CoreMinimal.h"

namespace VillageOilMotion
{
    constexpr double Raise=.41, Release=.36, Empty=.84, Finish=1.31;
    // Front edge of the actual hand-pot rim (author_oil.py, r=14 cm).
    inline const FVector Lip(11.58,-7.74,6.58);

    // Cubic-out pickup with a subtle heavy-kettle settle overshoot at the end of Raise.
    inline double LiftCurve(double Age)
    {
        const double T=FMath::Clamp(Age/Raise,0.,1.);
        const double Base=1.-FMath::Pow(1.-T,3.);
        const double Over=FMath::Sin(UE_PI*FMath::SmoothStep(.45,1.,T))*.065*(1.-T);
        return FMath::Clamp(Base+Over,0.,1.06);
    }

    // Slow, heavy gather back toward the torso before lunging forward to pour.
    inline double AnticipationCurve(double Age)
    {
        return FMath::SmoothStep(0.,.15,Age)*(1.-FMath::SmoothStep(.15,.34,Age));
    }

    // Explosive quartic-out thrust forward/up into the pour, holding with light tremor, then crisp retract.
    inline double PushCurve(double Age)
    {
        const double In=FMath::SmoothStep(.12,.39,Age);
        const double Thrust=1.-FMath::Pow(1.-In,4.);
        const double Retract=FMath::SmoothStep(.84,1.15,Age);
        return Thrust*(1.-Retract);
    }

    // Non-linear pour tilt: slight backward gather, fast snap across Release, lively tail shake, brisk empty return.
    inline double Tip(double Age)
    {
        const double Gather=-.08*FMath::SmoothStep(0.,.11,Age)*(1.-FMath::SmoothStep(.11,.22,Age));
        const double SnapIn=FMath::Pow(FMath::SmoothStep(.11,.42,Age),.72);
        const double Shake=.075*FMath::Sin(UE_PI*FMath::Clamp((Age-.62)/.17,0.,1.))
            *FMath::SmoothStep(.60,.65,Age)*(1.-FMath::SmoothStep(.76,.82,Age));
        const double Return=1.-FMath::SmoothStep(Empty,1.09,Age);
        const double Settle=-.045*FMath::Sin(UE_PI*FMath::Clamp((Age-1.05)/.16,0.,1.))
            *FMath::SmoothStep(1.04,1.08,Age)*(1.-FMath::SmoothStep(1.18,1.24,Age));
        return FMath::Clamp(Gather+(SnapIn+Shake)*Return+Settle,-.10,1.08);
    }

    // Subtle pouring stream tremor while hot oil surges over the rim.
    inline double PourTremor(double Age)
    {
        const double Gate=FMath::SmoothStep(Release-.04,Release+.05,Age)*(1.-FMath::SmoothStep(Empty-.06,Empty+.04,Age));
        return Gate*(.65*FMath::Sin(Age*34.)+.35*FMath::Sin(Age*53.+1.1));
    }

    // Quadratic-in stow after the empty pot rotates back upright.
    inline double LowerCurve(double Age)
    {
        const double T=FMath::SmoothStep(.94,Finish,Age);
        return T*T;
    }

    inline double Fill(double Age){return 1.-FMath::SmoothStep(Release,Empty,Age);}
}
