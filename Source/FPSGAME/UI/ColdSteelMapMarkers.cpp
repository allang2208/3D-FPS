#include "ColdSteelMapMarkers.h"
#include "ColdSteelDungeonMap.h"
#include "ColdSteelUIStyle.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelMapMarkerSharing.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
    const FSoftObjectPath BeamPath(TEXT("/Game/Items/LootFX/M_LootBeam.M_LootBeam"));
    const FSoftObjectPath PlanePath(TEXT("/Engine/BasicShapes/Plane.Plane"));
}

FLinearColor FColdSteelMapMarkers::Color(int32 Index)
{
    // User-assigned navigation colours; surfaces and ordinary text stay neutral.
    static const FColor Palette[]={FColor(232,211,154),FColor(111,184,255),FColor(104,213,173),
        FColor(255,129,147),FColor(188,153,255),FColor(103,222,231),FColor(255,174,105),FColor(232,232,232)};
    return FLinearColor::FromSRGBColor(Palette[FMath::Clamp(Index,0,ColorCount-1)]);
}

FText FColdSteelMapMarkers::ColorName(int32 Index)
{
    static const TCHAR* Names[]={TEXT("金"),TEXT("蓝"),TEXT("绿"),TEXT("红"),TEXT("紫"),TEXT("青"),TEXT("橙"),TEXT("白")};
    return FText::FromString(Names[FMath::Clamp(Index,0,ColorCount-1)]);
}

FText FColdSteelMapMarkers::VisibilityName(EColdSteelMapMarkerVisibility Visibility)
{
    return FText::FromString(Visibility==EColdSteelMapMarkerVisibility::Team?TEXT("全队可见"):TEXT("仅本人"));
}

FString FColdSteelMapMarkers::CleanLabel(const FString& Value)
{
    FString Result;
    for (TCHAR C:Value)
    {
        if (Result.Len()>=LabelLimit) break;
        if (C>=TEXT(' ') && C!=0x7f && C!=0x2028 && C!=0x2029) Result.AppendChar(C);
    }
    // Do not keep half of a UTF-16 surrogate pair at the length boundary.
    if (!Result.IsEmpty() && Result[Result.Len()-1]>=0xd800 && Result[Result.Len()-1]<=0xdbff) Result.LeftChopInline(1);
    Result.TrimStartAndEndInline();
    return Result;
}

FColdSteelMapMarkers::~FColdSteelMapMarkers() { ClearBeams(); }

void FColdSteelMapMarkers::DestroyBeam(FGuid Id)
{
    if (auto* Weak=Beams.Find(Id)) if (auto* Actor=Weak->Get()) Actor->Destroy();
    Beams.Remove(Id);
}

void FColdSteelMapMarkers::ClearBeams()
{
    for (const auto& Pair:Beams) if (auto* Actor=Pair.Value.Get()) Actor->Destroy();
    Beams.Reset();
}

const FColdSteelMapMarker* FColdSteelMapMarkers::Find(FGuid Id) const
{
    return VisibleEntries.FindByPredicate([Id](const auto& Marker){return Marker.Id==Id;});
}

bool FColdSteelMapMarkers::Save(FColdSteelMapMarker& Marker)
{
    SharingError.Reset();
    if(Marker.bReadOnly)return false;
    auto* Existing=Entries.FindByPredicate([&](const auto& M){return M.Id==Marker.Id;});
    if (Marker.bDungeon && Marker.LayoutSerial!=LayoutSerial) return false;
    if ((!Existing && Marker.Id.IsValid()) || (!Existing && Entries.Num()>=Limit) || Marker.Region.IsEmpty()) return false;
    if(Marker.Visibility==EColdSteelMapMarkerVisibility::Team&&!UColdSteelMapMarkerSharing::For(Owner.Get()))
    {SharingError=TEXT("玩家连接尚未就绪，请稍后共享");return false;}
    const bool bWasShared=Existing&&Existing->Visibility==EColdSteelMapMarkerVisibility::Team;
    Marker.Label=CleanLabel(Marker.Label);
    if (Marker.Label.IsEmpty()) Marker.Label=TEXT("标记");
    Marker.ColorIndex=FMath::Clamp(Marker.ColorIndex,0,ColorCount-1);
    if (Existing) *Existing=Marker;
    else { Marker.Id=FGuid::NewGuid(); Entries.Add(Marker); }
    // Recreate just the edited beam on the next menu update; no synchronous asset loading.
    DestroyBeam(Marker.Id);
    SendShare(Marker,bWasShared);
    RebuildView();
    ++ChangeSerial;
    return true;
}

void FColdSteelMapMarkers::Remove(FGuid Id)
{
    const auto* Existing=Entries.FindByPredicate([Id](const auto& M){return M.Id==Id;});
    if(!Existing)return; // A teammate's replicated marker is read-only, including the Delete shortcut.
    FColdSteelMapMarker Withdrawn=*Existing;
    Withdrawn.Visibility=EColdSteelMapMarkerVisibility::Personal;
    SendShare(Withdrawn,Existing->Visibility==EColdSteelMapMarkerVisibility::Team);
    Entries.RemoveAll([Id](const auto& M){return M.Id==Id;});
    DestroyBeam(Id);RebuildView();++ChangeSerial;
}

void FColdSteelMapMarkers::Update(APlayerController* Player,const FColdSteelDungeonMap& Fog,bool bDungeonReady)
{
    if (!Player || !Player->IsLocalController()) return;
    if (!Owner.IsExplicitlyNull() && Owner.Get()!=Player) return;
    Owner=Player;
    if (World.Get()!=Player->GetWorld())
    {
        ClearBeams();Entries.Reset();Received.Reset();VisibleEntries.Reset();PendingShares.Reset();Sharing.Reset();
        bHaveIncomingStamp=false;SharingError.Reset();++ChangeSerial;
        World=Player->GetWorld(); Origin=World->OriginLocation;
        LogicalRegion.Reset(); Hills.Reset(); bSearchedHills=false;
    }
    if (Origin!=World->OriginLocation)
    {
        const FVector Shift=FVector(Origin)-FVector(World->OriginLocation);
        for (auto& M:Entries) M.Position+=Shift;
        for (auto& M:Received) M.Position+=Shift;
        Origin=World->OriginLocation; ++ChangeSerial;
        bHaveIncomingStamp=false;RebuildView();
        ClearBeams();
    }
    if (LayoutSerial!=Fog.LayoutSerial)
    {
        LayoutSerial=Fog.LayoutSerial;
        ++ChangeSerial;
        for (int32 I=Entries.Num()-1;I>=0;--I) if (Entries[I].bDungeon) Remove(Entries[I].Id);
    }
    APawn* Pawn=Player->GetPawn();
    const auto* State=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const FString Map=Pawn?UDungeonRoomSubsystem::LogicalMap(Pawn):FString();
    if (Map!=LogicalRegion) { LogicalRegion=Map; Hills.Reset(); bSearchedHills=false; }
    ActiveRegion=Map;
    if (!Pawn || (State && State->RoomTransferToken.IsValid())) ActiveRegion.Reset();
    else if (Map==TEXT("L_Dungeon_Randomized"))
    {
        const auto* Run=UDungeonRunSubsystem::Get(World.Get());
        if (bDungeonReady && Run) ActiveRegion+=TEXT("/")+Run->RunId();
        else ActiveRegion.Reset();
    }
    else
    {
        if (!bSearchedHills)
        {
            bSearchedHills=true;
            for (TActorIterator<ATemperateHillsWorld> It(World.Get());It;++It) { Hills=*It; break; }
        }
        if (const auto* Terrain=Hills.Get())
            ActiveRegion+=FString::Printf(TEXT("/%d/%s"),Terrain->Seed,*Terrain->WorldId.ToString());
    }
    RefreshSharing();
    // OnlyOwnerSee compares the primitive's owner chain with the rendered ViewActor,
    // which is GetViewTarget() (normally the pawn), not its PlayerController.
    AActor* ViewOwner=Player->GetViewTarget();
    bool bNeedsBeam=false;
    for (const auto& M:VisibleEntries)
    {
        const bool bVisible=ViewOwner && IsActive(M) && (!M.bDungeon || M.Floor==Fog.PlayerFloor);
        if (auto* Weak=Beams.Find(M.Id)) if (auto* Actor=Weak->Get())
        {
            // SetOwner refreshes owner-sensitive render state. Existing beams also
            // need rebinding after respawn, possession or a camera-target change.
            if (bVisible && Actor->GetOwner()!=ViewOwner) Actor->SetOwner(ViewOwner);
            Actor->SetActorHiddenInGame(!bVisible);
        }
        bNeedsBeam|=bVisible;
    }
    if (!bNeedsBeam) return;
    if (!BeamAssets) BeamAssets=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{BeamPath,PlanePath});
    if (!BeamAssets || !BeamAssets->HasLoadCompleted()) return;
    auto* Material=Cast<UMaterialInterface>(BeamPath.ResolveObject());
    auto* Plane=Cast<UStaticMesh>(PlanePath.ResolveObject());
    if (!Material || !Plane) return;
    FVector Eye; FRotator View; Player->GetPlayerViewPoint(Eye,View);
    for (const auto& M:VisibleEntries)
    {
        if (!IsActive(M) || (M.bDungeon && M.Floor!=Fog.PlayerFloor)) continue;
        AActor* Actor=Beams.FindRef(M.Id).Get();
        if (!Actor)
        {
            FActorSpawnParameters Spawn;
            Spawn.Owner=ViewOwner;
            Spawn.ObjectFlags|=RF_Transient;
            Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Actor=World->SpawnActor<AActor>(AActor::StaticClass(),M.Position,FRotator::ZeroRotator,Spawn);
            if (!Actor) continue;
            Actor->SetReplicates(false);
            Actor->SetActorTickEnabled(false);
            auto* Mesh=NewObject<UStaticMeshComponent>(Actor);
            Actor->SetRootComponent(Mesh);
            Actor->AddInstanceComponent(Mesh);
            Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetStaticMesh(Plane);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Mesh->SetGenerateOverlapEvents(false);
            Mesh->SetCanEverAffectNavigation(false);
            Mesh->SetCastShadow(false);
            Mesh->SetOnlyOwnerSee(true);
            Mesh->bVisibleInRayTracing=false;
            Mesh->bVisibleInReflectionCaptures=false;
            auto* MID=UMaterialInstanceDynamic::Create(Material,Actor);
            MID->SetVectorParameterValue(TEXT("LootColor"),Color(M.ColorIndex));
            MID->SetScalarParameterValue(TEXT("Intensity"),3.f);
            Mesh->SetMaterial(0,MID);
            Mesh->RegisterComponent();
            // Plane's local X becomes vertical; its bottom stays at the selected ground point.
            constexpr double Height=200000.;
            Actor->SetActorLocation(M.Position+FVector(0,0,Height*.5+3.));
            Actor->SetActorScale3D(FVector(Height/100.,.7,1.));
            Beams.Add(M.Id,Actor);
        }
        Actor->SetActorRotation(FRotator(90.,(Eye-M.Position).Rotation().Yaw,0.));
    }
}
