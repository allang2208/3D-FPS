#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "EnhancementEscrowWireAudit.generated.h"
class AVoxelBuildWorld;
class AVoxelBuildPrefabActor;
class AFPSGAMECharacter;
class FJsonValue;
UCLASS()
class AEnhancementEscrowWirePlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    // Exercise real upload/request/reply transport without unrelated heartbeats.
    virtual void Tick(float Delta) override;
};
UCLASS()
class AEnhancementEscrowWireController : public APlayerController
{
    GENERATED_BODY()
    friend class AEnhancementEscrowWireGameMode;
public:
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) TObjectPtr<AVoxelBuildPrefabActor> Bench;
    UFUNCTION(Client,Reliable) void ClientPhase(int32 Phase,const TArray<uint8>& Seed);
    UFUNCTION(Server,Reliable) void ServerResult(int32 Phase,bool OwnerPass,int64 OwnerRevision,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientPlantState(int32 Index,const FColdSteelPlantingNetState& State,bool Changed);
    UFUNCTION(Server,Reliable) void ServerPlantResult(int32 Index,bool OK);
    UFUNCTION(Client,Reliable) void ClientFinish(bool OK);
    int32 Finished=-1,PlantFinished=0;
    bool Passed=true;
private:
    void Receipt(bool Success,const FString& Message);
    int32 Current=-1,Requested=-1,Receipts=0;
    bool Sent=false,Reported=false,ReceiptSuccess=false,Bound=false;
    double Started=0,ExitAt=-1;
    FString Notice;
    TArray<uint8> Fixture;
};
UCLASS()
class AEnhancementEscrowWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AEnhancementEscrowWireGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Logout(AController* Controller) override;
    virtual void Tick(float Delta) override;
    void Record(int32 Phase,bool Pass,bool OwnerPass,int64 OwnerRevision,const FString& Detail);
private:
    void BeginPhase(int32 Phase);
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> Building;
    UPROPERTY() TObjectPtr<AVoxelBuildPrefabActor> Bench;
    UPROPERTY() TObjectPtr<AEnhancementEscrowWireController> Guest;
    FColdSteelProfile WithSpace;
    TArray<TSharedPtr<FJsonValue>> Rows;
    int32 Connections=0,Prepared=-1;
    bool Passed=true,HostSeeded=false,AwaitingReconnect=false,Done=false;
    double Started=0,ExitAt=-1;
};
