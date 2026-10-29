#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "KukriCombatWireAudit.generated.h"
class AFPSGAMECharacter;
class ANurseZombie;

UCLASS()
class AKukriCombatWireFloor : public AActor
{
    GENERATED_BODY()
public:
    AKukriCombatWireFloor();
};

UCLASS()
class AKukriCombatWireState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    virtual void ServerReportHit_Implementation(const FColdSteelNetHitReport& Report) override;
    FColdSteelNetHitReport LastContact;
    int32 Reports=0;
};
UCLASS()
class AKukriCombatWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientSetup(int32 Case);
    UFUNCTION(Server,Reliable) void ServerReady(int32 Case);
    UFUNCTION(Server,Reliable) void ServerClockProbe(double EstimatedServerTime);
    UFUNCTION(Client,Reliable) void ClientGo(int32 Case);
    UFUNCTION(Server,Reliable) void ServerDone(int32 Case,bool OK,int32 Count,double Spent);
    UFUNCTION(Client,Reliable) void ClientReplay(const FColdSteelNetHitReport& Report);
    UFUNCTION(Client,Reliable) void ClientExit();
    UFUNCTION(Client,Reliable) void ClientCheckReplacement(AFPSGAMECharacter* NewPawn,double Spent);
    UFUNCTION(Server,Reliable) void ServerReplacementReady(bool Passed);
    int32 Finished=0;
    bool Ready=false,Done=false,Completed=false;
    int32 Inputs=0;
    double ClientSpent=0.;
    bool ReplacementReady=false;
    bool ClockReady=false;
    int32 ClockStableSamples=0;
private:
    void SeedProfile();
    bool Seeded=false,Attached=false,Running=false,SawAction=false,Sent=false;
    int32 Current=-1,Fired=0;
    double Started=0.,NextInput=0.,ExitAt=-1.;
    double LastClockProbe=-1.;
};
UCLASS()
class AKukriCombatWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AKukriCombatWireGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Logout(AController* Player) override;
    virtual void Tick(float Delta) override;
    UFUNCTION() void CountDamage(AActor* Actor,float Damage,const UDamageType* Type,AController* DamageController,AActor* Causer);
private:
    UPROPERTY() TObjectPtr<AKukriCombatWireController> Guest;
    UPROPERTY() TObjectPtr<ANurseZombie> Target;
    TArray<TSharedPtr<class FJsonValue>> Rows;
    int32 Prepared=-1,Contacts=0,ObservedFrames=0,RiftFrames=0,LeftRiftFrames=0;
    int32 ReallocatedHits=0;
    int32 JoinedCount=0;
    double Started=0.,LastSetup=-10.,Settling=-1.,ExitAt=-1.,SpentBefore=0.,ReconnectSpent=0.;
    float DamageTotal=0.f;
    bool AllPassed=true,Replayed=false,WaitingReconnect=false;
    bool Replaced=false;
    UPROPERTY() TObjectPtr<class ACameraActor> CaptureCamera;
    TSet<FString> Captures;
};
