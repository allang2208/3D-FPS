#include "ThunderHammerRunes.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerPommel.h"
#include "ThunderHammerFX.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MagicOcclusion.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/Pawn.h"

void ThunderHammerRunes::Configure(FLightningCast& Spell,const FColdSteelItem* Item)
{
    ThunderHammerPommel::Configure(Spell,Item);
    FString Rune;
    if(Item&&Item->Definition==ThunderHammer::Definition)
    {
        const auto Data=ColdSteelItemData::Read(Item->Data);const TSharedPtr<FJsonObject>* Parts=nullptr;
        if(Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))(*Parts)->TryGetStringField(TEXT("rune"),Rune);
    }
    const bool EchoInstalled=Rune==Echo;
    // Rebinding an offhand/committed item must neither double the bonus nor
    // inherit the rune on a different weapon currently held by its owner.
    Spell.OverloadStun+=(EchoInstalled?.25f:0.f)-(Spell.bEchoRune?.25f:0.f);
    Spell.bEchoRune=EchoInstalled;Spell.OverloadRetainedStacks=EchoInstalled?2:0;
    Spell.RuneElectrifyChance=Rune==Thunder?.5f:0.f;
}

int32 ThunderHammerRunes::Stacks(const FLightningCast& Spell,int32 NativeStacks)
{
    return NativeStacks+(Spell.RuneElectrifyChance>0.f&&FMath::FRand()<Spell.RuneElectrifyChance?1:0);
}

void ThunderHammerRunes::OnHit(AActor* Shooter,AActor* Target,const FColdSteelSkillShot& Shot)
{
    if(!Shooter||!Shooter->HasAuthority()||!Target||!UFPSMeleeLightningComponent::IsEnemy(Target,Shooter))return;
    ApplyStacks(Shooter,Target,Shot,Stacks(Shot.HammerLightning,Shot.HammerNativeStacks));
}

void ThunderHammerRunes::ApplyStacks(AActor* Shooter,AActor* Target,const FColdSteelSkillShot& Shot,int32 Count)
{
    if(!Shooter||!Shooter->HasAuthority()||!Target||!UFPSMeleeLightningComponent::IsEnemy(Target,Shooter))return;
    const auto& Spell=Shot.HammerLightning;
    if(Count<=0)return;
    auto* Status=UCombatStatusFormula::GetOrAdd(Target);
    if(!Status||Status->IsImmune()||!Status->AddElectrified(Count,Spell.ElectrifyDuration,Spell.OverloadStacks,
        Spell.ElectricBonusPerStack,Spell.OverloadRetainedStacks))return;
    Status->AddStun(Spell.OverloadStun);
    auto* Pawn=Cast<APawn>(Shooter);auto* World=Shooter->GetWorld();const FVector Start=Target->GetActorLocation();
    TArray<FOverlapResult> Nearby;FCollisionQueryParams Q(SCENE_QUERY_STAT(ThunderRuneOverload),false,Shooter);Q.AddIgnoredActor(Target);
    World->OverlapMultiByObjectType(Nearby,Start,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
        FCollisionShape::MakeSphere(Spell.OverloadRange),Q);
    for(const auto& O:Nearby)if(auto* Body=Cast<APawn>(O.GetActor()))Q.AddIgnoredActor(Body);
    TSet<AActor*> Seen;
    for(const auto& O:Nearby)
    {
        auto* Other=O.GetActor();auto* Combat=Other?Other->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||Combat->IsDead()||Seen.Contains(Other)||Other==Target||!UFPSMeleeLightningComponent::IsEnemy(Other,Shooter))continue;
        Seen.Add(Other);FHitResult Cover;const FVector End=Other->GetActorLocation();
        if(MagicOcclusion::TraceBlocker(World,Start,End,Q,Cover)&&Cover.GetActor()!=Other)continue;
        auto Splash=Shot;Splash.bMelee=false;Splash.ExtraMasteryExperience=0;Splash.DamagePanel={};
        // A rune's own overload is a follow-up receipt, not a new proc source.
        Splash.HammerNativeStacks=0;Splash.bHammerRuneContact=false;Splash.HammerLightning.RuneElectrifyChance=0.f;
        const auto* OtherStatus=Other->FindComponentByClass<UCombatStatusFormula>();
        Splash.DamagePanel.AddedMagic=Spell.OverloadDamage*(OtherStatus?OtherStatus->ElectricMultiplier():1.f);
        Splash.HammerElectricDamage=Splash.DamagePanel.AddedMagic;
        FHitResult Hit(Other,O.GetComponent(),End,(Start-End).GetSafeNormal());Hit.TraceStart=Start;Hit.TraceEnd=End;
        ColdSteelSkills::ApplyHit(Pawn,Hit,Splash.DamagePanel.Total(),(End-Start).GetSafeNormal(),Splash);
        if(auto* FX=World->GetSubsystem<UThunderHammerFXSubsystem>())FX->EmitOverload(Pawn,Start,End,Spell);
    }
}
