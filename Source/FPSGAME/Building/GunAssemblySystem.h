#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "CraftingSystem.h"
#include "ForgingSystem.h"
#include "GunAssemblyQuality.h"
#include "GunAssemblyCalibration.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "GunAssemblySystem.generated.h"

struct FGunAssemblyPart
{
    FString Id,Name,Mesh;
    FVector Target=FVector::ZeroVector,Loose=FVector::ZeroVector;
    FVector Extent=FVector(3);
    float Angle=0,Radius=4;
};
struct FGunAssemblyRecipe
{
    FName Id;
    FString Output,BodyMesh;
    TArray<FColdSteelCraftingInput> Inputs;
    TArray<FColdSteelCraftingInput> LegacyInputs;
    int64 MetalCount=0;
    TArray<FGunAssemblyPart> Parts;
    FVector BodyPosition=FVector::ZeroVector;
    FVector Camera=FVector(82,0,225),LookAt=FVector(82,0,95);
    float PositionTolerance=5,AngleTolerance=18,CalibrationDuration=GunAssemblyCalibration::Duration;
};
class UColdSteelStatusModel;
DECLARE_MULTICAST_DELEGATE_ThreeParams(FGunAssemblyNetworkResult,const FString&,bool,const FString&);

/** Owns paid work, scoring and the single inventory transaction for delivery. */
UCLASS()
class FPSGAME_API UGunAssemblySystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    UGunAssemblySystem* CreateNetworkSession(class UColdSteelStatusModel* M);
    UPROPERTY() TObjectPtr<class UColdSteelStatusModel> NetworkModel;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const FGunAssemblyRecipe& Recipe() const;
    const TArray<FGunAssemblyRecipe>& Catalog() const {return Recipes;}
    bool SelectRecipe(FName Id);
    const TArray<FColdSteelForgeMetal>& Metals() const;
    const FColdSteelForgeMetal* FindMetal(FName Id) const;
    bool SelectMetal(FName Id);
    FName Metal() const;
    double MaterialBonus() const;
    bool InputsFor(TArray<FColdSteelCraftingInput>& Inputs) const;
    FString ProductName() const;
    const FColdSteelGunAssemblyJob& Job() const;
    bool CanStart(FString& Reason) const;
    bool Start(FString& Reason);
    bool CanResume(FString& Reason) const;
    bool Resume(FString& Reason);
    void SetStation(AActor* Station){BoundStation=Station;}
    AActor* Station() const {return BoundStation.Get();}
    FGunAssemblyNetworkResult OnNetworkResult;
    bool Install(int32 Part,float Distance,float Angle,FString& Reason);
    void Calibrate(float DeltaTime,float Error,float HitFraction=-1.f);
    bool Finish(FString& Reason);
    bool Claim(FString& Reason);
    bool GetPaidMaterials(TMap<FString,int64>& Paid) const;
    bool GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const;
    bool Discard(FString& Reason);
    bool Pause(FString& Reason);
    void NetworkSessionEnded(){CalibrationAccum=CalibrationErrorAccum=CalibrationHitAccum=0.f;CalibrationPawn.Reset();CalibrationJob.Reset();}
    bool Assembled() const;
    bool Installed(int32 Part) const;
    int32 InstalledCount() const;
    float Score() const;
    static FString QualityName(float Score);
    static FString BenefitText(float Score,double MaterialBonus=0.);
private:
    bool RequestTransaction(const FString& Mode,FString& Reason);
    TWeakObjectPtr<AActor> BoundStation;
    UColdSteelStatusModel* Model() const;
    TArray<FGunAssemblyRecipe> Recipes;
    FName SelectedRecipe;
    FName SelectedMetal=TEXT("ironIngot");
    float CalibrationAccum=0,CalibrationErrorAccum=0,CalibrationHitAccum=0;
    TWeakObjectPtr<class APawn> CalibrationPawn;
    FString CalibrationJob;
};
