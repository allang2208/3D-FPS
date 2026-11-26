#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HatchetCharmComponent.generated.h"

class UColdSteelStatusModel;
class USoundBase;
class USoundAttenuation;
struct FColdSteelSkillShot;

USTRUCT()
struct FHatchetStepState
{
    GENERATED_BODY()
    UPROPERTY() FString Source;
    UPROPERTY() double ReadyUntil=0.;
    UPROPERTY() double SpeedUntil=0.;
};

// The equipped item owns its passive; the pawn owns the two shared cooldowns.
UCLASS()
class FPSGAME_API UHatchetCharmComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UHatchetCharmComponent();
    void Configure(const UColdSteelStatusModel* Model);
    bool CanWedge(const FColdSteelSkillShot& Shot,AActor* Target) const;
    void Confirm(const FColdSteelSkillShot& Shot,AActor* Target,bool Wedge,bool Broke,UColdSteelStatusModel* Model);
    bool StepReady() const;
    float MoveScale() const;
    void SpendStep();
    void FinishDodge(bool Completed);
    void RejectDodge();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
    double Clock() const;
    bool HasLiveStep() const;
    UFUNCTION(NetMulticast,Unreliable) void MulticastCharmCue(bool Wedge,const FString& Instance);
    UPROPERTY(Replicated) FHatchetStepState Step;
    UPROPERTY() TObjectPtr<USoundBase> Clink;
    UPROPERTY() TObjectPtr<USoundBase> Chirp;
    UPROPERTY() TObjectPtr<USoundAttenuation> Attenuation;
    struct FContactSet { FString Hand; uint32 Serial=0; TSet<TWeakObjectPtr<AActor>> Targets; };
    TArray<FContactSet> HeavyContacts;
    uint32 LastBreakCueSerial=0;
    TArray<FString> Wedges,Whistles;
    FString DodgeSource;
    double NextRefund=0.,NextWhistle=0.,PredictedSpent=-1.;
};
