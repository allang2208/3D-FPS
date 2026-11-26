#include "ForgingQuality.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelForgeQuality
{
namespace
{
constexpr const TCHAR* Field=TEXT("_forgeQuality");
void Write(FColdSteelItem& Item,const TSharedPtr<FJsonObject>& Data)
{Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));}
}
double HitBonus(int32 Hits)
{return BonusPerHit*FMath::Clamp(Hits,0,TargetCount);}
double FromHits(int32 Hits,double MaterialBonus)
{return 1.+FMath::Clamp(MaterialBonus,0.,MaxMaterialBonus)+HitBonus(Hits);}
double Multiplier(const FColdSteelForgeJob& Job)
{
    // A paid legacy workpiece keeps the rules under which it was started.
    return Job.QualityVersion>=Version?FromHits(Job.Hits,Job.MaterialBonus)
        :.75+.5*FMath::Clamp(Job.Hits,0,TargetCount)/TargetCount;
}
double Multiplier(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Data||!Data->TryGetObjectField(Field,Q)||!Q||!*Q)return 1.;
    double SmithPercent=0.;
    if((*Q)->TryGetNumberField(TEXT("blacksmithPercent"),SmithPercent))
        return FMath::IsFinite(SmithPercent)?1.+.01*FMath::Clamp(SmithPercent,double(SmithMinPercent),double(SmithMaxPercent)):1.;
    double SavedVersion=0;(*Q)->TryGetNumberField(TEXT("version"),SavedVersion);
    if(SavedVersion>=Version)
    {
        double Hits=0,Material=0;
        if(!(*Q)->TryGetNumberField(TEXT("hits"),Hits)||!FMath::IsFinite(Hits)
            ||!(*Q)->TryGetNumberField(TEXT("materialBonus"),Material)||!FMath::IsFinite(Material))return 1.;
        return FromHits(int32(FMath::Clamp(Hits,0.,double(TargetCount))),Material);
    }
    double Value=1.;(*Q)->TryGetNumberField(TEXT("multiplier"),Value);
    return FMath::IsFinite(Value)?FMath::Clamp(Value,.75,1.25):1.;
}
FString Label(int32 Hits)
{
    if(Hits>=20)return TEXT("完美");if(Hits>=18)return TEXT("精工");if(Hits>=14)return TEXT("精良");
    if(Hits>=10)return TEXT("合格");if(Hits>=5)return TEXT("普通");return TEXT("粗制");
}
bool Apply(FColdSteelItem& Item,const FColdSteelForgeJob& Job)
{
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    auto Q=MakeShared<FJsonObject>();Q->SetNumberField(TEXT("hits"),FMath::Clamp(Job.Hits,0,TargetCount));
    Q->SetNumberField(TEXT("total"),TargetCount);Q->SetNumberField(TEXT("multiplier"),Multiplier(Job));
    Q->SetStringField(TEXT("label"),Label(Job.Hits));
    if(Job.QualityVersion>=Version)
    {
        Q->SetNumberField(TEXT("version"),Version);Q->SetStringField(TEXT("metal"),Job.Metal.ToString());
        Q->SetStringField(TEXT("materialName"),Job.MaterialName);
        Q->SetNumberField(TEXT("materialBonus"),FMath::Clamp(Job.MaterialBonus,0.,MaxMaterialBonus));
        Q->SetNumberField(TEXT("hitBonus"),HitBonus(Job.Hits));
    }
    Data->SetObjectField(Field,Q);Write(Item,Data);return true;
}
bool ApplyBlacksmithOffer(FColdSteelItem& Item,int32 QualityPercent)
{
    TSharedPtr<FJsonObject> Data;
    if(QualityPercent<SmithMinPercent||QualityPercent>SmithMaxPercent||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    auto Q=MakeShared<FJsonObject>();
    Q->SetNumberField(TEXT("blacksmithPercent"),QualityPercent);
    Q->SetStringField(TEXT("label"),TEXT("铁匠成品"));
    Data->SetObjectField(Field,Q);Write(Item,Data);
    return true;
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
