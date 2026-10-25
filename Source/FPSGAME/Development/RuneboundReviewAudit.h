#pragma once
#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Monsters/NurseZombie.h"
#include "RuneboundReviewAudit.generated.h"

class AFPSGAMECharacter;
class UColdSteelStatusModel;

/** Capsule-only native enemy fixture; records raw damage, without armor/AI/art. */
UCLASS(Transient,NotBlueprintable)
class ARuneboundReviewTarget : public ANurseZombie
{
    GENERATED_BODY()
public:
    ARuneboundReviewTarget();
    virtual void OnConstruction(const FTransform& Transform) override {}
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override {}
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Source) override;
    TArray<float> Physical,Magic;
    void ResetDamage(){Physical.Reset();Magic.Reset();}
};

UCLASS()
class URuneboundReviewAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};

UCLASS(Transient,NotBlueprintable)
class ARuneboundReviewController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientSetup(const FString& Instance,ARuneboundReviewTarget* Target,AFPSGAMECharacter* Host);
    UFUNCTION(Server,Reliable) void ServerPhase(int32 Phase,bool Passed);
    UFUNCTION(Client,Reliable) void ClientFinish(bool Passed);
    void SetupSprint(const FString& Instance);
    void TickSprint(float Delta);
    UFUNCTION(Client,Reliable) void ClientSprintResult(float ServerX,bool Passed);
    int32 Reported=0;
    bool AllPassed=true;
private:
    FString Weapon;
    UPROPERTY() TObjectPtr<ARuneboundReviewTarget> Subject;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> HostSubject;
    double Started=-1.,ExitAt=-1.;
    int32 Stage=0;
    bool Sent=false;
    FVector SprintOrigin=FVector::ZeroVector;
    float SprintAge=0.f;
};

/** Explicit RuneboundReviewWire flag + isolated profile required. */
UCLASS(Transient,NotBlueprintable)
class ARuneboundReviewGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ARuneboundReviewGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
private:
    void TickSprint(float Delta);
    UPROPERTY() TObjectPtr<ARuneboundReviewController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> HostPawn;
    UPROPERTY() TObjectPtr<ARuneboundReviewTarget> Target;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> GuestModel;
    FString Weapon;
    double Joined=-1.,PhaseAt=-1.,ExitAt=-1.,InitialHostStamina=0.,InitialGuestStamina=0.;
    int32 Stage=0;
    TArray<TSharedPtr<FJsonValue>> Results;
};
