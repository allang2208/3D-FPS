#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "CraftingSystem.h"
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
    TArray<FGunAssemblyPart> Parts;
    FVector BodyPosition=FVector::ZeroVector;
    FVector Camera=FVector(82,0,225),LookAt=FVector(82,0,95);
    float PositionTolerance=5,AngleTolerance=18,CalibrationDuration=5;
};
class UColdSteelStatusModel;

/** Owns paid work, scoring and the single inventory transaction for delivery. */
UCLASS()
class FPSGAME_API UGunAssemblySystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    const FGunAssemblyRecipe& Recipe() const;
    const TArray<FGunAssemblyRecipe>& Catalog() const {return Recipes;}
    bool SelectRecipe(FName Id);
    FString ProductName() const;
    const FColdSteelGunAssemblyJob& Job() const;
    bool CanStart(FString& Reason) const;
    bool Start(FString& Reason);
    bool Install(int32 Part,float Distance,float Angle,FString& Reason);
    void Calibrate(float DeltaTime,float Error);
    bool Finish(FString& Reason);
    bool Claim(FString& Reason);
    bool GetPaidMaterials(TMap<FString,int64>& Paid) const;
    bool GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const;
    bool Discard(FString& Reason);
    bool Pause(FString& Reason);
    bool Assembled() const;
    bool Installed(int32 Part) const;
    int32 InstalledCount() const;
    float Score() const;
    static FString QualityName(float Score);
    static FString BenefitText(float Score);
private:
    UColdSteelStatusModel* Model() const;
    TArray<FGunAssemblyRecipe> Recipes;
    FName SelectedRecipe;
};
