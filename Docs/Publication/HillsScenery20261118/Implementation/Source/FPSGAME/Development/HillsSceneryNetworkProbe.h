#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsSceneryNetworkProbe.generated.h"

UCLASS()
class AHillsSceneryNetworkProbe : public AActor
{
    GENERATED_BODY()
public:
    AHillsSceneryNetworkProbe();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) FVector Center=FVector::ZeroVector;
    UPROPERTY(Replicated) FString Expected;
    UPROPERTY(Replicated) TArray<FString> Harvested;
    UFUNCTION(Server,Reliable) void ServerResult(int32 Case,bool OK,const FString& ResultDetail);
    UFUNCTION(Client,Reliable) void ClientFinish(bool OK);
    int32 Observed=0;
    bool Passed=false;
    FString Detail;
private:
    int32 LastPhase=0;
    double Began=0.;
    double WalkStarted=0.;
    double NextHarvest=0.;
    bool Reported=false;
    bool Requested=false;
};
