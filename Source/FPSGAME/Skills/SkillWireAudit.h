#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "SkillWireAudit.generated.h"
class ANurseZombie;
class AFPSMeteorStrike;
class UColdSteelStatusModel;
struct FColdSteelItem;
namespace SkillWireEquipment
{
    FColdSteelItem MakeWeapon(UColdSteelStatusModel* Model,const TCHAR* DefaultWeapon);
}

// Keep isolated fixture profiles fixed while exercising inherited production
// RPCs. Full profile upload/mirror ordering is covered by the authority audit.
UCLASS()
class ASkillWireAuditPlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override {}
};

UCLASS()
class ASkillWireAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientSetup(ANurseZombie* InSubject,const FString& InWeapon,float Stamina,float Cost);
    UFUNCTION(Client,Reliable) void ClientRestoreStamina();
    UFUNCTION(Server,Reliable) void ServerResult(bool Paid,bool Cooldown,bool Locked,bool Unlocked,bool Meteor);
    UFUNCTION(Client,Reliable) void ClientSetupArmor(class AFPSGAMECharacter* ExistingArmor);
    void TickFlameArmor();
    void TickConversationCombat();
    void TickForgedBlade();
    void SetupForgedBlade(ANurseZombie* First,ANurseZombie* Second);
    void TickLeapWire(float Delta);
    void SetupLeapWire(int32 Case);
    void SetupSessionChain(ANurseZombie* Target,const FString& Id);
    void TickSessionChain();
    UFUNCTION(Server,Reliable) void ServerObserveChain(int32 CutMask);
    int32 ObservedChainCuts=INDEX_NONE;
    int32 ChainWristSampleMask=0;
    FVector ChainFirstWrists[4][2]{};
    bool bSawRemoteChainImpact=false,bRemoteChainImpactEnded=false;
    UFUNCTION(Client,Reliable) void ClientSetupConversation(int32 Case,ANurseZombie* First,ANurseZombie* Second,class AFPSGAMECharacter* Observer);
    int32 ConversationCase=-1;
    UPROPERTY() TObjectPtr<ANurseZombie> ConversationSecond;
    bool bConversationContact=false,bConversationFinished=false,bConversationHasteSeen=false,bConversationLateSeen=false;
    void TickStarMarrow();
    UFUNCTION(Client,Reliable) void ClientStarStep(int32 Step,class AFPSGAMECharacter* ObserverPawn);
    UFUNCTION(Server,Reliable) void ServerStarStep(int32 Step,bool Passed);
    int32 StarStep=0,StarReportedStep=0;
    bool bStarPassed=true,bLateSeen=false,bStarSent=false,bStartedMotion=false,bSawStatusCap=false,bSawRefresh=false;
    double StarStatusFirstSeen=-1.;
    float StarInitialMana=0.f,StarManaCost=0.f;
    UPROPERTY() TObjectPtr<class AFPSGAMECharacter> StarObservedPawn;
    UFUNCTION(Client,Reliable) void ClientSetupMeteor(float Mana,float Cost);
    UFUNCTION(Server,Reliable) void ServerMeteorResult(bool PaidOnce,bool Replica,bool Late,bool Receipt);
    void TickMeteor();
    bool bReported=false,bPassed=false;
private:
    UPROPERTY() TObjectPtr<ANurseZombie> Subject;
    FString Weapon;
    float InitialStamina=0.f,ExpectedCost=0.f;
    bool bSetup=false,bHit=false,bPaid=false,bCooldown=false,bLocked=false,bUnlocked=false,bMeteor=false,bDone=false;
    double Started=-1.,ExitAt=-1.;
    UPROPERTY() TObjectPtr<class AFPSGAMECharacter> OtherArmor;
    uint32 ArmorCastId=0;
    bool bArmorOwn=false,bArmorOther=false,bArmorOwnEnded=false,bArmorOtherEnded=false;
    uint32 MeteorCastId=0;
    bool bMeteorReplica=false,bMeteorLate=false,bMeteorReceipt=false;
    float MeteorInitialMana=0.f,MeteorCost=0.f;
};

/** Opt-in empty-map fixture. Uses production PlayerState RPCs and actor replicas. */
UCLASS()
class ASkillWireAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ASkillWireAuditGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
    UFUNCTION() void CountContact(AActor* Actor,float Damage,const class UDamageType* Type,class AController* DamageController,AActor* Causer);
    void TickFlameArmor();
    void TickConversationCombat();
    void TickForgedBlade();
    void TickLeapWire(float Delta);
    void TickSessionChain();
    int32 ConversationCase=0,ConversationPhase=0;
    double ConversationStarted=-1.;
    UPROPERTY() TObjectPtr<ANurseZombie> ConversationSecond;
    TArray<TSharedPtr<FJsonValue>> ConversationResults;
    void TickStarMarrow(float Delta);
    void TickMeteor();
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> StarObserverProfile;
    bool bStarPassed=true,bSawThirdPersonMotion=false,bSawThirdPersonFlame=false;
    double StarGrantedAt=-1.,StarHostSpend=0.,StarStatusAt=-1.;
    float StarInitialMana=0.f,StarManaCost=0.f;
    UPROPERTY() TObjectPtr<class AFPSGAMECharacter> StarObservedPawn;
private:
    UPROPERTY() TObjectPtr<ASkillWireAuditController> Guest;
    UPROPERTY() TObjectPtr<ASkillWireAuditController> ChainObserver;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> GuestModel;
    UPROPERTY() TObjectPtr<ANurseZombie> Target;
    UPROPERTY() TObjectPtr<AFPSMeteorStrike> Meteor;
    FString Weapon;
    int32 Contacts=0,Stage=0;
    float InitialStamina=0.f,ExpectedCost=0.f;
    double Joined=-1.,LastSetup=-1.,ExhaustedAt=-1.,MeteorAt=-1.,ExitAt=-1.;
    UPROPERTY() TObjectPtr<class AFPSGAMECharacter> ExistingArmor;
    float ArmorInitialMana=0.f,ArmorManaCost=0.f;
    int32 ArmorHostXP=0;
};
