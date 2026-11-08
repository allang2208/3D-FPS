// Replacement definitions for the existing local host; do not compile as a separate translation unit.
#include "ColdSteelContainerSearchSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "ColdSteelSceneContainer.h"
#include "ColdSteelDungeonLoot.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemRarity.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

void UColdSteelContainerSearchSubsystem::ObserveChange(APlayerController* Player,const TArray<FColdSteelItem>& Before,const TArray<FColdSteelItem>& After)
{
    auto* Viewer=Viewers.Find(Player);if(!Viewer||!Viewer->Anchor.IsValid())return;
    if(Player&&Player->HasAuthority()&&Viewer->Anchor->ActorHasTag(TEXT("DungeonFinalTreasure")))
    {
        // This callback runs after a committed local/shared inventory change.
        // Compare quantities by definition, so sorting/merging/splitting stacks
        // cannot count as looting. Ammo converted to the ammo pool counts too.
        TMap<FString,int64> Counts;
        for(const auto& Item:Before)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)Counts.FindOrAdd(Item.Definition)+=Item.Count;
        for(const auto& Item:After)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)Counts.FindOrAdd(Item.Definition)-=Item.Count;
        for(const auto& Pair:Counts)if(Pair.Value>0)
        {if(auto* Run=UDungeonRunSubsystem::Get(GetWorld()))Run->MarkFinalTreasureLooted(Viewer->Anchor.Get(),Player);break;}
    }
    auto& Record=Viewer->Records.FindChecked(Viewer->Key);
    bool Learned=false;
    for(const auto& Item:After)if(Item.Place==4&&Canonical(Item.Container)==Viewer->Key)
        if(!Before.ContainsByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId&&I.Place==4&&Canonical(I.Container)==Viewer->Key;}))
        {Record.Revealed.Add(Item.InstanceId);Learned=true;}
    Reconcile(Record,Viewer->Key,After);
    if(Learned&&GetWorld()->GetNetMode()==NM_Standalone)Notify(Player,Viewer->Anchor.Get());
}
