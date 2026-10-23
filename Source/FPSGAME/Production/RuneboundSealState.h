#pragma once
#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"
#include "RuneboundSealState.generated.h"

/** Persistent seals travel as state so a newly relevant replica can recover them. */
USTRUCT()
struct FRuneboundReplicatedSeal
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target=nullptr;
    UPROPERTY() FVector_NetQuantize10 LocalPoint=FVector::ZeroVector;
    UPROPERTY() double Started=0.;
    UPROPERTY() double Expires=0.;
};

USTRUCT()
struct FRuneboundSealSnapshot
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() TArray<FRuneboundReplicatedSeal> Marks;
};
