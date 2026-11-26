#include "MagicArrowRainGround.h"
#include "BlizzardEnvironment.h"
#include "MeteorGround.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"

FVector MagicArrowRainGround::Flight(const FVector& Start,const FVector& Burst,float Fraction)
{return FMath::Lerp(Start,Burst,Fraction)+FVector(0,0,60.f*FMath::Sin(PI*Fraction));}

namespace
{
bool FlightClearance(APawn* Pawn,const FMagicArrowRainCast& Cast,const FVector& Start,
    FVector& Ground,FVector& Normal,FVector& Burst,FString& Failure)
{
    FHitResult Roof;
    float Height=Cast.BurstHeight;
    if(BlizzardEnvironment::Trace(Pawn,Ground+FVector(0,0,8),Ground+FVector(0,0,Height+65),Roof,true))
        Height=FMath::Min(Height,float(Roof.ImpactPoint.Z-Ground.Z)-65.f);
    if(Height<Cast.MinimumHeight){Failure=TEXT("上方空间不足");return false;}
    Burst=Ground+FVector(0,0,Height);
    FVector Previous=Start;
    for(int32 I=1;I<=20;++I)
    {
        const FVector Next=MagicArrowRainGround::Flight(Start,Burst,float(I)/20.f);FHitResult Hit;
        if(BlizzardEnvironment::Trace(Pawn,Previous,Next,Hit,true))
        {Failure=TEXT("引导箭路径被遮挡");return false;}
        Previous=Next;
    }
    return true;
}
}

bool MagicArrowRainGround::Validate(APawn* Pawn,const FMagicArrowRainCast& Cast,const FVector& Start,
    FVector& Ground,FVector& Normal,FVector& Burst,FString& Failure)
{
    return MeteorGround::Validate(Pawn,Cast.Range,Ground,Normal,true,Failure)&&
        FlightClearance(Pawn,Cast,Start,Ground,Normal,Burst,Failure);
}

bool MagicArrowRainGround::Select(APawn* Pawn,const FMagicArrowRainCast& Cast,const FVector& Eye,const FVector& Aim,
    FVector& Ground,FVector& Normal,FVector& Burst,FString& Failure,const FVector* LaunchOrigin)
{
    Failure.Reset();FVector Axis=FVector::RightVector;
    if(!BlizzardEnvironment::Select(Pawn,Cast.Range,Eye,Aim,Ground,Normal,Axis,Failure))return false;
    // The camera selects the ground; the arrow tip determines flight clearance.
    // Select already checked floor/range/sight; do not repeat those traces.
    return FlightClearance(Pawn,Cast,LaunchOrigin?*LaunchOrigin:Eye,Ground,Normal,Burst,Failure);
}
