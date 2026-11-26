#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "ShotgunWireAudit.generated.h"
class AFPSGAMECharacter;
class FJsonValue;

UCLASS()
class AShotgunWireAuditPlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    // This isolated fixture pins profiles while production shot/ammo RPCs run.
    virtual void Tick(float Delta) override {}
};
UCLASS()
class AShotgunWireAuditController : public APlayerController
{
    GENERATED_BODY()
    friend class AShotgunWireAuditGameMode;
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientSetup(int32 Case,const FString& Id,AFPSGAMECharacter* HostPawn);
    UFUNCTION(Server,Reliable) void ServerReady(int32 Case);
    UFUNCTION(Server,Reliable) void ServerProbeShot(int32 Case,FVector Eye,FVector Muzzle,FVector Aim,double FiredAt);
    UFUNCTION(Server,Reliable) void ServerCaseResult(int32 Case,bool OwnerOK,bool RemoteOK,const TArray<FVector_NetQuantizeNormal>& Predicted);
    UFUNCTION(Client,Reliable) void ClientFinish(bool Passed);
    UFUNCTION(Server,Reliable) void ServerPresentationResult(int32 Phase,bool ObserverOK,FVector HostLaser,FVector OwnerLaser,FVector OwnerGrip);
    bool TickM870Presentation(float Delta);
    bool bM24CycleCasePassed=true;
    void TickSniperZhiming(AFPSGAMECharacter* Subject,double Now);
    void ProbeSniperZhiming(int32 Phase);
    bool bObservedSniperStun=false;
    float SniperStunPeak=0.f;
    double SniperStunFirstAt=-1.,SniperStunLastAt=-1.;
    int32 SniperProbePhase=INDEX_NONE;
    double SniperProbeStartedAt=0.;
    void SetupM870Presentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host);
    static void PoseM870Presentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Muted);
    UFUNCTION(Server,Reliable) void ServerSparrowResult(int32 Phase,bool ObserverOK);
    bool TickSparrowPresentation(float Delta);
    void SetupSparrowPresentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host);
    static void PoseSparrowPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Muted);
    static bool CheckSparrowPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Expired,TSharedPtr<class FJsonObject> Row);
    bool TickPistolPresentation(float Delta);
    bool TickPistolAmmo(float Delta);
    bool TickMealReceipt(float Delta);
    void SetupMealReceipt(int32 Phase,const FString& Session);
    UFUNCTION(Server,Reliable) void ServerMealResult(int32 Phase,bool LocalOK,int32 MealCount,int32 WaterUses);
    FGuid PreviousMealUse;
    bool bObservedMeal=false;
    void SetupPistolAmmo(int32 Phase,const FString& Id,AFPSGAMECharacter* Host);
    UFUNCTION(Server,Reliable) void ServerPistolAmmoResult(int32 Phase,const FString& Report);
    void SetupPistolPresentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host);
    static void PosePistolPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Initialize=false);
    static bool CheckPistolPresentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Expired,TSharedPtr<class FJsonObject> Row);
    void ReadyPistolPresentation(int32 Phase);
    bool bPistolObserverReady=false;
    UFUNCTION(Server,Reliable) void ServerPistolResult(int32 Phase,const FString& Report);
    int32 Finished=0,Expected=INDEX_NONE;
    bool bAllPassed=true;
    TArray<TSharedPtr<FJsonValue>> Results;
private:
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> ObserverSubject;
    FString Weapon;
    int32 Current=INDEX_NONE;
    double Started=0,SentAt=-1,ExitAt=-1;
    TArray<FVector_NetQuantizeNormal> Prediction;
    bool bSent=false,bReported=false;
    int32 AmmoStage=0,AmmoFired=0;
    double AmmoNextShot=0.;
    bool AmmoCancelled=false;
};
UCLASS()
class AShotgunWireAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AShotgunWireAuditGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<AShotgunWireAuditController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> HostPawn;
    FString Weapon;
    int32 Prepared=INDEX_NONE;
    double Joined=0,LastSetup=-10,ExitAt=-1;
    bool TickM870Presentation(float Delta);
    bool TickSparrowPresentation(float Delta);
    bool TickPistolPresentation(float Delta);
    bool TickPistolAmmo(float Delta);
    bool TickMealReceipt(float Delta);
    int32 PresentationConnections=0;
    bool bPresentationPassed=true;
    TArray<TSharedPtr<FJsonValue>> PresentationHistory;
};
