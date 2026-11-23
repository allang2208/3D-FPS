#pragma once

#include "Components/ActorComponent.h"
#include <initializer_list>
#include "VillageResidentDetail.generated.h"

class USkeletalMeshComponent;
struct FStreamableHandle;

UCLASS()
class UVillageResidentDetail : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageResidentDetail();
    static void Attach(AActor& Owner, TArray<FSoftObjectPath> Assets, FSimpleDelegate Dress,
        std::initializer_list<USkeletalMeshComponent*> Parts, FSimpleDelegate Release = {});
    void Refresh();
protected:
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    TArray<FSoftObjectPath> Paths;
    TArray<TWeakObjectPtr<USkeletalMeshComponent>> Meshes;
    TArray<uint8> OriginalTickOptions;
    FSimpleDelegate ApplyAppearance, ReleaseAppearance;
    TSharedPtr<FStreamableHandle> Load;
    double LastNeeded = 0.;
    bool bReduced = false;
    void ReducePoseWork(bool bReduce);
};
