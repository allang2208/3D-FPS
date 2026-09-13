#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillDefinition ColdSteelSkills::LoadDefinition()
{
    FColdSteelSkillDefinition D;
    FString Json; TSharedPtr<FJsonObject> Root;
    if (!FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir()/TEXT("ColdSteelData/skills.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root) return D;
    const TSharedPtr<FJsonObject>* Entry = nullptr;
    if (!Root->TryGetObjectField(TEXT("rifleMastery"), Entry)) return D;
    const auto& O = *Entry;
    O->TryGetStringField(TEXT("name"), D.Name); O->TryGetStringField(TEXT("description"), D.Description);
    O->TryGetStringField(TEXT("icon"), D.Icon); O->TryGetStringField(TEXT("upgradeSound"), D.UpgradeSound);
    auto Num = [&](const TCHAR* Key, double Default) { double Value=Default; O->TryGetNumberField(Key,Value); return FMath::IsFinite(Value)?Value:Default; };
    // Version 1's save contract fixes the level cap; tuning accepts positive, bounded coefficients.
    D.ExperiencePerLevel = FMath::Clamp(int32(Num(TEXT("experiencePerLevel"),100)),1,100000);
    D.KillExperience = FMath::Clamp(int32(Num(TEXT("killExperience"),10)),0,10000);
    D.CriticalExperience = FMath::Clamp(int32(Num(TEXT("criticalExperience"),5)),0,10000);
    D.DamagePercentPerLevel = FMath::Clamp(Num(TEXT("damagePercentPerLevel"),.01),0.,1.);
    D.FlatDamagePerLevel = FMath::Clamp(Num(TEXT("flatDamagePerLevel"),1),0.,100.);
    D.WeakpointPerLevel = FMath::Clamp(Num(TEXT("weakpointPercentPerLevel"),.01),0.,1.);
    D.WisdomPerLevel = FMath::Clamp(int32(Num(TEXT("wisdomPerLevel"),1)),0,100);
    return D;
}
bool ColdSteelSkills::Migrate(FColdSteelProfile& P)
{
    if (P.SkillProgressVersion != 0) return false;
    P.Skills.FindOrAdd(TEXT("rifleMastery")); P.SkillProgressVersion=1;
    return true;
}
bool ColdSteelSkills::Validate(const FColdSteelProfile& P, FString& Reason)
{
    if (P.SkillProgressVersion<0 || P.SkillProgressVersion>1 || P.Skills.Num()>128) { Reason=TEXT("技能存档版本或数量无效"); return false; }
    if (P.SkillProgressVersion==1 && !P.Skills.Contains(TEXT("rifleMastery"))) { Reason=TEXT("技能进度缺失"); return false; }
    for (const auto& Pair:P.Skills)
        if (Pair.Key.IsNone() || Pair.Value.Level<1 || Pair.Value.Level>20 || Pair.Value.Experience<0 || Pair.Value.Experience>2000000 || (Pair.Value.Level==20 && Pair.Value.Experience!=0))
        { Reason=TEXT("技能等级或修炼值无效"); return false; }
    return true;
}
bool ColdSteelSkills::IsRifle(const FColdSteelItem* I)
{ return I && ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("rifle"); }
FColdSteelSkillEffect ColdSteelSkills::Effect(const FColdSteelSkillDefinition& D, int32 Level)
{
    const int32 L=FMath::Clamp(Level,0,D.MaxLevel);
    FColdSteelSkillEffect E; E.DamagePercent=L*D.DamagePercentPerLevel; E.FlatDamage=L*D.FlatDamagePerLevel;
    E.WeakpointPercent=L*D.WeakpointPerLevel; E.Wisdom=L*D.WisdomPerLevel; return E;
}
int32 ColdSteelSkills::ExperienceRequired(const FColdSteelSkillDefinition& D, int32 L)
{ return L>=D.MaxLevel?0:FMath::Max(1,L)*D.ExperiencePerLevel; }
void ColdSteelSkills::AddExperience(FColdSteelProfile& P, const FColdSteelSkillDefinition& D, int32 Amount)
{
    auto* Progress=P.Skills.Find(D.Id);
    if (!Progress || Amount<=0 || Progress->Level>=D.MaxLevel) return;
    Progress->Experience+=Amount;
    while (Progress->Level<D.MaxLevel)
    {
        const int32 Need=ExperienceRequired(D,Progress->Level); if (Progress->Experience<Need) break;
        Progress->Experience-=Need; ++Progress->Level;
    }
    if (Progress->Level==D.MaxLevel) Progress->Experience=0;
}
FString ColdSteelSkills::EffectSummary(const FColdSteelSkillEffect& E)
{ return FString::Printf(TEXT("步枪伤害 +%.0f%% / +%.0f   ·   精神 +%d   ·   要害伤害 +%.0f%%"),E.DamagePercent*100,E.FlatDamage,E.Wisdom,E.WeakpointPercent*100); }
FColdSteelSkillShot ColdSteelSkills::Snapshot(AActor* Shooter)
{
    FColdSteelSkillShot Shot;
    if (Shooter && Shooter->GetGameInstance()) if (auto* M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    { Shot.bRifle=IsRifle(M->Equipped()); Shot.WeakpointPercent=Shot.bRifle?M->RifleEffect().WeakpointPercent:0; }
    return Shot;
}
float ColdSteelSkills::ApplyHit(AActor* Shooter,const FHitResult& Hit,float Damage,const FVector& Direction,const FColdSteelSkillShot& Shot)
{
    if (Shooter && Shooter->GetGameInstance()) if (auto* M=Shooter->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        return M->ApplySkillWeaponHit(Shooter,Hit,Damage,Direction,Shot);
    const auto* Pawn=Cast<APawn>(Shooter);
    return UGameplayStatics::ApplyPointDamage(Hit.GetActor(),Damage,Direction,Hit,Pawn?Pawn->GetController():nullptr,Shooter,nullptr);
}
