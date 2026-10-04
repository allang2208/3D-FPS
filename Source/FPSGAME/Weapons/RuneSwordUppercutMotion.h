#pragma once
#include "CoreMinimal.h"

// Uppercut animation authoring reads these frames too. The skill keeps its own
// fixed clock; weapon attack-speed stats do not change the release or stride.
namespace RuneSwordUppercutMotion
{
    inline constexpr int32 SampleRate=120;
    inline constexpr int32 ReleaseFrame=120;
    inline constexpr int32 StrokeEndFrame=129;
    inline constexpr int32 FinishFrame=135;
    inline constexpr int32 RecoveryStartFrame=152;
    inline constexpr int32 EndFrame=246;
    inline constexpr float ReleaseStart=float(ReleaseFrame)/SampleRate;
    inline constexpr float StrokeEnd=float(StrokeEndFrame)/SampleRate;
    inline constexpr float Finish=float(FinishFrame)/SampleRate;
    inline constexpr float RecoveryStart=float(RecoveryStartFrame)/SampleRate;
    inline constexpr float End=float(EndFrame)/SampleRate;
    inline constexpr float LungeEnd=ReleaseStart+.16f;
    // The active skill's blade crosses the forward aim at source frame 126.
    // Complete the stride there; a .16 s stride leaves most travel after contact.
    inline constexpr float SkillLungeEnd=ReleaseStart+6.f/SampleRate;
    inline constexpr float LungeDistance=150.f;

    inline float LungeAlpha(float Time,bool ActiveSkill=false)
    {
        return FMath::SmoothStep(ReleaseStart,ActiveSkill?SkillLungeEnd:LungeEnd,Time);
    }

    // Camera-local cm/degrees, before the existing sword and comfort scales.
    // This is one release/arrest impulse, independent of confirmed-hit shakes.
    inline void Camera(float Time,bool Stepping,FVector& Location,FRotator& Rotation,bool ActiveSkill=false)
    {
        // Camera-local +Y is right. Gather down/right, then whip up/left on
        // the same 75 ms release as the blade; never change the control aim.
        constexpr float SweepStrength=1.5f;
        const FVector Load=FVector(-1.5f,2.4f,-2.1f)*SweepStrength;
        const FVector Follow=FVector(3.f,-2.8f,2.8f)*SweepStrength;
        const FRotator LoadTurn=FRotator(-3.2f,3.4f,1.0f)*SweepStrength;
        const FRotator FollowTurn=FRotator(5.4f,-4.6f,-1.8f)*SweepStrength;
        if(Time<=ReleaseStart)
        {
            const float Gather=FMath::SmoothStep(0.f,ReleaseStart,Time);
            Location=Load*Gather;Rotation=LoadTurn*Gather;
        }
        else if(Time<=StrokeEnd)
        {
            const float Up=FMath::SmoothStep(ReleaseStart,StrokeEnd,Time);
            Location=FMath::Lerp(Load,Follow,Up);
            Rotation=FMath::Lerp(LoadTurn,FollowTurn,Up);
        }
        else
        {
            // Keep the follow-through through the arrest, then settle with
            // the supported recovery instead of snapping the view back early.
            const float Settle=1.f-FMath::SmoothStep(Finish,End-.10f,Time);
            Location=Follow*Settle;Rotation=FollowTurn*Settle;
            const float Age=Time-StrokeEnd;
            const float Envelope=1.f-FMath::SmoothStep(0.f,.20f,Age);
            const float Arrest=FMath::Square(FMath::Sin(PI*FMath::Clamp(Age/.10f,0.f,1.f)));
            const float Rattle=FMath::Sin(Age*92.f)*FMath::Exp(-22.f*Age)*Envelope;
            Location.Z+=.8f*Arrest;Location.Y-=.35f*Arrest;
            Rotation.Pitch+=1.35f*Arrest+1.5f*Rattle;
            Rotation.Yaw-=.75f*Arrest+.6f*Rattle;
            Rotation.Roll+=.5f*Rattle;
        }
        if(Stepping)
        {
            const float StepEnd=ActiveSkill?SkillLungeEnd:LungeEnd;
            const float Step=FMath::Clamp((Time-ReleaseStart)/(StepEnd-ReleaseStart),0.f,1.f);
            const float Transfer=FMath::Square(FMath::Sin(PI*Step));
            Location.Z-=1.6f*Transfer;
            const float Land=FMath::Clamp((Time-StepEnd)/.14f,0.f,1.f);
            const float Plant=FMath::Square(FMath::Sin(PI*Land))*(1.f-Land);
            Location.Z-=1.5f*Plant;Rotation.Pitch-=.65f*Plant;
        }
    }
}
