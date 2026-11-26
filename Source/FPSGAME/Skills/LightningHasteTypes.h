#pragma once
#include "CoreMinimal.h"
#include "LightningHasteTypes.generated.h"

struct FLightningHasteTuning
{
    float MoveBase=.10f,MovePerLevel=.01f,ActionBase=.05f,ActionPerLevel=.005f;
    float DurationBase=20,DurationPerLevel=.5f,ManaBase=40,ManaPerLevel=2,Cooldown=50;
    int32 CastExperience=1,KillExperience=3,Kill6Bonus=15,Kill11Bonus=40;
};

USTRUCT()
struct FLightningHasteCast
{
    GENERATED_BODY()
    UPROPERTY() float MoveBonus=.1f;
    UPROPERTY() float ActionBonus=.05f;
    UPROPERTY() float Duration=20;
    UPROPERTY() float ManaCost=40;
    UPROPERTY() float Cooldown=50;
    UPROPERTY() float CastSpeed=1;
    UPROPERTY() int32 CastExperience=1;
    UPROPERTY() int32 KillExperience=3;
    UPROPERTY() int32 Kill6Bonus=15;
    UPROPERTY() int32 Kill11Bonus=40;
};

USTRUCT()
struct FLightningHasteState
{
    GENERATED_BODY()
    UPROPERTY() FLightningHasteCast Cast;
    UPROPERTY() double StartedAt=0;
    UPROPERTY() uint32 CastId=0;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() bool bActive=false;
};

namespace LightningHasteAssets
{
inline constexpr const TCHAR* Arc=TEXT("/Game/Skills/LightningHaste20261019/NS_LightningHasteArc.NS_LightningHasteArc");
inline constexpr const TCHAR* CastSound=TEXT("/Game/Skills/ElectricMagic/S_ElectricCast1.S_ElectricCast1");
inline constexpr const TCHAR* EndSound=TEXT("/Game/Skills/ElectricMagic/S_ElectricCast2.S_ElectricCast2");
}
