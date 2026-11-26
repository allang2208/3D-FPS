#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/RavenQuillChargeComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/TangDaoGuardComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "FPSExhaustionComponent.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "GameFramework/PlayerController.h"

namespace
{
enum class EStaminaActivity { Recovering, Charging, Guarding, Sprinting, Inactive };
EStaminaActivity StaminaActivity(const AFPSGAMECharacter* Pawn,const FColdSteelStaminaTuning& Tuning)
{
    if(!Pawn)return EStaminaActivity::Inactive;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead())return EStaminaActivity::Inactive;
    const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
    const auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();
    const auto* Bow=Pawn->FindComponentByClass<UBowWeaponComponent>();
    const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    const auto* Rain=Pawn->FindComponentByClass<UFPSMagicArrowRainComponent>();
    if((Rain&&Rain->IsManaDraining())||(Bow&&Bow->IsDrawing())||(PS&&PS->IsBowDrawActive(Pawn)))return EStaminaActivity::Charging;
    if((Sword&&Sword->IsHeavyCharging())||(Tool&&Tool->IsHeavyChargeConsumingStamina())||(Kukri&&Kukri->IsHeavyCharging()))return EStaminaActivity::Charging;
    if(Sword&&Sword->IsGuarding())return EStaminaActivity::Guarding;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    bool Sprint=Pawn->IsSprinting();
    if(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
        if(const auto* Raven=Pawn->FindComponentByClass<URavenQuillChargeComponent>();Raven&&Raven->IsInstalled())
            Sprint=Raven->IsMovingSprint();
    if(Tuning.SprintPerSecond>0&&Sprint&&Pawn->GetVelocity().SizeSquared2D()>2500&&!AFPSGAMEPlayerController::BlocksOngoingActions(PC))
        return EStaminaActivity::Sprinting;
    return EStaminaActivity::Recovering;
}
}

void UColdSteelStatusModel::LoadStaminaTuning()
{
    FString Json; TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/stamina.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root) || !Root)return;
    auto Read=[&](const TCHAR* Key,float& Field,float Min,float Max){double V=Field;if(Root->TryGetNumberField(Key,V)&&FMath::IsFinite(V))Field=FMath::Clamp(float(V),Min,Max);};
    Read(TEXT("baseMaximum"),StaminaTuning.BaseMaximum,1,10000);Read(TEXT("perConstitution"),StaminaTuning.PerConstitution,0,1000);
    Read(TEXT("sprintPerSecond"),StaminaTuning.SprintPerSecond,0,1000);Read(TEXT("meleeCost"),StaminaTuning.MeleeCost,0,1000);
    Read(TEXT("punchCost"),StaminaTuning.PunchCost,0,1000);
    Read(TEXT("harvestCost"),StaminaTuning.HarvestCost,0,1000);Read(TEXT("dodgeCost"),StaminaTuning.DodgeCost,0,1000);
    Read(TEXT("recoveryPerSecond"),StaminaTuning.RecoveryPerSecond,0,1000);Read(TEXT("recoveryDelay"),StaminaTuning.RecoveryDelay,0,60);
    Read(TEXT("sprintRestartRatio"),StaminaTuning.SprintRestartRatio,.01f,1);
}
double UColdSteelStatusModel::StaminaMaximum(const FColdSteelProfile& State,const FColdSteelStaminaTuning& Tuning)
{
    const double Con=(State.Attributes.FindRef(TEXT("con"))+EquipmentBonusFor(State,TEXT("con")))*State.Infection.AttributeMultiplier()*State.Survival.AttributeMultiplier();
    return (Tuning.BaseMaximum+Con*Tuning.PerConstitution+EquipmentBonusFor(State,TEXT("maxStamina")))*(State.Survival.LargeLambMealSeconds>0.f?FFPSSurvivalState::LargeLambMaximumMultiplier:1.f);
}
float UColdSteelStatusModel::MaxStamina() const
{
    // Remove the saved snapshot factor, then use the live server clock factor.
    const float SavedFactor=Current.Survival.LargeLambMealSeconds>0.f?FFPSSurvivalState::LargeLambMaximumMultiplier:1.f;
    return float(StaminaMaximum(Current,StaminaTuning))/SavedFactor*FoodStaminaMaximumMultiplier();
}
float UColdSteelStatusModel::FoodStaminaMaximumMultiplier() const
{
    const auto* Survival=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSSurvivalComponent>():nullptr;
    const float Remaining=Survival?Survival->LargeLambMealRemaining():Current.Survival.LargeLambMealSeconds;
    return Remaining>0.f?FFPSSurvivalState::LargeLambMaximumMultiplier:1.f;
}
float UColdSteelStatusModel::FoodStaminaRecoveryMultiplier() const
{
    const auto* Survival=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSSurvivalComponent>():nullptr;
    const float Remaining=Survival?Survival->SausageRecoveryRemaining():Current.Survival.SausageRecoverySeconds;
    const float LambRemaining=Survival?Survival->LargeLambMealRemaining():Current.Survival.LargeLambMealSeconds;
    // Independent source multipliers compose; each named food refreshes one clock.
    return (Remaining>0.f?FFPSSurvivalState::SausageRecoveryRateMultiplier:1.f)*
        (LambRemaining>0.f?FFPSSurvivalState::LargeLambRecoveryMultiplier:1.f);
}
float UColdSteelStatusModel::StaminaRecoveryRate() const
{ return StaminaTuning.RecoveryPerSecond*Derived(TEXT("staminaRegen"))*FoodStaminaRecoveryMultiplier(); }
AFPSGAMECharacter* UColdSteelStatusModel::RuntimePawn() const {return CurrentPawn.Get();}
float UColdSteelStatusModel::ActionStaminaMultiplier() const
{ return float(SetEffect(TEXT("actionStaminaCost"))); }
float UColdSteelStatusModel::HeavyChargeStaminaPerSecond() const
{
    if(UEagleTalonGuardComponent::Ready(this))return 0.f;
    if(const auto* Tool=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UProductionToolComponent>():nullptr;Tool&&Tool->IsThunderCalling())
        return ThunderHammerCall::StaminaPerSecond*ActionStaminaMultiplier();
    const auto* Item=ActiveKukriWeapon();
    double BladeCost=!ActiveProductionTool()&&Item&&ColdSteelInventory::IsOneHandedMelee(*Item)?
        ColdSteelMelee::ItemModifiers(Item,this).Stamina:1.;
    const auto* Off=Item&&ColdSteelInventory::IsOneHandedMelee(*Item)?ColdSteelMelee::PairedOneHandedWeapon(Item,this):nullptr;
    const auto* Kukri=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UKukriWeaponComponent>():nullptr;
    // While charging, use the actual selected action (single fallback or dual), including the authority's receipt.
    if(Off&&(!Kukri||!Kukri->IsHeavyCharging()||Kukri->IsDualHeavyCharging()))
        BladeCost=.5*BladeCost+.5*ColdSteelMelee::ItemModifiers(Off,this).Stamina;
    const auto* G=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    const float Oath=!ActiveProductionTool()&&HighlandOathRune::Installed(G,Equipped())?
        float(G->Calculate(Equipped()->Definition,G->Installed(*Equipped())).Melee.OathChargeStamina):1.f;
    return MasteryDefinition(TEXT("heavyStrike")).HeavyChargeStaminaPerSecond*BladeCost*ActionStaminaMultiplier()*Oath;
}
float UColdSteelStatusModel::SprintStaminaPerSecond() const
{
    const auto* Guard=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UTangDaoGuardComponent>():nullptr;
    const auto* Item=!ActiveProductionTool()?Equipped():nullptr;
    // Highland pommel modifiers belong to the currently held sword. The Tang
    // Dao guard already supplies its own multiplier below; do not apply it twice.
    const double SwordCost=Item&&Item->Definition==TEXT("ue_highland_claymore")?
        ColdSteelMelee::ItemModifiers(Item,this).SprintStamina:1.;
    // 装备的 sprintStaminaCost 为负时降低奔跑消耗；下限 0，避免出现负消耗。
    // 套装效果（ST6 战术套）与装备同口径叠加，角色面板与实机消耗读同一处。
    const float Equipment=FMath::Max(0.f,1.f+float(EquipmentBonus(TEXT("sprintStaminaCost"))+SetEffect(TEXT("sprintStaminaCost"))));
    return StaminaTuning.SprintPerSecond*SwordCost*(Guard?Guard->SprintStaminaMultiplier():1.f)*Equipment*ActionStaminaMultiplier();
}
FColdSteelMeleeStaminaReadout UColdSteelStatusModel::MeleeStaminaReadout(const AFPSGAMECharacter* Pawn) const
{
    FColdSteelMeleeStaminaReadout Result;
    const int32 Offhand=Current.ActiveWeaponSlot==6?8:11;
    const bool Empty=!Equipped(Current.ActiveWeaponSlot)&&!Equipped(Offhand)&&!ActiveProductionTool();
    const float Available=FMath::Max(0.f,Current.Stamina);
    const float Cost=Empty?ColdSteelMelee::UnarmedAttackStamina(this):ColdSteelMelee::ComboAttackStamina(ActiveKukriWeapon(),this,true);
    Result.bUnlimitedAttacks=Cost==0.f;
    if(Cost>0.f)Result.AvailableAttacks=FMath::FloorToInt(double(Available)/double(Cost));
    const float Missing=FMath::Max(0.f,MaxStamina()-Available);
    if(Missing==0.f)return Result;
    const float Rate=StaminaRecoveryRate();
    Result.bRecoveryDisabled=Rate<=0.f;
    Result.bRecoveryPaused=StaminaActivity(Pawn,StaminaTuning)!=EStaminaActivity::Recovering;
    if(Rate>0.f)Result.FullRecoverySeconds=FMath::Max(0.f,Current.StaminaRecoveryDelay)+Missing/Rate;
    return Result;
}
bool UColdSteelStatusModel::NormalizeStamina(FColdSteelProfile& P) const
{
    const float Maximum=float(StaminaMaximum(P,StaminaTuning));
    const bool Migrated=P.StaminaVersion==0;
    if(Migrated){P.StaminaVersion=1;P.Stamina=Maximum;P.StaminaRecoveryDelay=0;P.bSprintExhausted=false;}
    P.Stamina=FMath::Clamp(P.Stamina,0.f,Maximum);
    return Migrated;
}
bool UColdSteelStatusModel::CanSprint() const
{
    if(Current.Stamina<=0.f||Current.bSprintExhausted)return false;
    const auto* Status=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    return !Status||Status->ExhaustionRemaining()<=0.f;
}
bool UColdSteelStatusModel::CanSpendStamina(float Amount) const
{ return FMath::IsFinite(Amount)&&Amount>=0&&Current.Stamina>=Amount; }
bool UColdSteelStatusModel::SpendStamina(float Amount)
{
    if(!CanSpendStamina(Amount)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    if(Amount==0)return true;
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    Current.Stamina=FMath::Max(0.f,Current.Stamina-Amount);Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0)Current.bSprintExhausted=true;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    OnStaminaChanged.Broadcast();return true;
}
void UColdSteelStatusModel::DelayStaminaRecovery()
{
    Current.StaminaRecoveryDelay=FMath::Max(Current.StaminaRecoveryDelay,StaminaTuning.RecoveryDelay);
    OnStaminaChanged.Broadcast();
}
void UColdSteelStatusModel::ApplyKillStaminaRecovery(AActor* Victim)
{
    if(!IsValid(Victim)||!Victim->HasAuthority()||KillStaminaVictims.Contains(Victim))return;
    for(auto It=KillStaminaVictims.CreateIterator();It;++It)
        if(!It->IsValid())It.RemoveCurrent();
    KillStaminaVictims.Add(Victim);
    if(const auto* Health=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;Health&&Health->IsDead())return;
    double Ratio=ColdSteelMelee::EquippedModifiers(this).KillStaminaMaxRatio;
    if(!ActiveProductionTool())
    {
        // Equipped kill passives belong to each active blade, regardless of which
        // owned attack dealt the killing blow. Stored/inactive weapon sets do not count.  (A lone off-hand blade is the
        // active one.)
        const auto* Main=ActiveKukriWeapon();
        if(Main&&ColdSteelInventory::IsOneHandedMelee(*Main))
            Ratio+=ColdSteelMelee::ItemModifiers(Main,this).KillStaminaMaxRatio;
        if(const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(Main,this))
            Ratio+=ColdSteelMelee::ItemModifiers(Off,this).KillStaminaMaxRatio;
    }
    if(Ratio<=0)return;
    RestoreCombatStamina(MaxStamina()*float(Ratio));
}
void UColdSteelStatusModel::RestoreCombatStamina(float Amount)
{
    const float Maximum=MaxStamina(),Before=Current.Stamina;
    const bool WasExhausted=Current.bSprintExhausted;
    Current.Stamina=FMath::Clamp(Current.Stamina+Amount,0.f,Maximum);
    if(Current.bSprintExhausted&&Current.Stamina>=Maximum*StaminaTuning.SprintRestartRatio)
        Current.bSprintExhausted=false;
    // Instant kill recovery does not change the ordinary recovery-delay clock.
    if(Before!=Current.Stamina||WasExhausted!=Current.bSprintExhausted)OnStaminaChanged.Broadcast();
}
double UColdSteelStatusModel::RefundOathStamina(float Amount)
{
    // The owner reconciles the cumulative credit after its own later spending.
    // Publish only what the authority could restore below the stamina cap.
    Amount=FMath::Clamp(Amount,0.f,FMath::Max(0.f,MaxStamina()-Current.Stamina));
    Current.OathStaminaRestored+=Amount;RestoreCombatStamina(Amount);
    return Current.OathStaminaRestored;
}
void UColdSteelStatusModel::ApplyOathRefundReceipt(double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Current.OathStaminaRestored)return;
    const float Delta=float(Total-Current.OathStaminaRestored);
    Current.OathStaminaRestored=Total;RestoreCombatStamina(Delta);
}
bool UColdSteelStatusModel::TickStamina(float Delta,AFPSGAMECharacter* Pawn,float BowSkillManaPerSecond)
{
    if(Delta<=0||!Pawn)return false;
    bool AuroraDrawing=false;
    const EStaminaActivity Activity=StaminaActivity(Pawn,StaminaTuning);
    if(Activity==EStaminaActivity::Inactive)return false;
    auto* Exhaustion=Pawn->FindComponentByClass<UFPSExhaustionComponent>();
    // Observe direct authoritative resource transactions before recovery advances.
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    const float Before=Current.Stamina,BeforeWait=Current.StaminaRecoveryDelay;
    const bool BeforeExhausted=Current.bSprintExhausted;
    // Expiration clamps even while guarding, charging or sprinting; activation
    // and refresh never add current stamina or rescale its percentage.
    Current.Stamina=FMath::Clamp(Current.Stamina,0.f,MaxStamina());
    if(Activity==EStaminaActivity::Charging)
    {
        // Use real gameplay seconds, including an indefinitely held full charge.
        const auto* Bow=ActiveBow();
        const auto* Rain=Pawn->FindComponentByClass<UFPSMagicArrowRainComponent>();
        const float Drain=Rain&&Rain->IsManaDraining() ? float(ColdSteelBow::ArrowRainStaminaPerSecond(*this))
            : Bow ? float(ColdSteelBow::ChargeStaminaPerSecond(*Bow,this)) : HeavyChargeStaminaPerSecond();
        const float BeforeChargeDrain=Current.Stamina;
        auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
        float Spent=Sword&&Sword->IsBillingRingChainCharge()?Sword->TakeRingChainChargeDrain(Drain):Drain*Delta;
        AuroraDrawing=ColdSteelBow::AuroraRiser(this,Bow)!=nullptr;
        if(AuroraDrawing&&!HasInfiniteMana())
        {
            // Bill both pools for the same fraction of the last affordable frame.
            const float StaminaDue=FMath::Min(Current.Stamina,Spent);
            const float ManaDue=AdjustedManaCost(StaminaDue+BowSkillManaPerSecond*Delta);
            const float Fraction=ManaDue>0.f?FMath::Min(1.f,Current.Mana/ManaDue):1.f;
            Spent=StaminaDue*Fraction;
            Current.Mana=FMath::Max(0.f,Current.Mana-ManaDue);
        }
        Current.Stamina=FMath::Max(0.f,Current.Stamina-Spent);
        if(Sword)
            Sword->AccumulateGaleCharge(BeforeChargeDrain-Current.Stamina);
        Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
        const bool ManaExhausted=AuroraDrawing&&!HasInfiniteMana()&&Current.Mana<=0.f;
        if((Current.Stamina<=0.f&&Drain>0.f)||ManaExhausted)
        {
            if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
            if(Sword)Sword->CancelHeavyCharge();
            if(auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>())Tool->CancelHeavyCharge();
            if(auto* BowComponent=Pawn->FindComponentByClass<UBowWeaponComponent>())BowComponent->CancelDrawForExhaustion(ManaExhausted);
            if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();PS&&PS->IsBowDrawActive(Pawn))PS->CancelBowDraw(true);
        }
    }
    else if(Activity==EStaminaActivity::Guarding)
    {
        Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    }
    else if(Activity==EStaminaActivity::Sprinting)
    {
        Current.Stamina=FMath::Max(0.f,Current.Stamina-SprintStaminaPerSecond()*Delta);
        Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
        if(Current.Stamina<=0)Current.bSprintExhausted=true;
    }
    else
    {
        const float RecoverSeconds=FMath::Max(0.f,Delta-Current.StaminaRecoveryDelay);
        Current.StaminaRecoveryDelay=FMath::Max(0.f,Current.StaminaRecoveryDelay-Delta);
        Current.Stamina=FMath::Min(MaxStamina(),Current.Stamina+StaminaRecoveryRate()*RecoverSeconds);
        if(Current.bSprintExhausted&&Current.Stamina>=MaxStamina()*StaminaTuning.SprintRestartRatio)Current.bSprintExhausted=false;
    }
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(Before!=Current.Stamina||BeforeWait!=Current.StaminaRecoveryDelay||BeforeExhausted!=Current.bSprintExhausted)OnStaminaChanged.Broadcast();
    return AuroraDrawing;
}
