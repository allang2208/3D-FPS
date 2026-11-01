#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "SwordFinishWireAudit.generated.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;

UCLASS()
class ASwordFinishWireState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    // The fixture seeds isolated profiles; it does not exercise inventory uploads.
    virtual void Tick(float Delta) override {}
};

UCLASS()
class ASwordFinishWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) TObjectPtr<AFPSGAMECharacter> Subject;
    UPROPERTY(Replicated) int32 Phase=INDEX_NONE;
    UFUNCTION(Server,Reliable) void ServerResult(int32 Case,bool Passed,const FString& Details);
    UFUNCTION(Client,Reliable) void ClientFinish();
    bool Reported=false;
private:
    int32 Prepared=INDEX_NONE;
    double Started=0,LastSent=-10,ExitAt=-1;
};

UCLASS()
class ASwordFinishWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASwordFinishWireGameMode();
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Logout(AController* Player) override;
    virtual void Tick(float Delta) override;
    void Record(ASwordFinishWireController* Sender,int32 Case,bool Passed,const FString& Details);
private:
    UPROPERTY() TObjectPtr<ASwordFinishWireController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> GuestModel;
    int32 NextPhase=0,Prepared=INDEX_NONE;
    bool Seeded=false,AwaitingReconnect=false,Reconnected=false,Passed=true;
    double PhaseAt=0,ExitAt=-1;
    TArray<TSharedPtr<class FJsonValue>> Rows;
    void Finish();
};
