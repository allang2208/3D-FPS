#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "ApartmentNetworkAudit.generated.h"
class AColdSteelSceneContainer;
class AColdSteelSlidingDoor;
class AApartmentDeviceControl;
class AFPSGAMECharacter;
class FJsonValue;

// Explicit isolated test mode; ordinary apartment gameplay never selects this mode.
UCLASS()
class AApartmentAuditPlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override {}
};
UCLASS()
class AApartmentAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION(Client,Reliable) void ClientStage(int32 Stage,AColdSteelSceneContainer* StageCabinet,AColdSteelSlidingDoor* StageDoor,AApartmentDeviceControl* StageDevice,AFPSGAMECharacter* StageRestPawn);
    UFUNCTION(Server,Reliable) void ServerExercise(int32 Stage);
    UFUNCTION(Server,Reliable) void ServerReport(int32 Stage,const FString& Json);
    UFUNCTION(Client,Reliable) void ClientExit();
    int32 Expected=INDEX_NONE;
private:
    friend class AApartmentNetworkAuditGameMode;
    UPROPERTY(Replicated) TObjectPtr<AColdSteelSceneContainer> Cabinet;
    UPROPERTY(Replicated) TObjectPtr<AColdSteelSlidingDoor> Door;
    UPROPERTY(Replicated) TObjectPtr<AApartmentDeviceControl> Device;
    UPROPERTY(Replicated) TObjectPtr<AFPSGAMECharacter> RestPawn;
    int32 Current=INDEX_NONE;
    double Started=0.;
    bool Sent=false,Reported=false;
};
UCLASS()
class AApartmentNetworkAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AApartmentNetworkAuditGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
    void Exercise(AApartmentAuditController* Player,int32 Stage);
    void Receive(AApartmentAuditController* Player,int32 Stage,const FString& Json);
private:
    UPROPERTY() TObjectPtr<AColdSteelSceneContainer> Cabinet;
    UPROPERTY() TObjectPtr<AColdSteelSlidingDoor> Door;
    UPROPERTY() TObjectPtr<AApartmentDeviceControl> Device;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> RestPawn;
    UPROPERTY() TObjectPtr<AApartmentAuditController> First;
    UPROPERTY() TObjectPtr<AApartmentAuditController> Late;
    TArray<TSharedPtr<FJsonValue>> Results;
    double ExitAt=-1.;
    bool Passed=true;
    bool WaitingForDisconnect=false;
    int32 Guests=0;
    void Stage(AApartmentAuditController* Player,int32 Value);
};
