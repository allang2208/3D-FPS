#pragma once
#include "CoreMinimal.h"
#include "FPSPlayerBodyTypes.h"

/** Shared presentation clock; health/respawn remain server authoritative. */
namespace FPSPlayerDeathMotion
{
inline constexpr float RespawnSeconds=2.f;
inline constexpr float BlendSeconds=.18f;
inline constexpr float FadeStart=1.65f,FadeEnd=1.96f;
inline float FallSeconds(bool Crouched){return Crouched?1.2f:1.4f;}
inline void State(FFPSBodyState& Out,float StartedAt,bool Crouched)
{
    Out.Action=EFPSBodyAction::Dead;Out.ActionVariant=Crouched?TEXT("Crouched"):TEXT("Standing");
    Out.ActionStartedAt=StartedAt;Out.ActionDuration=RespawnSeconds;
    Out.bHasActionProgress=false;Out.Motion=EFPSBodyMotion::Ground;
    Out.bHasHandholds=false;Out.MotionHandContact=0.f;Out.Contacts=FFPSBodyMotionSample();
}
struct FCameraKey
{
    FVector Eye=FVector::ZeroVector;
    FRotator Rotation=FRotator::ZeroRotator;
};
}
