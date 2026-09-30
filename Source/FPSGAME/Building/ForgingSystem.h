#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "CraftingSystem.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ForgingSystem.generated.h"

class UColdSteelStatusModel;
struct FColdSteelForgeRecipe
{
    FName Id;
    FString Output, Mold;
    TArray<FColdSteelCraftingInput> Inputs;
    TArray<FVector2D> Points;
};

/** Single-player crafting authority. UI never grants items or calculates accepted hits. */
UCLASS()
class FPSGAME_API UColdSteelForgingSystem : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    static constexpr int32 TargetCount=20;
    static constexpr double Preparation=3.0;
    static constexpr double HitWindowMin=2.2;
    static constexpr double HitWindowMax=3.2;
    static constexpr double TargetGapMin=.85;
    static constexpr double TargetGapMax=1.35;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override {return !IsTemplate()&&bActive;}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UColdSteelForgingSystem,STATGROUP_Tickables);}
    const TArray<FColdSteelForgeRecipe>& Catalog() const {return Recipes;}
    const FColdSteelForgeRecipe* Find(FName Id) const;
    const FColdSteelForgeJob& Job() const;
    bool CanStart(FName Id,FString& Reason) const;
    bool Start(FName Id,FString& Reason);
    bool Finish(FString& Reason);
    bool Claim(FString& Reason);
    bool GetPaidMaterials(TMap<FString,int64>& Paid) const;
    bool GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const;
    bool Discard(FString& Reason);
    bool Active() const {return bActive;}
    double Elapsed() const;
    double PhaseRemaining() const;
    int32 ResolvedTargets() const {return CompletedTargets;}
    bool StrikeInProgress() const {return bStrikePending;}
    int32 TargetIndex() const;
    // Life is also the visible and accepted radius scale, frozen when the swing starts.
    bool Target(FVector2D& UV,float& Life) const;
    bool BeginStrike(int32 ShownIndex,double ContactDelay,double RecoveryDelay);
    bool Strike(int32 ShownIndex,const FVector2D& UV,const FVector2D& RadiusUV);
    static double Multiplier(int32 Hits) {return .75+.5*FMath::Clamp(Hits,0,TargetCount)/TargetCount;}
    static FString Quality(int32 Hits);
    const FString& Error() const {return LastError;}
private:
    UColdSteelStatusModel* Model() const;
    void AdvanceTargets(double Now);
    void ResolveTarget(bool bHit,double Now);
    TArray<FColdSteelForgeRecipe> Recipes;
    TArray<FVector2D> Sequence;
    FString ActiveId,LastError;
    double StartedAt=0,RetryAt=0;
    // One deadline belongs to the current preparation, visible point, or gap.
    double TargetOpenedAt=0,PhaseEndsAt=0,StrikeContactAt=0,RecoveryAfterContact=0;
    int32 CompletedTargets=0;
    bool bTargetOpen=false,bStrikePending=false;
    bool bActive=false;
    float StrikeTargetLife=0;
};
