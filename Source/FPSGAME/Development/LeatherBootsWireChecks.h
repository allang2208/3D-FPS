#pragma once
#include "../UI/ColdSteelPickup.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"

// Additional assertions for the opt-in wardrobe wire fixture. No normal-play path calls these.
namespace LeatherBootsWire
{
inline bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("LeatherBootsWireAudit"));}
inline TSharedPtr<FJsonObject> Expected()
{
    static TSharedPtr<FJsonObject> Root;
    if(!Root){FString Path,Json;if(FParse::Value(FCommandLine::Get(),TEXT("LeatherBootsWireExpected="),Path)&&FFileHelper::LoadFileToString(Json,*Path))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root);}
    return Root;
}
inline FString Path(const TCHAR* Key)
{auto Root=Expected();FString Value;if(Root)Root->TryGetStringField(Key,Value);return Value;}
inline FString Pants(int32 Mask)
{return Path((Mask&2)?((Mask&16)?TEXT("pants_robe_boots"):TEXT("pants_robe")):((Mask&16)?TEXT("pants_boots"):TEXT("pants")));}
inline FString Boots(int32 Mask){return Path((Mask&2)?TEXT("boots_robe"):TEXT("boots"));}
inline FString Shirt(int32 Mask){return Mask==0||(Mask&2)?FString():Path((Mask&8)?((Mask&16)?TEXT("shirt_pants_boots"):TEXT("shirt_pants")):TEXT("shirt"));}
inline bool IsPants(const FString& Asset)
{return Asset.Contains(TEXT("/ue_leather_pants/"))||Asset==Pants(31)||Asset==Pants(15)||Asset==Pants(29)||Asset==Pants(13);}
inline bool IsBoots(const FString& Asset){return Asset.Contains(TEXT("/ue_leather_boots/"));}
inline bool IsShirt(const FString& Asset){return Asset.Contains(TEXT("/ue_field_sweater/"));}
inline bool SameDisplay(UStaticMesh* Actual,UStaticMesh* Current)
{
    if(!Actual||!Current||Actual->GetNumTriangles(0)!=Current->GetNumTriangles(0)||Actual->GetStaticMaterials().Num()!=Current->GetStaticMaterials().Num())return false;
    for(int32 I=0;I<Current->GetStaticMaterials().Num();++I)if(Actual->GetMaterial(I)!=Current->GetMaterial(I))return false;
    return Actual->GetBounds().BoxExtent.Equals(Current->GetBounds().BoxExtent,.01);
}
inline void SpawnLegacyDrop(UColdSteelStatusModel* Model,UWorld* World)
{
    if(!Enabled())return;
    auto Item=Model->CreateItem(TEXT("ue_leather_boots"));Item.InstanceId=TEXT("LeatherBootsAuditLegacyDrop");Item.Place=2;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);if(!Data)return;
    Data->SetStringField(TEXT("world_mesh"),Path(TEXT("legacy_pickup")));Data->SetStringField(TEXT("ue_equipment_icon_mesh"),Path(TEXT("legacy_icon")));
    Data->SetNumberField(TEXT("enhanceLevel"),7);Data->SetStringField(TEXT("leather_wire_sentinel"),TEXT("preserve-instance"));
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    auto* Drop=World->SpawnActor<AColdSteelPickup>(FVector(500,500,500),FRotator::ZeroRotator);
    if(Drop){Drop->InitializeSharedItem(Item);Drop->Body->SetSimulatePhysics(false);Drop->Body->SetEnableGravity(false);}
}
inline bool LegacyDrop(UWorld* World,FString& Details)
{
    if(!Enabled())return true;
    bool DataOK=false,MeshOK=false,IconOK=false;
    for(TActorIterator<AColdSteelPickup> It(World);It;++It)
    {
        if(It->ItemId!=TEXT("LeatherBootsAuditLegacyDrop"))continue;
        const auto* Property=FindFProperty<FStructProperty>(AColdSteelPickup::StaticClass(),TEXT("SharedItem"));if(!Property)break;
        const auto& Item=*Property->ContainerPtrToValuePtr<FColdSteelItem>(*It);
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        FString Sentinel,MeshPath,IconPath;double Level=0;
        DataOK=Data&&Data->TryGetStringField(TEXT("leather_wire_sentinel"),Sentinel)&&Sentinel==TEXT("preserve-instance")&&Data->TryGetNumberField(TEXT("enhanceLevel"),Level)&&Level==7&&Item.Definition==TEXT("ue_leather_boots")&&Item.Count==1;
        if(Data){Data->TryGetStringField(TEXT("world_mesh"),MeshPath);Data->TryGetStringField(TEXT("ue_equipment_icon_mesh"),IconPath);}
        auto* Current=LoadObject<UStaticMesh>(nullptr,*Path(TEXT("pickup")));TArray<UStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components)if(Component->GetStaticMesh()&&Component->GetStaticMesh()->GetPathName()==MeshPath)MeshOK|=SameDisplay(Component->GetStaticMesh(),Current);
        IconOK=IconPath==Path(TEXT("legacy_icon"))&&SameDisplay(LoadObject<UStaticMesh>(nullptr,*IconPath),LoadObject<UStaticMesh>(nullptr,*Path(TEXT("icon"))));
        DataOK&=MeshPath==Path(TEXT("legacy_pickup"));break;
    }
    Details=FString::Printf(TEXT("legacy_drop data=%d mesh=%d icon=%d"),DataOK,MeshOK,IconOK);return DataOK&&MeshOK&&IconOK;
}
}
