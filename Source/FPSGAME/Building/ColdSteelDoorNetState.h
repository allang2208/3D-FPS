#pragma once
#include "CoreMinimal.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "ColdSteelDoorNetState.generated.h"

class UStaticMesh;

/** One authoritative transition, including the clock for relevancy/late join. */
USTRUCT()
struct FColdSteelDoorNetState
{
    GENERATED_BODY()
    UPROPERTY() bool bOpen=false;
    UPROPERTY() float From=0.f;
    UPROPERTY() float To=0.f;
    UPROPERTY() float Direction=1.f;
    UPROPERTY() float Speed=180.f;
    UPROPERTY() double StartedAt=0.;
    static double Now(const UWorld* World)
    {
        const auto* State=World?World->GetGameState():nullptr;
        return State?State->GetServerWorldTimeSeconds():(World?World->GetTimeSeconds():0.);
    }
    float Angle(const UWorld* World) const
    {return FMath::FInterpConstantTo(From,To,float(FMath::Max(0.,Now(World)-StartedAt)),Speed);}
};

/** Runtime leaf configuration used by generated ward rooms, not just the CDO. */
USTRUCT()
struct FColdSteelDoorLeafConfig
{
    GENERATED_BODY()
    UPROPERTY() bool bStandalone=false;
    UPROPERTY() TObjectPtr<UStaticMesh> Mesh=nullptr;
    UPROPERTY() bool bPositiveHinge=true;
    UPROPERTY() float OpeningSeconds=.55f;
    UPROPERTY() float ClosingDelay=6.f;
};
