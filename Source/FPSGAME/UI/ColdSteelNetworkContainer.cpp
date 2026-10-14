#include "ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelHUDWidget.h"
#include "../Monsters/FPSCombatHealthComponent.h"

void UColdSteelStatusModel::StripNetworkContainerView(FColdSteelProfile& Profile)
{
    Profile.Items.RemoveAll([](const auto& I){return I.Container.StartsWith(TEXT("NetView."));});
    for(auto It=Profile.StoragePages.CreateIterator();It;++It)
        if(It.Key().StartsWith(TEXT("NetView.")))It.RemoveCurrent();
}
bool UColdSteelStatusModel::HasNetworkContainerView() const
{
    return !bStagingNetworkContainer&&ActiveContainer.StartsWith(TEXT("NetView."));
}
bool UColdSteelStatusModel::RequestContainerOperation(uint8 Action,const FString& Item,int32 Place,int32 Cell,int32 Orientation,int64 Count,const FString& Mode)
{
    auto* PS=CurrentPawn.IsValid()?CurrentPawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!PS||!NetworkContainerAnchor.IsValid())return false;
    FColdSteelInventoryRequest Request;Request.Action=static_cast<EColdSteelInventoryAction>(Action);
    Request.Target=NetworkContainerAnchor.Get();Request.ContainerRevision=NetworkContainerRevision;
    Request.Item=Item;Request.Place=Place;Request.Cell=Cell;Request.Orientation=Orientation;Request.Count=Count;
    Request.Page=WarehousePage;Request.Mode=Mode;
    if(Request.Action==EColdSteelInventoryAction::ContainerOpen)Request.Count=-1; // refresh an existing panel
    return PS->RequestInventoryAction(Request);
}
void UColdSteelStatusModel::ApplyNetworkContainerView(const UColdSteelInventoryReply* Reply,AActor* Anchor)
{
    if(!Reply||!Reply->bContainerView||!IsValid(Anchor)||!CurrentPawn.IsValid())return;
    if(const auto* Health=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(FVector::DistSquared(CurrentPawn->GetActorLocation(),Anchor->GetActorLocation()+FVector(0,0,70))>FMath::Square(250.f))return;
    auto State=Snapshot();StripNetworkContainerView(State);
    const FString ViewKey=TEXT("NetView.")+Reply->ContainerKey;
    State.StoragePages.Add(ViewKey,Reply->ContainerPages);
    for(auto Item:Reply->ContainerItems){Item.Container=ViewKey;State.Items.Add(MoveTemp(Item));}
    AdoptNetMirror(State);NetworkContainerAnchor=Anchor;NetworkContainerRevision=Reply->ContainerRevision;
    ActiveContainer=ViewKey;ActiveStorageCaption=Reply->ContainerCaption;
    if(auto* PC=Cast<AFPSGAMEPlayerController>(CurrentPawn->GetController()))
        if(auto* HUD=PC->GetColdSteelHUD())HUD->OpenChestLootStorage(Anchor,ViewKey,Reply->ContainerPages,Reply->ContainerCaption);
    OnChanged.Broadcast();
}
