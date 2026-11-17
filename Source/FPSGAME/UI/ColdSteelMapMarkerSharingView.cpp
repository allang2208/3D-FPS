#include "ColdSteelMapMarkers.h"
#include "../Multiplayer/ColdSteelMapMarkerSharing.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"

void FColdSteelMapMarkers::RebuildView()
{
    VisibleEntries=Entries;
    for(const auto& Marker:Received)
        if(!Entries.ContainsByPredicate([&](const auto& Own){return Own.Id==Marker.Id;}))VisibleEntries.Add(Marker);
}

void FColdSteelMapMarkers::SendShare(const FColdSteelMapMarker& Marker,bool bWasShared)
{
    auto* Network=UColdSteelMapMarkerSharing::For(Owner.Get());
    if(!Network)return;
    if(Sharing.Get()!=Network)
    {
        if(!Sharing.IsExplicitlyNull())for(auto& Entry:Entries)
            if(Entry.Id!=Marker.Id)Entry.Visibility=EColdSteelMapMarkerVisibility::Personal;
        Sharing=Network;PendingShares.Reset();bHaveIncomingStamp=false;
    }
    if(Marker.Visibility==EColdSteelMapMarkerVisibility::Team)PendingShares.Add(Marker.Id,Network->Publish(Marker));
    else if(bWasShared)PendingShares.Add(Marker.Id,Network->Withdraw(Marker.Id));
}

void FColdSteelMapMarkers::RefreshSharing()
{
    auto* Player=Owner.Get();
    auto* Network=UColdSteelMapMarkerSharing::For(Player);
    if(Sharing.Get()!=Network)
    {
        // Initial late PlayerState binding retains private data; a replacement cannot resurrect old shares.
        if(!Sharing.IsExplicitlyNull())for(auto& Marker:Entries)Marker.Visibility=EColdSteelMapMarkerVisibility::Personal;
        Sharing=Network;PendingShares.Reset();bHaveIncomingStamp=false;RebuildView();++ChangeSerial;
    }
    if(Network)
    {
        TArray<FColdSteelMapShareResult> Results;
        Network->TakeResults(Results);
        for(const auto& Result:Results)
        {
            const auto* Pending=PendingShares.Find(Result.Id);
            if(!Pending||*Pending!=Result.Request)continue;
            PendingShares.Remove(Result.Id);
            if(!Result.bAccepted)if(auto* Marker=Entries.FindByPredicate([&](const auto& Item){return Item.Id==Result.Id;}))
            {
                Marker->Visibility=EColdSteelMapMarkerVisibility::Personal;
                SharingError=Result.Reason+TEXT("，已保留为仅本人标记");
                RebuildView();++ChangeSerial;
            }
        }
    }
    const auto* GameState=World.IsValid()?World->GetGameState():nullptr;
    const auto* OwnState=Player?Player->GetPlayerState<APlayerState>():nullptr;
    uint32 Stamp=0;
    if(GameState)for(const auto& State:GameState->PlayerArray)
    {
        if(!State||State==OwnState||State->IsInactive())continue;
        const auto* Peer=State->FindComponentByClass<UColdSteelMapMarkerSharing>();
        if(!Peer)continue;
        Stamp=HashCombineFast(Stamp,GetTypeHash(State.Get()));
        Stamp=HashCombineFast(Stamp,Peer->Revision());
        Stamp=HashCombineFast(Stamp,GetTypeHash(State->GetPlayerName()));
    }
    if(bHaveIncomingStamp&&Stamp==IncomingStamp)return;
    bHaveIncomingStamp=true;IncomingStamp=Stamp;
    TArray<FColdSteelMapMarker> Next;
    if(GameState)for(const auto& State:GameState->PlayerArray)
    {
        if(!State||State==OwnState||State->IsInactive())continue;
        const auto* Peer=State->FindComponentByClass<UColdSteelMapMarkerSharing>();
        if(!Peer)continue;
        for(const auto& Wire:Peer->Shared())
        {
            FColdSteelMapMarker Marker;
            Marker.Id=Wire.Id;Marker.Region=Wire.Region;Marker.Area=Wire.Area;Marker.Label=Wire.Label;
            Marker.Position=Wire.AbsolutePosition-FVector(World->OriginLocation);
            Marker.Floor=Wire.Floor;Marker.ColorIndex=Wire.ColorIndex;Marker.bDungeon=Wire.bDungeon;
            Marker.Visibility=EColdSteelMapMarkerVisibility::Team;Marker.bReadOnly=true;Marker.OwnerName=State->GetPlayerName();
            Next.Add(MoveTemp(Marker));
        }
    }
    for(const auto& Before:Received)
    {
        const auto* After=Next.FindByPredicate([&](const auto& Item){return Item.Id==Before.Id;});
        if(!After||After->Position!=Before.Position||After->ColorIndex!=Before.ColorIndex)DestroyBeam(Before.Id);
    }
    Received=MoveTemp(Next);RebuildView();++ChangeSerial;
}
