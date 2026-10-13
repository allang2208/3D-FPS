#include "WoodworkingQuality.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelWoodQuality
{
namespace
{
constexpr const TCHAR* Field=TEXT("_woodworkingQuality");
const TCHAR* ChannelKey(EChannel Value)
{return Value==EChannel::Physical?TEXT("physical"):Value==EChannel::MagicAttack?TEXT("magicAttack"):TEXT("");}
void Write(FColdSteelItem& Item,const TSharedPtr<FJsonObject>& Data)
{Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));}
}
EChannel Channel(const FColdSteelItem& Item)
{
    if(ColdSteelInventory::IsBow(Item))return EChannel::Physical;
    return ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("staff")?EChannel::MagicAttack:EChannel::None;
}
double FromScore(double Score)
{return FMath::IsFinite(Score)?.75+.005*FMath::Clamp(Score,0.,100.):1.;}
bool Read(const FColdSteelItem& Item,double& Score)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Data||!Data->TryGetObjectField(Field,Q)||!Q||!*Q)return false;
    double Version=0;FString Stat;
    return (*Q)->TryGetNumberField(TEXT("version"),Version)&&Version==1
        &&(*Q)->TryGetNumberField(TEXT("score"),Score)&&FMath::IsFinite(Score)&&Score>=0&&Score<=100
        &&(*Q)->TryGetStringField(TEXT("stat"),Stat)&&Channel(Item)!=EChannel::None&&Stat==ChannelKey(Channel(Item));
}
double Multiplier(const FColdSteelItem& Item,EChannel Expected)
{double Score=0;return Channel(Item)==Expected&&Read(Item,Score)?FromScore(Score):1.;}
FString StatLabel(const FColdSteelItem& Item)
{return Channel(Item)==EChannel::Physical?TEXT("物理伤害修正"):TEXT("法杖魔攻修正");}
bool Apply(FColdSteelItem& Item,double Score)
{
    const auto Stat=Channel(Item);if(Stat==EChannel::None)return true; // Legacy component workpieces remain claimable.
    if(!FMath::IsFinite(Score))return false;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    auto Q=MakeShared<FJsonObject>();Score=FMath::Clamp(Score,0.,100.);
    Q->SetNumberField(TEXT("version"),1);Q->SetNumberField(TEXT("score"),Score);
    Q->SetNumberField(TEXT("multiplier"),FromScore(Score));Q->SetStringField(TEXT("stat"),ChannelKey(Stat));
    Data->SetObjectField(Field,Q);Write(Item,Data);return true;
}
void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority)
{
    TMap<FString,const FColdSteelItem*> ById;ById.Reserve(Authority.Num());
    for(const auto& Item:Authority)ById.Add(Item.InstanceId,&Item);
    for(auto& Item:Incoming)
    {
        const auto* Found=ById.Find(Item.InstanceId);if(!Found)continue;
        const auto& Known=**Found;
        if(!Known.Data.Contains(Field)&&!Item.Data.Contains(Field))continue;
        const auto Before=ColdSteelItemData::Read(Known.Data),After=ColdSteelItemData::Read(Item.Data);
        if(!Before||!After)continue;
        const auto Trusted=Before->TryGetField(Field),Uploaded=After->TryGetField(Field);
        if((!Trusted&&!Uploaded)||(Trusted&&Uploaded&&FJsonValue::CompareEqual(*Trusted,*Uploaded)))continue;
        TSharedPtr<FJsonObject> Editable;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Editable)||!Editable)continue;
        if(Trusted)Editable->SetField(Field,Trusted);else Editable->RemoveField(Field);
        Write(Item,Editable);
    }
}
}
