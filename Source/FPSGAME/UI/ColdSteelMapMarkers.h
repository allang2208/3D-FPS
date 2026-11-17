#pragma once

#include "CoreMinimal.h"

class APlayerController;
class AActor;
class UWorld;
class ATemperateHillsWorld;
class UColdSteelMapMarkerSharing;
struct FColdSteelDungeonMap;
struct FStreamableHandle;

enum class EColdSteelMapMarkerVisibility : uint8 { Personal,Team };

struct FColdSteelMapMarker
{
    FGuid Id;
    FString Region, Area, Label;
    FVector Position = FVector::ZeroVector;
    int32 Floor = 0;
    int32 ColorIndex = 0;
    uint32 LayoutSerial = 0;
    bool bDungeon = false;
    EColdSteelMapMarkerVisibility Visibility=EColdSteelMapMarkerVisibility::Personal;
    bool bReadOnly=false;
    FString OwnerName;
};

/** Local navigation view. Only explicitly shared data travels through the PlayerState component. */
struct FColdSteelMapMarkers
{
    static constexpr int32 Limit = 10;
    static constexpr int32 LabelLimit = 32;
    static constexpr int32 ColorCount = 8;
    static FLinearColor Color(int32 Index);
    static FText ColorName(int32 Index);
    static FString CleanLabel(const FString& Value);
    static FText VisibilityName(EColdSteelMapMarkerVisibility Visibility);

    ~FColdSteelMapMarkers();
    void Update(APlayerController* Player, const FColdSteelDungeonMap& Fog, bool bDungeonReady);
    bool Save(FColdSteelMapMarker& Marker);
    void Remove(FGuid Id);
    const FColdSteelMapMarker* Find(FGuid Id) const;
    const TArray<FColdSteelMapMarker>& All() const { return VisibleEntries; }
    int32 OwnedCount() const { return Entries.Num(); }
    int32 TeammateCount() const { return VisibleEntries.Num()-Entries.Num(); }
    const FString& ShareError() const { return SharingError; }
    bool IsActive(const FColdSteelMapMarker& Marker) const { return !ActiveRegion.IsEmpty() && Marker.Region==ActiveRegion; }
    uint32 Revision() const { return ChangeSerial; }

private:
    friend class UColdSteelDungeonFogCheckCommandlet;
    friend class AColdSteelMapMarkerWireController;
    TArray<FColdSteelMapMarker> Entries;
    TArray<FColdSteelMapMarker> Received,VisibleEntries;
    TWeakObjectPtr<UColdSteelMapMarkerSharing> Sharing;
    TMap<FGuid,uint32> PendingShares;
    FString SharingError;
    uint32 IncomingStamp=0;
    bool bHaveIncomingStamp=false;
    TMap<FGuid,TWeakObjectPtr<AActor>> Beams;
    TSharedPtr<FStreamableHandle> BeamAssets;
    TWeakObjectPtr<APlayerController> Owner;
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    FString LogicalRegion, ActiveRegion;
    FIntVector Origin = FIntVector::ZeroValue;
    uint32 LayoutSerial = 0, ChangeSerial = 0;
    bool bSearchedHills = false;
    void DestroyBeam(FGuid Id);
    void ClearBeams();
    void RefreshSharing();
    void RebuildView();
    void SendShare(const FColdSteelMapMarker& Marker,bool bWasShared);
};
