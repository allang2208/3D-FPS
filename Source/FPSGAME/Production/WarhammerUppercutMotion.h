#pragma once
#include "../Weapons/RuneSwordUppercutMotion.h"

// Keep the sword's stride/contact/end clock. The hammer stays loaded through
// push-off, then spends its main angular travel around the planted foot.
// Pose, contact arc and camera all sample this same source-time mapping.
namespace WarhammerUppercutMotion
{
    inline constexpr float StrikeStart=RuneSwordUppercutMotion::SkillLungePlaybackEnd-.055f;
    inline constexpr float StrikeFinish=RuneSwordUppercutMotion::SkillLungePlaybackEnd+.050f;
    inline constexpr float LoadedSource=RuneSwordUppercutMotion::ReleaseStart+.008f;
    inline float Hermite(float Time,float A,float B,float From,float To,float VelocityA,float VelocityB)
    {
        const float Span=B-A,U=FMath::Clamp((Time-A)/Span,0.f,1.f);
        return (2*U*U*U-3*U*U+1)*From+(U*U*U-2*U*U+U)*Span*VelocityA+
            (-2*U*U*U+3*U*U)*To+(U*U*U-U*U)*Span*VelocityB;
    }
    inline float PoseTime(float PlaybackTime)
    {
        using namespace RuneSwordUppercutMotion;
        if(PlaybackTime<=ReleaseStart)return PlaybackTime;
        if(PlaybackTime<StrikeStart)
            return Hermite(PlaybackTime,ReleaseStart,StrikeStart,ReleaseStart,LoadedSource,0.f,.10f);
        if(PlaybackTime<SkillLungePlaybackEnd)
            return Hermite(PlaybackTime,StrikeStart,SkillLungePlaybackEnd,LoadedSource,SkillLungeEnd,.10f,1.5f);
        if(PlaybackTime<StrikeFinish)
            return Hermite(PlaybackTime,SkillLungePlaybackEnd,StrikeFinish,SkillLungeEnd,Finish,1.5f,1.f);
        const float RecoveryPlayback=SkillPlaybackTime(RecoveryStart);
        if(PlaybackTime<RecoveryPlayback)
            return Hermite(PlaybackTime,StrikeFinish,RecoveryPlayback,Finish,RecoveryStart,1.f,1.f);
        return SkillSourceTime(PlaybackTime);
    }
    inline void Camera(float PlaybackTime,bool Stepping,FVector& Location,FRotator& Rotation)
    {
        using namespace RuneSwordUppercutMotion;
        RuneSwordUppercutMotion::Camera(PoseTime(PlaybackTime),false,Location,Rotation,true);
        // Legs keep the original swept 0.28 s stride, independent of the
        // concentrated upper-body release. Preserve its foot-plant feedback.
        if(Stepping)
        {
            const float Step=FMath::Clamp((PlaybackTime-ReleaseStart)/SkillLungeSeconds,0.f,1.f);
            Location.Z-=1.6f*FMath::Square(FMath::Sin(PI*Step));
            const float Land=FMath::Clamp((PlaybackTime-SkillLungePlaybackEnd)/.14f,0.f,1.f);
            const float Plant=FMath::Square(FMath::Sin(PI*Land))*(1.f-Land);
            Location.Z-=1.5f*Plant;Rotation.Pitch-=.65f*Plant;
        }
    }
}
