// Server accepted action identity (requires existing ordinary/dash/quick/uppercut/whirlwind receipts)
// Host file: Source/FPSGAME/Multiplayer/ColdSteelKukriAuthority.cpp
uint32 AColdSteelPlayerState::ResolveKukriRuneAttackSerial(const FColdSteelNetHitReport& R,uint32 SnapshotSerial)
{
    if(KukriRunePawn.Get()!=GetPawn())
    {
        KukriRunePawn=GetPawn();
        for(int32 I=0;I<5;++I){KukriRuneSequences[I]=0;KukriRuneAttackIds[I]=0;}
    }
    int32 Family=0;uint32 Sequence=KukriAttack.Serial;
    if(R.AttackMeta&0x80){Family=1;Sequence=QuickCombatServerSequence;}
    else if(R.AttackMeta==SwordUppercut::AttackMeta){Family=2;Sequence=UppercutActiveSequence;}
    else if(R.AttackMeta&0x20){Family=3;Sequence=WhirlwindActiveSequence;}
    else if((R.AttackMeta&0x10)&&R.AttackMeta!=0x16)
    {
        Family=4;
        const auto* Weapon=GetPawn()?GetPawn()->FindComponentByClass<UKukriWeaponComponent>():nullptr;
        Sequence=Weapon?Weapon->GetNetworkHeavyReleaseSerial():0;
    }
    if(!Sequence||!SnapshotSerial)return 0;
    if(KukriRuneSequences[Family]!=Sequence)
    {
        KukriRuneSequences[Family]=Sequence;
        KukriRuneAttackIds[Family]=SnapshotSerial;
    }
    return KukriRuneAttackIds[Family];
}

// Private declarations
// Host file: Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h
uint32 ResolveKukriRuneAttackSerial(const FColdSteelNetHitReport& Report,uint32 SnapshotSerial);
TWeakObjectPtr<APawn> KukriRunePawn;
uint32 KukriRuneSequences[5]={},KukriRuneAttackIds[5]={};

// After accepting contact, immediately before common ApplyHit
// Host file: Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp
if(Shot.ItemDefinition==TEXT("ue_kukri"))
    Shot.MasteryAttackSerial=ResolveKukriRuneAttackSerial(Report,Shot.MasteryAttackSerial);
const float Applied = ColdSteelSkills::ApplyHit(Shooter, Hit, Damage, FVector(Report.Direction), Shot, &Receipt);

// Heavy receipt member paired with getter/increment in the patch
// Host file: Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.h
uint32 NetworkHeavyReleaseSerial=0;

// Extend the existing weather-equipment enumeration
// Host file: Source/FPSGAME/Characters/FPSPlayerBodyComponent.h
void GetWeatherWeaponMeshes(TArray<FFPSWeatherWeaponMesh>& Out,bool bWorldOnly=false) const;

// Mirror signature; gate only the owner-viewmodel block, retaining world entries
// Host file: Source/FPSGAME/Characters/FPSPlayerBodyWeather.cpp
void UFPSPlayerBodyComponent::GetWeatherWeaponMeshes(TArray<FFPSWeatherWeaponMesh>& Out,bool bWorldOnly) const
// Within the existing body:
if(!bWorldOnly&&Character.IsValid()&&(GetNetMode()==NM_Standalone||Character->IsLocallyControlled()))

// Existing fixture member declaration
// Host file: Source/FPSGAME/Multiplayer/KukriNetworkAuditCommandlet.h
void CheckRunes(class AColdSteelPlayerState* PS,class AFPSGAMECharacter* Pawn,TFunctionRef<void(bool,const TCHAR*)> Check);

// Invoke rune cases after existing attack cases
// Host file: Source/FPSGAME/Multiplayer/KukriNetworkAuditCommandlet.cpp
CheckRunes(PS,Pawn,Check);

// In RefreshOffhand after selecting the actual inventory instance
// Host file: Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.cpp
if(OffhandItem)OffhandModules.Refresh(OffhandBlade,OffhandItem);
else if(!OffhandModules.ItemId.IsEmpty())OffhandModules.Clear(OffhandBlade);

// Stat bindings inside existing action lifecycle (placement excerpts only)
// Host file: Source/FPSGAME/Weapons/Kukri/KukriHeavy.cpp
// Host line 23
// HeavyChargeSeconds, from the press) is the heavy.  The quick-bar skill charges and releases by itself.  The charge drains
// Host line 44
        Profile->MasteryProgress(TEXT("heavyStrike")).Level>=1&&(Profile->Stamina()>0.f||Profile->HeavyChargeStaminaPerSecond()<=0.f)&&
// Host line 45
        Profile->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile,DualHeavyReady()))&&
// Host line 65
    HeavyRequiredSeconds=FMath::Max(.3f,float(ColdSteelMelee::HeavyChargeSeconds(*Item,Profile,bDualHeavy)));
// Host line 128
    if(!P||!Item||Item->InstanceId!=InstanceId||!CanUse()||P->IsCastBlockingLeftHandAction()||(Profile->Stamina()<=0.f&&Profile->HeavyChargeStaminaPerSecond()>0.f))
// Host line 155
    if(!Profile->SpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Profile,bDualHeavy))){CancelHeavyCharge(true);return;}
// Host line 169
        OffhandSwingDamage=float(OffStats.Damage*OffStats.Modifiers.HeavyMultiplier(HeavyMultiplier));
// Host line 170
        OffhandReach=float((OffStats.BaseReach>0.?OffStats.BaseReach:KukriRhythm::DefaultReachCM)*OffStats.Modifiers.MartialRange);
// Host line 297
        Model->MasteryProgress(TEXT("heavyStrike")).Level<1||(Model->Stamina()<=0.f&&Model->HeavyChargeStaminaPerSecond()>0.f)||
// Host line 298
        (BothBlades&&!Off)||!Model->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Item,Model,BothBlades))||UBoundCongregateCaptureComponent::IsCaptured(P))
// Host line 307
        ServerHeavyRequired=FMath::Max(.3,ColdSteelMelee::HeavyChargeSeconds(*Item,Model,BothBlades));
// Host line 327
    const double Cost=ColdSteelMelee::HeavyReleaseStamina(Item,Model,BothBlades);
// Host line 356
    if(!P||!Item||Item->InstanceId!=ServerHeavyWeapon||(Model->Stamina()<=0.f&&Model->HeavyChargeStaminaPerSecond()>0.f)||UBoundCongregateCaptureComponent::IsCaptured(P)||

// Stat bindings inside existing action lifecycle (placement excerpts only)
// Host file: Source/FPSGAME/Weapons/Kukri/KukriWeaponComponent.cpp
// Host line 567
    PlayRate=KukriAttackTiming::PlayRate(Stats.AttackRate);
// Host line 575
        OffhandSwingDamage=OffStats.Damage;
// Host line 576
        OffhandReach=OffStats.BaseReach>0.?float(OffStats.BaseReach):KukriRhythm::DefaultReachCM;
// Host line 577
        OffhandPlayRate=KukriAttackTiming::PlayRate(OffStats.AttackRate);
// Host line 585
        if(DualThrust)PlayRate=KukriAttackTiming::PairedPlayRate(PlayRate,OffhandPlayRate);

// Stat bindings inside existing action lifecycle (placement excerpts only)
// Host file: Source/FPSGAME/Weapons/Kukri/KukriQuickCombat.cpp
// Host line 25
// quick-melee weapons (RuneSwordComponent::StartQuickCombatStrike, WarhammerQuickCombat.cpp): QuickCombatStats damage /
// Host line 54
    QuickCast=Profile->QuickCombatStats();
// Host line 58
    // The pommel is a blunt blow: blunt toughness conversion; the authority recomputes it from QuickCombatStats.

// Stat bindings inside existing action lifecycle (placement excerpts only)
// Host file: Source/FPSGAME/Weapons/Kukri/KukriUppercut.cpp
// Host line 50
    if(!Profile->CanSpendStamina(Profile->SwordUppercutStaminaCost()))return TEXT("体力不足");
// Host line 65
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
// Host line 67
    SwingDamage=float(Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers));
// Host line 68
    Reach=float((Stats.BaseReach>0.?Stats.BaseReach:KukriRhythm::DefaultReachCM)*Effect.UppercutReachMultiplier*Stats.Modifiers.MartialRange);

// Stat bindings inside existing action lifecycle (placement excerpts only)
// Host file: Source/FPSGAME/Weapons/Kukri/KukriWhirlwind.cpp
// Host line 77
    if(!Profile->CanSpendStamina(Profile->WhirlwindStats().StaminaCost))return TEXT("体力不足");
// Host line 100
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);

// Chill constant in an independently maintained source
// Host file: Source/FPSGAME/Skills/ElementalArrowTypes.h
#include "../Combat/CombatChill.h"
    float ChillSeconds=5.f,ChillSlow=CombatChill::SlowPerStack,StunSeconds=1.5f;
inline constexpr float HoldSeconds=.30f, ChillSeconds=5.f, ChillSlow=CombatChill::SlowPerStack, StunSeconds=1.5f;

// Chill constant in an independently maintained source
// Host file: Source/FPSGAME/Skills/ColdSteelSkillRules.cpp
        T.ChillSeconds=Num(TEXT("chillSeconds"),5);T.ChillSlow=CombatChill::SlowPerStack;T.StunSeconds=Num(TEXT("stunSeconds"),1.5);
        T.ChillSeconds=Num(TEXT("chillSeconds"),T.ChillSeconds);

// Chill constant in an independently maintained source
// Host file: Source/FPSGAME/Skills/ColdSteelSkillRules.cpp
        T.SlowPerStack=CombatChill::SlowPerStack;

// Add to existing /Script/UnrealEd.ProjectPackagingSettings section
// Host file: Config/DefaultGame.ini
+DirectoriesToAlwaysCook=(Path="/Game/Weapons/Kukri20261020/Berserker20261028")
+DirectoriesToAlwaysCook=(Path="/Game/Weapons/Kukri20261020/FrostRaven20261028")
