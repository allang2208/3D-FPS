#include "GunAssemblyQuality.h"
#include "GunAssemblyCalibration.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelAssemblyQuality
{
namespace
{
constexpr const TCHAR* Field=TEXT("_assemblyQuality");
double FiniteNumber(const TSharedPtr<FJsonObject>& Data,const TCHAR* Key,double Fallback=0.)
{double Value=Fallback;Data->TryGetNumberField(Key,Value);return FMath::IsFinite(Value)?Value:Fallback;}
void Write(FColdSteelItem& Item,const TSharedPtr<FJsonObject>& Data)
{Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));}
}
double Score(const FColdSteelGunAssemblyJob& Job)
{
    if(Job.bFinished)return FMath::Clamp(double(Job.Quality),0.,100.);
    double Sum=0;for(float Value:Job.Scores)Sum+=Value;
    const double Fit=Sum/FMath::Max(1,Job.PartCount);
    // Calibration is earned as it progresses; an untouched workpiece starts at its metal floor.
    const bool Rounds=Job.CalibrationVersion>=GunAssemblyCalibration::FirstRoundsVersion;
    const double Progress=FMath::Clamp(double(Job.CalibrationSeconds)/FMath::Max(.01,Rounds?double(GunAssemblyCalibration::ScoringSeconds):double(Job.CalibrationDuration)),0.,1.);
    const double Error=FMath::Clamp(double(Job.CalibrationError)/FMath::Max(.01,Rounds?double(GunAssemblyCalibration::ActiveElapsed(Job.CalibrationTime,Job.CalibrationVersion)):double(Job.CalibrationTime)),0.,1.);
    return FMath::Clamp(.7*Fit+.3*100.*Progress*(1.-.65*Error),0.,100.);
}
double SkillBonus(double Value){return FMath::Clamp(Value,0.,100.)*MaxSkillBonus/100.;}
double MaterialBonus(const FColdSteelGunAssemblyJob& Job)
{return Job.QualityVersion>=Version?FMath::Clamp(Job.MaterialBonus,0.,MaxMaterialBonus):0.;}
double MaterialBonus(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Data||!Data->TryGetObjectField(Field,Q)||!Q||!*Q)return 0.;
    return FiniteNumber(*Q,TEXT("version"))>=Version?FMath::Clamp(FiniteNumber(*Q,TEXT("materialBonus")),0.,MaxMaterialBonus):0.;
}
double Multiplier(const FColdSteelGunAssemblyJob& Job){return 1.+MaterialBonus(Job)+SkillBonus(Score(Job));}
double Multiplier(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Data||!Data->TryGetObjectField(Field,Q)||!Q||!*Q)return 1.;
    // Existing firearms retain their earned score; unrecorded materials grant no invented floor.
    const double Base=FiniteNumber(*Q,TEXT("version"))>=Version?FMath::Clamp(FiniteNumber(*Q,TEXT("materialBonus")),0.,MaxMaterialBonus):0.;
    return 1.+Base+SkillBonus(FiniteNumber(*Q,TEXT("score")));
}
bool Apply(FColdSteelItem& Item,const FColdSteelGunAssemblyJob& Job)
{
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return false;
    const double Value=Score(Job);auto Q=MakeShared<FJsonObject>();
    Q->SetNumberField(TEXT("version"),Version);Q->SetNumberField(TEXT("score"),Value);
    Q->SetStringField(TEXT("label"),Value>=90?TEXT("精工"):Value>=75?TEXT("优良"):Value>=55?TEXT("合格"):TEXT("粗制"));
    Q->SetStringField(TEXT("metal"),Job.QualityVersion>=Version?Job.Metal.ToString():FString());
    Q->SetStringField(TEXT("materialName"),Job.QualityVersion>=Version?Job.MaterialName:TEXT("旧制工件"));
    Q->SetNumberField(TEXT("materialBonus"),MaterialBonus(Job));Q->SetNumberField(TEXT("skillBonus"),SkillBonus(Value));
    Q->SetNumberField(TEXT("multiplier"),Multiplier(Job));
    Data->SetObjectField(Field,Q);Write(Item,Data);return true;
}
void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority)
{
    TMap<FString,const FColdSteelItem*> ById;ById.Reserve(Authority.Num());
    for(const auto& Item:Authority)ById.Add(Item.InstanceId,&Item);
    for(auto& Item:Incoming)
    {
        const auto* Found=ById.Find(Item.InstanceId);if(!Found)continue;const auto& Known=**Found;
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
