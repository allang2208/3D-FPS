#include "KukriModuleVisual.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../ModularSwordVisual.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Misc/Crc.h"

namespace {const FString RequestPrefix=TEXT("KukriModuleRequest=");}

void FKukriModuleVisual::Clear(UStaticMeshComponent* Root)
{
    if(Load){Load->CancelHandle();Load.Reset();}
    ItemId.Reset();ItemData.Reset();
    TraceBase=KukriRhythm::BladeRoot;TraceTip=KukriRhythm::BladeTip;
    if(!Root)return;
    Root->ComponentTags.RemoveAll([](FName Tag){return Tag.ToString().StartsWith(RequestPrefix);});
    ColdSteelModularSword::Clear(Root);
}

void FKukriModuleVisual::Refresh(UStaticMeshComponent* Root,const FColdSteelItem* Item)
{
    if(!Root)return;
    if(!Item){Clear(Root);return;}
    if(ItemId==Item->InstanceId&&ItemData==Item->Data)return;
    if(Load){Load->CancelHandle();Load.Reset();}
    ItemId=Item->InstanceId;ItemData=Item->Data;
    TraceBase=KukriRhythm::BladeRoot;TraceTip=KukriRhythm::BladeTip;
    if(ColdSteelModularSword::Supports(*Item))
    {
        TraceBase=ColdSteelModularSword::BladePoint(*Item,false);
        TraceTip=ColdSteelModularSword::BladePoint(*Item,true);
    }
    const FName Request(*(RequestPrefix+ItemId+FString::Printf(TEXT(":%08x"),FCrc::StrCrc32(*ItemData))));
    Root->ComponentTags.RemoveAll([](FName Tag){return Tag.ToString().StartsWith(RequestPrefix);});
    Root->ComponentTags.Add(Request);
    TArray<FSoftObjectPath> Paths;ColdSteelModularSword::GatherVisualResources(*Item,Paths);
    const auto Apply=[Weak=TWeakObjectPtr<UStaticMeshComponent>(Root),Snapshot=*Item,Request]()
    {
        if(auto* Target=Weak.Get();Target&&Target->ComponentHasTag(Request))
            ColdSteelModularSword::Apply(Target,Snapshot);
    };
    if(Paths.ContainsByPredicate([](const FSoftObjectPath& Path){return !Path.ResolveObject();}))
        Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateLambda(Apply));
    else Apply();
}
