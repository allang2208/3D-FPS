#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DevelopmentEnvironmentObject.generated.h"

struct FProductionResource;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UBoxComponent;

struct FDevelopmentEnvironmentEntry
{
    FName Id;
    FString Name;
    FSoftObjectPath Mesh;
    FString Ore;
    bool IsTree() const { return Ore.IsEmpty(); }
};

/** A session-only harvest target created by the F6 environment page. */
UCLASS(Transient, NotBlueprintable)
class ADevelopmentEnvironmentObject : public AActor
{
    GENERATED_BODY()
public:
    ADevelopmentEnvironmentObject();
    static const TArray<FDevelopmentEnvironmentEntry>& Catalogue();
    static const FDevelopmentEnvironmentEntry* FindEntry(FName Id);
    bool Initialize(FName Id,int32 Shape=0);
    bool Describe(FProductionResource& Resource) const;
    void ApplyStrike(const FProductionResource& Resource, const FHitResult& Hit, bool bDepleted);
    bool FindGround(const FVector& Around, FHitResult& Ground) const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
    UPROPERTY(ReplicatedUsing=OnRep_Entry) FName EntryId;
    UPROPERTY(ReplicatedUsing=OnRep_Entry) int32 OreShape=0;
    UPROPERTY(Replicated) float HealthRatio = 1.f;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Rock;
    UPROPERTY() TObjectPtr<USkeletalMeshComponent> Tree;
    UPROPERTY() TObjectPtr<UBoxComponent> Trunk;
    UFUNCTION() void OnRep_Entry();
    bool ApplyEntry();
};
