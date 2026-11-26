#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "CraftingSystem.h"
#include "ForgeBlankProfile.h"
#include "ForgingQuality.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "ForgingSystem.generated.h"

class UColdSteelStatusModel;
struct FColdSteelForgeMetal
{
    FName Item;
    double Bonus=0.;
};
struct FColdSteelForgeRecipe
{
    FName Id;
    FName Blank=TEXT("sword");
    FString Output, Mold;
    TArray<FColdSteelCraftingInput> Inputs;
    TArray<FColdSteelCraftingInput> LegacyInputs;
    int64 MetalCount=0;
    TArray<FVector2D> Points;
};

/** Single-player crafting authority. UI never grants items or calculates accepted hits. */
UCLASS()
class FPSGAME_API UColdSteelForgingSystem : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    UColdSteelForgingSystem* CreateNetworkSession(class UColdSteelStatusModel* M);
    UPROPERTY() TObjectPtr<class UColdSteelStatusModel> NetworkModel;
    static constexpr int32 TargetCount=ColdSteelForgeQuality::TargetCount;
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
    const TArray<FColdSteelForgeMetal>& Metals() const {return MetalOptions;}
    const FColdSteelForgeMetal* FindMetal(FName Id) const;
    bool InputsFor(FName Recipe,FName Metal,TArray<FColdSteelCraftingInput>& Out) const;
    const FColdSteelForgeBlank* FindBlank(FName Id) const {return Blanks.Find(Id);}
    const TMap<FName,FColdSteelForgeBlank>& BlankProfiles() const {return Blanks;}
    const FColdSteelForgeJob& Job() const;
    bool CanStart(FName Id,FString& Reason,FName Metal=FName(TEXT("ironIngot"))) const;
    bool Start(FName Id,FString& Reason,FName Metal=FName(TEXT("ironIngot")),AActor* Station=nullptr);
    void SetStation(AActor* Station){BoundStation=Station;}
    bool Finish(FString& Reason);
    bool Claim(FString& Reason);
    bool GetPaidMaterials(TMap<FString,int64>& Paid) const;
    bool GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const;
    bool Discard(FString& Reason);
    FColdSteelForgeNetState NetworkState() const;
    void ApplyNetworkState(const FColdSteelForgeNetState& State);
    void NetworkSessionEnded();
    bool Active() const {return bActive;}
    double Elapsed() const;
    double PhaseRemaining() const;
    int32 ResolvedTargets() const {return CompletedTargets;}
    bool StrikeInProgress() const {return bStrikePending;}
    int32 TargetIndex() const;
    // Life is also the visible and accepted radius scale, frozen when the swing starts.
    bool Target(FVector2D& UV,float& Life) const;
    bool BeginStrike(int32 ShownIndex,double ContactDelay,double RecoveryDelay,const FVector2D& SurfaceUV=FVector2D(.5,.375));
    bool Strike(int32 ShownIndex,const FVector2D& UV,const FVector2D& RadiusUV);
    static double Multiplier(const FColdSteelForgeJob& Job) {return ColdSteelForgeQuality::Multiplier(Job);}
    static FString Quality(int32 Hits) {return ColdSteelForgeQuality::Label(Hits);}
    const FString& Error() const {return LastError;}
private:
    UColdSteelStatusModel* Model() const;
    void AdvanceTargets(double Now);
    void ResolveTarget(double Now);
    TArray<FColdSteelForgeRecipe> Recipes;
    TArray<FColdSteelForgeMetal> MetalOptions;
    TMap<FName,FColdSteelForgeBlank> Blanks;
    TArray<FVector2D> Sequence;
    FString ActiveId,LastError;
    TWeakObjectPtr<AActor> BoundStation;
    double StartedAt=0,RetryAt=0;
    // One deadline belongs to the current preparation, visible point, or gap.
    double TargetOpenedAt=0,PhaseEndsAt=0,StrikeContactAt=0,RecoveryAfterContact=0;
    int32 CompletedTargets=0;
    bool bTargetOpen=false,bStrikePending=false;
    bool bActive=false;
    float StrikeTargetLife=0;
};
