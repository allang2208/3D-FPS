#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsMultiplayerClosure.generated.h"

/** Opt-in, isolated-profile transport probe. Uses the production controllers and inventory RPCs. */
UCLASS()
class AHillsMultiplayerClosure : public AActor
{
    GENERATED_BODY()
public:
    AHillsMultiplayerClosure();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) int32 Command=0;
    UPROPERTY(Replicated) TObjectPtr<AActor> Subject;
    UPROPERTY(Replicated) FString ItemId;
    UPROPERTY(Replicated) FVector Place=FVector::ZeroVector;
    UPROPERTY(Replicated) double ExecuteAt=0.;
    UPROPERTY(Replicated) int64 ExpectedCount=-1;
    UFUNCTION(Server,Reliable) void ServerObserved(int32 Case,bool OK,const FString& Text,FGuid Id,int64 N);
    UFUNCTION(Client,Reliable) void ClientFinish(bool OK);
    int32 Observed=0;
    bool Passed=true;
    FString Detail;
    FGuid Identity;
    int64 Count=0;
private:
    int32 LastCommand=0;
    double Began=0.;
    double AssetsIdleAt=0.;
    bool Requested=false,Reported=false;
    TWeakObjectPtr<AActor> ObservedWolf;
};
