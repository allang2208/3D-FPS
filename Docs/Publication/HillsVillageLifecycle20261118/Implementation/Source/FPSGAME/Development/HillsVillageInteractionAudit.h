#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsVillageInteractionAudit.generated.h"

/** Opt-in real-transport fixture; never spawned during ordinary gameplay. */
UCLASS()
class AHillsVillageInteractionAudit : public AActor
{
    GENERATED_BODY()
public:
    AHillsVillageInteractionAudit();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) TObjectPtr<AActor> Target;
    UPROPERTY(Replicated) FVector Aim=FVector::ZeroVector;
    UFUNCTION(Server,Reliable) void ServerResult(int32 Case,bool OK,const FString& Text);
    UFUNCTION(Client,Reliable) void ClientFinish();
    int32 Observed=0;
    bool Passed=false;
    FString Detail;
private:
    int32 Previous=0;
    double Began=0.;
    bool Requested=false,Reported=false;
};
