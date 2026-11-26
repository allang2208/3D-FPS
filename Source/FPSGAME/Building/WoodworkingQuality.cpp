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
double SkillBonus(double Score){return FMath::IsFinite(Score)?FMath::Clamp(Score,0.,100.)*MaxSkillBonus/100.:0.;}
double FromJob(const FColdSteelWoodworkingJob& Job)
{return Job.QualityVersion>=Version?1.+FMath::Clamp(Job.MaterialBonus,0.,MaxMaterialBonus)+SkillBonus(Job.Quality):FromScore(Job.Quality);}
bool UsesMaterials(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;double V=0;
    return Data&&Data->TryGetObjectField(Field,Q)&&Q&&*Q&&(*Q)->TryGetNumberField(TEXT("version"),V)&&V==Version;
}
double MaterialBonus(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;double Bonus=0;
    if(!UsesMaterials(Item)||!Data->TryGetObjectField(Field,Q)||!Q||!*Q||!(*Q)->TryGetNumberField(TEXT("materialBonus"),Bonus)||!FMath::IsFinite(Bonus))return 0;
    return FMath::Clamp(Bonus,0.,MaxMaterialBonus);
}
bool Read(const FColdSteelItem& Item,double& Score)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Data||!Data->TryGetObjectField(Field,Q)||!Q||!*Q)return false;
    double StoredVersion=0;FString Stat;
    return (*Q)->TryGetNumberField(TEXT("version"),StoredVersion)&&(StoredVersion==1||StoredVersion==ColdSteelWoodQuality::Version)
        &&(*Q)->TryGetNumberField(TEXT("score"),Score)&&FMath::IsFinite(Score)&&Score>=0&&Score<=100
        &&(*Q)->TryGetStringField(TEXT("stat"),Stat)&&Channel(Item)!=EChannel::None&&Stat==ChannelKey(Channel(Item));
}
double Multiplier(const FColdSteelItem& Item,EChannel Expected)
{double Score=0;if(Channel(Item)!=Expected||!Read(Item,Score))return 1.;return UsesMaterials(Item)?1.+MaterialBonus(Item)+SkillBonus(Score):FromScore(Score);}
FString StatLabel(const FColdSteelItem& Item)
{return Channel(Item)==EChannel::Physical?TEXT("物理伤害修正"):TEXT("法杖魔攻修正");}
bool Apply(FColdSteelItem& Item,double Score,double Bonus,FName Core,int32 QualityVersion)
{
    const auto Stat=Channel(Item);if(Stat==EChannel::None)return true; // Legacy component workpieces remain claimable.
    if(!FMath::IsFinite(Score)||!FMath::IsFinite(Bonus)||(QualityVersion!=1&&QualityVersion!=Version))return false;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    auto Q=MakeShared<FJsonObject>();Score=FMath::Clamp(Score,0.,100.);
    Q->SetNumberField(TEXT("version"),QualityVersion);Q->SetNumberField(TEXT("score"),Score);
    if(QualityVersion>=Version){Q->SetNumberField(TEXT("materialBonus"),FMath::Clamp(Bonus,0.,MaxMaterialBonus));Q->SetStringField(TEXT("core"),Core.ToString());}
    Q->SetNumberField(TEXT("multiplier"),QualityVersion>=Version?1.+FMath::Clamp(Bonus,0.,MaxMaterialBonus)+SkillBonus(Score):FromScore(Score));Q->SetStringField(TEXT("stat"),ChannelKey(Stat));
    Data->SetObjectField(Field,Q);Write(Item,Data);return true;
}
bool Apply(FColdSteelItem& Item,const FColdSteelWoodworkingJob& Job)
{return Apply(Item,Job.Quality,Job.MaterialBonus,Job.Core,Job.QualityVersion);}
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
