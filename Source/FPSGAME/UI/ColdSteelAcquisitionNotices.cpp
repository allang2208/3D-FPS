#include "ColdSteelStatusModel.h"
#include "ColdSteelItemRarity.h"
#include "ColdSteelUIStyle.h"
using namespace ColdSteelInventory;

namespace
{
bool AcquisitionOwned(const FColdSteelItem& Item)
{
    // A displayed network chest is a view, never part of the player's possessions.
    return Item.Count>0&&!Item.bIncineratorAmmo&&!Item.Container.StartsWith(TEXT("NetView."))
        &&(Item.Place==0||Item.Place==1||Item.Place==5||(Item.Place==4&&Item.Container.IsEmpty()));
}
FString AcquisitionRarity(const FColdSteelItem& Item)
{
    return ColdSteelItemRarity::IsEquipment(Item)?FString():Text(Item,TEXT("rarity"));
}
}

void UColdSteelStatusModel::SetAcquisitionFeedEnabled(bool Enabled)
{
    bAcquisitionFeedEnabled=Enabled;ResetAcquisitionNotices();
}
void UColdSteelStatusModel::ResetAcquisitionNotices(){AcquisitionNotices.Reset();++AcquisitionEpoch;}
bool UColdSteelStatusModel::PopAcquisitionNotice(FColdSteelAcquisitionNotice& Out,const FString& MatchKey)
{
    if(AcquisitionNotices.IsEmpty())return false;
    const int32 Index=MatchKey.IsEmpty()?0:AcquisitionNotices.IndexOfByPredicate([&](const auto& E){return E.Key==MatchKey;});
    if(Index==INDEX_NONE)return false;
    Out=MoveTemp(AcquisitionNotices[Index]);AcquisitionNotices.RemoveAt(Index);return true;
}
void UColdSteelStatusModel::EnqueueAcquisition(FColdSteelAcquisitionNotice Notice)
{
    if(Notice.Count<=0||Notice.Name.IsEmpty())return;
    if(auto* Existing=AcquisitionNotices.FindByPredicate([&](const auto& E){return E.Key==Notice.Key;}))
    {Existing->Count+=Notice.Count;return;}
    // Coalesce by catalog item/rarity; never discard an unshown gain during a burst.
    AcquisitionNotices.Add(MoveTemp(Notice));
}
void UColdSteelStatusModel::QueueAcquisitionNotices(const FColdSteelProfile& Before,const FColdSteelProfile& After)
{
    if(!bAcquisitionFeedEnabled||bNetShadowProfile||bAudit||Before.NetworkProfileId!=After.NetworkProfileId)return;
    // Compare instance payloads before reading rarity. Sorting/equipping and
    // ordinary saves stay cheap, while swapping equal counts of different
    // rarities still announces the newly acquired variant.
    TMap<FString,const FColdSteelItem*> Previous;
    for(const auto& I:Before.Items)if(AcquisitionOwned(I))Previous.Add(I.InstanceId,&I);
    TSet<FString> Gained;
    for(const auto& I:After.Items)if(AcquisitionOwned(I))
    {
        const auto* Old=Previous.FindRef(I.InstanceId);
        if(!Old||Old->Definition!=I.Definition||Old->Count!=I.Count||Old->Data!=I.Data)Gained.Add(I.Definition);
    }
    if(!Gained.IsEmpty())
    {
        TMap<FString,int64> BeforeVariants,AfterVariants;
        TArray<FColdSteelAcquisitionNotice> Ordered;
        for(const auto& I:Before.Items)if(AcquisitionOwned(I)&&Gained.Contains(I.Definition))
            BeforeVariants.FindOrAdd(I.Definition+TEXT("|")+AcquisitionRarity(I))+=I.Count;
        for(const auto& I:After.Items)if(AcquisitionOwned(I)&&Gained.Contains(I.Definition))
        {
            const FString Rarity=AcquisitionRarity(I),Key=I.Definition+TEXT("|")+Rarity;
            if(!AfterVariants.Contains(Key))
            {
                FString Name=Text(I,TEXT("name"));if(Name.IsEmpty())Name=I.Definition;
                Ordered.Add({Key,Name,0,Rarity.IsEmpty()?ColdSteelUI::TextPrimary:ColdSteelUI::RarityColor(Rarity)});
            }
            AfterVariants.FindOrAdd(Key)+=I.Count;
        }
        for(auto& Notice:Ordered)
        {Notice.Count=AfterVariants.FindRef(Notice.Key)-BeforeVariants.FindRef(Notice.Key);EnqueueAcquisition(MoveTemp(Notice));}
    }
    // Ammo lives in a pouch. Include owned live rounds so unloading a magazine is not a gain.
    for(const auto& Pair:After.AmmoPouch)
    {
        if(Pair.Value<=Before.AmmoPouch.FindRef(Pair.Key))continue;
        auto OwnedAmmo=[&](const FColdSteelProfile& Profile)
        {
            int64 Total=Profile.AmmoPouch.FindRef(Pair.Key);
            for(const auto& I:Profile.Items)
                if(AcquisitionOwned(I)&&WeaponAmmoGroups.Contains(I.Definition)&&AmmoDefinitionFor(I)==Pair.Key)
                    Total+=FMath::Max(0,I.Magazine-I.VirtualMagazineAmmo);
            return Total;
        };
        const int64 Gain=OwnedAmmo(After)-OwnedAmmo(Before);
        const auto* Type=AmmoType(Pair.Key);
        if(Gain>0&&Type)EnqueueAcquisition({TEXT("ammo|")+Pair.Key,AmmoLabel(Pair.Key),Gain,
            Type->TierColor.A>0?Type->TierColor:ColdSteelUI::TextPrimary});
    }
}
