#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelPlantingTypes.h"
#include "ColdSteelPlantingSystem.generated.h"

class UStaticMesh;
class UInstancedStaticMeshComponent;
class AVoxelBuildWorld;
class AVoxelBuildPrefabActor;
class UColdSteelStatusModel;
class APawn;
struct FColdSteelInventoryRequest;
struct FColdSteelProfile;
struct FStreamableHandle;

struct FColdSteelCropRule
{
    FName Id;
    FString Name,InputItem,OutputItem;
    int64 InputCount=1,OutputCount=3;
    double GrowthSeconds=1200.;
    FIntPoint Footprint=FIntPoint(1,1);
    TMap<FName,TArray<FSoftObjectPath>> Variants;
};

UCLASS()
class FPSGAME_API UColdSteelPlantingSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
    friend class UColdSteelPlantingAuditCommandlet;
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    bool LoadCatalog();
    const TArray<FColdSteelCropRule>& Catalog() const {return Rules;}
    const FColdSteelCropRule* Find(FName Crop) const;
    const FColdSteelCropPlant* Occupant(const AVoxelBuildWorld* World,FIntVector Cell,int32 Slot) const;
    bool CanAct(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FString& Reason) const;
    bool Act(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FString& Reason,const FGuid& ExpectedPlantId=FGuid());
    bool SelectionAnchors(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,TArray<int32>& Anchors,FString& Reason) const;
    bool CanPlantSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,int32& Count,FString& Reason) const;
    bool PlantSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,FString& Reason);
    void UpdateWorld(AVoxelBuildWorld* World,float Delta);
    const TArray<FColdSteelCropPlant>& Plants(const AVoxelBuildWorld* World) const;
    int64 NowTicks(const AVoxelBuildWorld* World) const;
    uint64 StateSerial() const {return ChangeSerial;}
    bool Pending() const {return bNetworkPending;}
    const FString& NetworkNotice() const {return Notice;}
    bool NetworkFailed() const {return bNetworkFailed;}
    int32 Capacity() const {return MaxPlants;}
    void ObserveServerClock(UWorld* Context,int64 UtcTicks);
    void NetworkEnded();
    FColdSteelPlantingNetState NetworkState(AVoxelBuildWorld* World);
    bool ApplyNetworkState(UWorld* Context,const FColdSteelPlantingNetState& State);
    void NetworkFinished(const FColdSteelInventoryRequest& Request,bool Success,const FString& Reason,APawn* RequestPawn);
    bool PrepareNetwork(AVoxelBuildWorld* World,const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Operator,
        FColdSteelProfile& Profile,TArray<FColdSteelCropPlant>& After,FString& Reason) const;
    static FName BedPrefabId() {return FName(TEXT("planting_bed"));}
private:
    bool Prepare(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,FColdSteelProfile& Proposed,FString& Reason,bool Preview=false,
        UColdSteelStatusModel* Operator=nullptr,TArray<FColdSteelCropPlant>* SharedAfter=nullptr,const FColdSteelProfile* BaseProfile=nullptr) const;
    bool PrepareSelection(AVoxelBuildWorld* World,FIntVector Cell,const TArray<int32>& Slots,FName Crop,UColdSteelStatusModel* Operator,
        FColdSteelProfile& Profile,TArray<FColdSteelCropPlant>& After,FString& Reason) const;
    bool RequestNetwork(AVoxelBuildWorld* World,FIntVector Cell,int32 Slot,FName Crop,const FGuid& ExpectedPlantId,FString& Reason,const TArray<int32>& Slots={});
    void EndNetworkContext();
    UColdSteelStatusModel* Model() const;
    AVoxelBuildPrefabActor* Bed(const AVoxelBuildWorld* World,FIntVector Cell) const;
    void ClearPresentation();
    TArray<FColdSteelCropRule> Rules;
    TArray<FVector> SlotsCm;
    int32 MaxPlants=1024;
    float ScaleMin=.9f,ScaleMax=1.f;
    double Accum=0.;
    uint32 VisualSignature=0;
    bool bAssetsReady=false,bVisualDirty=true;
    TWeakObjectPtr<AVoxelBuildWorld> ActiveWorld;
    TSharedPtr<FStreamableHandle> AssetRequest;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> MeshCache;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UInstancedStaticMeshComponent>> MeshGroups;
    UPROPERTY(Transient) FColdSteelPlantingNetState Mirror;
    TWeakObjectPtr<UWorld> MirrorWorld,ClockWorld,RequestWorld;
    TWeakObjectPtr<APawn> RequestPawn;
    TWeakObjectPtr<AVoxelBuildPrefabActor> RequestBed;
    FGuid RequestBedId;
    int64 ClockUtcTicks=0;
    uint64 PublishedSnapshotSequence=0;
    double ClockServerSeconds=0.,MirrorReceivedAt=0.;
    TWeakObjectPtr<UWorld> ObservedClockWorld;
    int64 ObservedUtcTicks=0;
    double ObservedUtcAt=0.;
    uint64 ChangeSerial=1;
    bool bNetworkPending=false,bNetworkFailed=false;
    FString Notice;
};
