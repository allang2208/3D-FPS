#pragma once
#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"
#include "FPSBodyReactionState.generated.h"

/** Server-written presentation events. They never apply damage or displacement. */
USTRUCT()
struct FFPSBodyReactionState
{
    GENERATED_BODY()
    UPROPERTY() uint16 HitSerial=0;
    UPROPERTY() float HitAt=-100.f;
    UPROPERTY() float HitStrength=0.f;
    UPROPERTY() FVector_NetQuantizeNormal HitDirection=FVector::BackwardVector;
    UPROPERTY() bool bStunned=false;
    UPROPERTY() float StunAt=0.f;
    UPROPERTY() uint16 PushSerial=0;
    UPROPERTY() float PushAt=-100.f;
    UPROPERTY() float PushSeconds=.5f;
    UPROPERTY() float PushStrength=0.f;
    UPROPERTY() FVector_NetQuantizeNormal PushDirection=FVector::BackwardVector;
};
