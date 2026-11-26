#pragma once
#include "CoreMinimal.h"
#include "ProductionBluntComboTiming.h"

// The charged Pojun rune enters the opening cut at its loaded pose.
namespace PojunChixiao
{
    inline constexpr int32 OpeningStage=0;
    inline constexpr float Start=ProductionBluntComboTiming::HoldClip[OpeningStage];
    inline constexpr float Release=ProductionBluntComboTiming::ApexClip[OpeningStage];
    inline constexpr float Handoff=ProductionBluntComboTiming::ChainClip[OpeningStage];
}

namespace ProductionBluntCombo
{
    // Same post-recovery input window as the two-handed sword.
    inline constexpr double ResetSeconds=.85;
    inline constexpr float ExtraWindupSeconds=.15f;
    inline constexpr float ContactSeconds=.97f,SwingSeconds=1.75f;
    inline constexpr float HitRecoverSeconds=.80f;
    // Attack speed shortens the release and the miss brake by at most this
    // factor; load and settle absorb the rest, so a fast hammer still swings.
    inline constexpr float MaxProtectedRate=1.15f;
    inline double DamageMultiplier(int32 Stage){return Stage==2?1.25:1.;}
    inline FName Swing(int32 Stage)
    {
        return Stage==0?TEXT("Slash1"):Stage==1?TEXT("Slash2"):TEXT("Slash3");
    }
    inline FName Recovery(int32 Stage)
    {
        return Stage==0?TEXT("Slash1Recover"):Stage==1?TEXT("Slash2Recover"):TEXT("Slash3Recover");
    }
    inline constexpr const TCHAR* Clips[]={TEXT("Slash1"),TEXT("Slash2"),TEXT("Slash3"),
        TEXT("Slash1Recover"),TEXT("Slash2Recover"),TEXT("Slash3Recover")};

    // Like RuneSwordRhythm, load/release/brake/return have distinct speeds.
    // The extra 150 ms belongs to the load only; release and recovery keep
    // their original durations. Inventory timing drives the server contact too.
    inline float Hermite(float U,float StartSlope,float EndSlope)
    {
        U=FMath::Clamp(U,0.f,1.f);
        return (U*U*U-2*U*U+U)*StartSlope+(-2*U*U*U+3*U*U)+(U*U*U-U*U)*EndSlope;
    }
    // HeavyCharge still uses the accepted legacy load. Preserve its partial-
    // charge gameplay resume time; the grip-constrained entry fits the new cut.
    inline float ChargeResumeSourceTime(float Time,float Contact,float Duration)
    {
        constexpr float NewContact=.82f+ExtraWindupSeconds;
        constexpr float NewWindup=.70f+ExtraWindupSeconds;
        const float Clock=Time<=Contact?NewContact*Time/FMath::Max(.001f,Contact):
            NewContact+.78f*(Time-Contact)/FMath::Max(.001f,Duration-Contact);
        const float T=Clock<=NewWindup?Clock*.70f/NewWindup:Clock-ExtraWindupSeconds;
        struct FTimeKey{float Time,Source,Slope;};
        static constexpr FTimeKey Load[]={
            {0.f,0.f,0.f},{.12f,.009f,.13f},{.32f,.058f,.29f},
            {.50f,.128f,.37f},{.60f,.17f,.25f},{.68f,.188f,0.f}};
        if(T<=0.f)return 0.f;
        if(T<=.68f)
            for(int32 I=1;I<UE_ARRAY_COUNT(Load);++I)
                if(T<=Load[I].Time)
                {
                    const auto& A=Load[I-1];const auto& B=Load[I];
                    const float Span=B.Time-A.Time,Distance=B.Source-A.Source;
                    return A.Source+Distance*Hermite((T-A.Time)/Span,A.Slope*Span/Distance,B.Slope*Span/Distance);
                }
        if(T<=.70f)return .188f;
        if(T<=.82f)return .188f+.052f*(T-.70f)/.12f;
        if(T<=.93f)return .24f+.066785714f*Hermite((T-.82f)/.11f,1.4f,0.f);
        if(T<=.97f)return .306785714f;
        if(T<=1.24f)return .306785714f+.123214286f*Hermite((T-.97f)/.27f,0.f,1.2f);
        return .43f+.25f*Hermite((T-1.24f)/.36f,1.1f,0.f);
    }
    inline int32 SafeStage(int32 Stage){return FMath::Clamp(Stage,0,2);}
    inline float Hold(int32 Stage){return ProductionBluntComboTiming::HoldClip[SafeStage(Stage)];}
    inline float Apex(int32 Stage){return ProductionBluntComboTiming::ApexClip[SafeStage(Stage)];}
    inline float Turn(int32 Stage){return ProductionBluntComboTiming::TurnClip[SafeStage(Stage)];}
    inline float WhooshClip(int32 Stage){return ProductionBluntComboTiming::WhooshClip[SafeStage(Stage)];}
    // Real seconds of the protected downswing before contact. BaseContact is
    // the rate-1 contact time; clip and base time are proportional.
    inline float ReleaseReal(float RealContact,float BaseContact,float Rate,int32 Stage)
    {
        const float ClipToReal=BaseContact/ContactSeconds;
        return FMath::Min((ContactSeconds-Apex(Stage))*ClipToReal/FMath::Max(.01f,FMath::Min(Rate,MaxProtectedRate)),RealContact*.6f);
    }
    // Real attack age -> clip seconds of the V6 ordinary cut. At rate 1 the
    // load and release keep the contact-scaled clock; the miss brake keeps
    // that same scale so the hammer's speed is continuous through contact.
    // StartClip continues a visual chain that already played the first part
    // of this cut's load (same load speed).
    inline float ClipTime(float Real,float RealContact,float RealSwing,float BaseContact,float Rate,int32 Stage,float StartClip=0.f)
    {
        const float ApexClip=Apex(Stage);
        if(Real<=RealContact)
        {
            const float Release=ReleaseReal(RealContact,BaseContact,Rate,Stage);
            const float Load=FMath::Max(.001f,RealContact-Release);
            const float From=FMath::Clamp(StartClip,0.f,ApexClip);
            if(Real<=Load)return From+(ApexClip-From)*FMath::Max(0.f,Real)/Load;
            return ApexClip+(ContactSeconds-ApexClip)*(Real-Load)/FMath::Max(.001f,Release);
        }
        const float ClipToReal=BaseContact/ContactSeconds,TurnClip=Turn(Stage);
        const float Post=FMath::Max(.001f,RealSwing-RealContact);
        const float Brake=FMath::Min((TurnClip-ContactSeconds)*ClipToReal/FMath::Max(.01f,FMath::Min(Rate,MaxProtectedRate)),Post*.6f);
        const float U=Real-RealContact;
        if(U<=Brake)return ContactSeconds+(TurnClip-ContactSeconds)*U/FMath::Max(.001f,Brake);
        return TurnClip+(SwingSeconds-TurnClip)*FMath::Clamp((U-Brake)/FMath::Max(.001f,Post-Brake),0.f,1.f);
    }
    // Inverse of ClipTime before contact (swing sound).
    inline float RealForWindupClip(float Clip,float RealContact,float BaseContact,float Rate,int32 Stage,float StartClip=0.f)
    {
        const float ApexClip=Apex(Stage);
        const float Release=ReleaseReal(RealContact,BaseContact,Rate,Stage);
        const float Load=FMath::Max(.001f,RealContact-Release);
        const float From=FMath::Clamp(StartClip,0.f,ApexClip);
        if(Clip<=ApexClip)return Load*FMath::Clamp((Clip-From)/FMath::Max(.001f,ApexClip-From),0.f,1.f);
        return Load+Release*FMath::Clamp((Clip-ApexClip)/(ContactSeconds-ApexClip),0.f,1.f);
    }
    inline float HitSourceTime(float Age){return FMath::Clamp(Age,0.f,HitRecoverSeconds);}
    inline float Ease(float U){U=FMath::Clamp(U,0.f,1.f);return U*U*U*(10.f+U*(-15.f+6.f*U));}
    inline float Smooth(float U){U=FMath::Clamp(U,0.f,1.f);return U*U*(3.f-2.f*U);}
    // Slightly underdamped settle (about 8% overshoot) instead of a linear return.
    inline float Settle(float X){X=FMath::Max(0.f,X);return FMath::Exp(-6.5f*X)*(FMath::Cos(8.f*X)+6.5f/8.f*FMath::Sin(8.f*X));}
    // Body/camera effort on the cut's clip clock. Stage picks the V6 apex/turn.
    inline void Effort(float Time,bool Hit,float& Load,float& Follow,int32 Stage=0)
    {
        if(Hit)
        {
            const float Hold=ProductionBluntComboTiming::HitStopClip[SafeStage(Stage)]+.10f;
            Load=0.f;
            Follow=(Time<=Hold?1.f:Settle(Time-Hold))*(1.f-Smooth((Time-(HitRecoverSeconds-.14f))/.14f));
            return;
        }
        const float ApexClip=Apex(Stage);
        const float U=FMath::Clamp((Time-ApexClip)/(ContactSeconds-ApexClip),0.f,1.f);
        // V7 rhythm: full load through the tension beat, then an explosive cut
        // whose effort lands in the last frames before contact.
        const float Cut=U*U*U;
        Load=Ease(Time/Hold(Stage))*(1.f-Cut);
        Follow=Cut*(Time<=Turn(Stage)?1.f:Settle(Time-Turn(Stage)))*(1.f-Smooth((Time-(SwingSeconds-.14f))/.14f));
    }
    inline void SampleCamera(float Clock,int32 Stage,bool Hit,FVector& Position,FRotator& Rotation)
    {
        // The head/chest leads the arms by a few frames through load and cut.
        float Load,Follow;Effort(Hit?Clock:FMath::Min(Clock+.03f,SwingSeconds),Hit,Load,Follow,Stage);
        const float Side=Stage==0?1.f:Stage==1?-1.f:0.f;
        const bool Heavy=Stage==2;
        Position=FVector(-7.f,-Side*4.f,2.f)*Load+FVector(14.f,Side*8.f,-6.f)*Follow;
        Rotation=FRotator(5.f,-Side*6.f,-Side*4.f)*Load+FRotator(-6.f,Side*9.f,Side*7.f)*Follow;
        // One forward drive and a short damped contact impulse. The common
        // character camera scale still applies; ordinary cuts never aim-lock.
        const float Drive=Heavy?11.f:9.f;
        if(!Hit)
        {
            const float ApexClip=Apex(Stage),Beat=Hold(Stage)-.03f;
            // Anticipation: the gather tightens through the tension beat and
            // is released exactly as the downswing fires.
            const float Gather=FMath::Square(FMath::Sin(PI*FMath::Clamp((Clock-Beat)/FMath::Max(.02f,ApexClip+.01f-Beat),0.f,1.f)));
            Position.X-=2.5f*Gather;Rotation.Pitch+=1.2f*Gather;
            // The forward drive accelerates with the cut and peaks on contact;
            // a miss is braked with the swing-on.
            if(Clock>ApexClip)
            {
                const float U=FMath::Clamp((Clock-ApexClip)/(ContactSeconds-ApexClip),0.f,1.f);
                Position.X+=Drive*(Clock<=ContactSeconds?U*U:FMath::Exp(-(Clock-ContactSeconds)/.07f));
            }
            if(Heavy)
            {
                // The third cut commits its weight: a step-in dip that lingers past contact.
                const float Step=FMath::Square(FMath::Sin(PI*FMath::Clamp((Clock-ApexClip)/(ContactSeconds+.32f-ApexClip),0.f,1.f)));
                Position.X+=4.f*Step;Position.Z-=2.5f*Step;
            }
        }
        else
        {
            // Impact: the drive is stopped dead by the target (continuous with
            // the swing at contact), a shudder through the hit stop, a recoil kick.
            const float Strength=Heavy?1.4f:1.f;
            Position.X+=Drive*FMath::Exp(-Clock/.035f);
            const float Stop=ProductionBluntComboTiming::HitStopClip[SafeStage(Stage)]+.05f;
            if(Clock<Stop)
            {
                const float Shudder=FMath::Sin(2.f*PI*27.f*Clock)*FMath::Exp(-Clock/.05f)*Strength;
                Rotation.Pitch+=.7f*Shudder;Rotation.Roll+=Side*.5f*Shudder;Position.Z+=.4f*Shudder;
            }
            if(Clock<.18f)
            {
                const float Kick=FMath::Exp(-24.f*Clock)*FMath::Sin(66.f*Clock)*(1.f-Ease(Clock/.18f))*1.6f*Strength;
                Position.X-=3.f*Kick;Rotation.Pitch-=2.2f*Kick;Rotation.Roll+=Side*1.5f*Kick;
            }
        }
    }
}
