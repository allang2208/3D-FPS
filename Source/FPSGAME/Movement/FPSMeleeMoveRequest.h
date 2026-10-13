#pragma once
#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"

enum class EFPSMeleeMove : uint8 {None,Thrust,Pommel,OverheadFinisher,Uppercut,RisingDragon,Dash,AirMomentum};
struct FFPSMeleeMoveRequest
{
    uint32 Sequence=0;
    EFPSMeleeMove Kind=EFPSMeleeMove::None;
    FVector_NetQuantizeNormal Direction=FVector::ZeroVector;
    float Distance=0.f; // cumulative accepted local sweep, replayed once on authority
    FVector_NetQuantize10 Momentum=FVector::ZeroVector;
};
