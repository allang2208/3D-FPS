#include "ColdSteelStatusModel.h"
#include "../Movement/StableHorseGear.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"

namespace
{
bool ReturnToBag(TArray<FColdSteelItem>& Items,FColdSteelItem Gear,const TOptional<FColdSteelItem>& Replacement)
{
    using namespace ColdSteelInventory;
    Gear.Container.Reset();
    // A full bag can still exchange two pieces using the compartment cell just vacated.
    const FIntPoint Grid=CompartmentGrid(Items);
    if(Replacement.IsSet() && Replacement->Place==ColdSteelCompartment::Place &&
       ColdSteelCompartment::Fits(Items,Gear,Replacement->Cell,Grid))
    {
        Gear.Place=ColdSteelCompartment::Place;
        Gear.Cell=Replacement->Cell;Items.Add(MoveTemp(Gear));
        return true;
    }
    Gear.Place=0;
    const int32 Preferred=Replacement.IsSet() && Replacement->Place==0?Replacement->Cell:Gear.BackpackCell;
    if(Insert(Items,Gear,Preferred))return true;
    ApplyOrientation(Gear,Gear.bRotated?0:1);
    if(Insert(Items,Gear))return true;
    Gear.Place=ColdSteelCompartment::Place;
    for(int32 Orientation=0;Orientation<2;++Orientation)
    {
        ApplyOrientation(Gear,Orientation);
        for(int32 Cell=0;Cell<Grid.X*Grid.Y;++Cell)
            if(ColdSteelCompartment::Fits(Items,Gear,Cell,Grid))
            {Gear.Cell=Cell;Items.Add(MoveTemp(Gear));return true;}
    }
    return false;
}
}

bool UColdSteelStatusModel::ChangeMountGear(FGuid HorseId,int32 Slot,const FString& ItemId,bool Equip,FString& Reason)
{
    using namespace ColdSteelInventory;
    auto* Pawn=RuntimePawn();
    if(!Pawn || !Pawn->HasAuthority() || Slot<0 || Slot>=StableHorseGear::Count || ItemId.IsEmpty())
    {Reason=TEXT("马具操作无效");return false;}
    auto Next=Snapshot();
    auto* Horse=Next.MountRoster.Find(HorseId);
    if(!Horse){Reason=TEXT("马匹不在当前名册");return false;}
    const int32 Worn=Horse->Equipment.IndexOfByPredicate([Slot](const auto& Item){return StableHorseGear::SlotOf(Item.Definition)==Slot;});
    TOptional<FColdSteelItem> Incoming;
    if(Equip)
    {
        const int32 Index=Next.Items.IndexOfByPredicate([&](const auto& Item){return Item.InstanceId==ItemId;});
        if(Index==INDEX_NONE){Reason=TEXT("马具已移走");return false;}
        const auto& Item=Next.Items[Index];
        if((Item.Place!=0 && Item.Place!=ColdSteelCompartment::Place) || Item.Count!=1 || StableHorseGear::SlotOf(Item.Definition)!=Slot)
        {Reason=TEXT("请选择随身背包里与该部位匹配的马具");return false;}
        Incoming=Item;
        Next.Items.RemoveAt(Index);
        for(auto& Binding:Next.QuickBindings)if(Binding.ItemId==ItemId)Binding=FColdSteelQuickBinding();
        for(int32 I=0;I<Next.Hotbar.Num();++I)
            if(Next.Hotbar[I]==ItemId)
            {
                Next.Hotbar[I].Reset();
                if(Next.HotbarDefinitions.IsValidIndex(I))Next.HotbarDefinitions[I].Reset();
            }
    }
    else if(Worn==INDEX_NONE || Horse->Equipment[Worn].InstanceId!=ItemId)
    {Reason=TEXT("该装备位已变化");return false;}
    if(Worn!=INDEX_NONE)
    {
        if(!ReturnToBag(Next.Items,Horse->Equipment[Worn],Incoming))
        {Reason=TEXT("背包空间不足，马具仍穿戴在马上");return false;}
        Horse->Equipment.RemoveAt(Worn);
    }
    if(Incoming.IsSet())
    {
        auto& Item=Incoming.GetValue();
        Item.BackpackCell=Item.Place==0?Item.Cell:INDEX_NONE;
        Item.Container.Reset();Item.Cell=INDEX_NONE;Item.Place=0;
        Horse->Equipment.Add(MoveTemp(Item));
    }
    ++Next.MountRoster.Revision;
    const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    if(bNetShadowProfile && (!PS || PS->CampfireGuestSlot().IsEmpty())){Reason=TEXT("角色档案尚未就绪");return false;}
    if(!CommitCampfireState(MoveTemp(Next),TEXT("MountGear"),bNetShadowProfile?PS->CampfireGuestSlot():FString()))
    {Reason=ResultMessage();return false;}
    Reason=Equip?TEXT("已装上马具"):TEXT("马具已放回背包");return true;
}
