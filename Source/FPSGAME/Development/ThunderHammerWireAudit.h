#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "ThunderHammerWireAudit.generated.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;

UCLASS()
class AThunderHammerWirePlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override {} // isolated seed, no real profile upload
};
UCLASS()
class AThunderHammerWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientCase(int32 Phase,AActor* Target);
    UFUNCTION(Server,Reliable) void ServerResult(int32 Phase,bool OK,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientFinish();
    UFUNCTION(Client,Reliable) void ClientObserverReport();
    UFUNCTION(Server,Reliable) void ServerObserverReport(bool SawCharge,bool SawStop,bool SawEmbeddedHammer,bool SawMeshySeat);
    UFUNCTION() void HammerDestroyed(AActor* Actor);
    static void Prepare(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,int32 Phase);
    int32 Finished=0;
    bool Passed=true;
    TArray<TSharedPtr<class FJsonValue>> Rows;
private:
    friend class AThunderHammerWireGameMode;
    UPROPERTY() TObjectPtr<AActor> Subject;
    TSet<TWeakObjectPtr<AActor>> Waves;
    TSet<TWeakObjectPtr<AActor>> Hammers;
    TSet<TWeakObjectPtr<AActor>> Arcs;
    int32 Current=INDEX_NONE,Catches=0,AudioCatches=0;
    bool Released=false,Sent=false,SawReturn=false,ChargeSent=false,HoldSent=false;
    bool UnexpectedCharge=false,SawConfirmedCharge=false;
    bool SawChargeResourceDebit=false;
    int64 InitialResourceRevision=0;
    bool ObserverCharge=false,ObserverStop=false,ObserverEmbedded=false,ObserverMeshy=false,ObserverReported=false;
    TWeakObjectPtr<AActor> ObserverChargePawn;
    double Started=0.,ExitAt=-1.,DiagnosticAt=-1.;
};
UCLASS()
class AThunderHammerWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AThunderHammerWireGameMode();
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
    virtual void Logout(AController* Exiting) override;
private:
    UPROPERTY() TObjectPtr<AThunderHammerWireController> Guest;
    UPROPERTY() TObjectPtr<AThunderHammerWireController> Observer;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> GuestModel;
    UPROPERTY() TObjectPtr<AActor> Subject;
    int32 Prepared=INDEX_NONE;
    bool Seeded=false,Finishing=false;
    double Joined=0.,LastSetup=-10.,ExitAt=-1.,DiagnosticAt=-1.;
    TArray<TSharedPtr<class FJsonValue>> FinalRows;
    bool FinalPassed=false,LoggedOut=false;
};
