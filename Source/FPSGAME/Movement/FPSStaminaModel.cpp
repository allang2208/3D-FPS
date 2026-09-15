#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "GameFramework/PlayerController.h"

namespace
{
enum class EStaminaActivity { Recovering, Guarding, Sprinting, Inactive };
EStaminaActivity StaminaActivity(const AFPSGAMECharacter* Pawn,const FColdSteelStaminaTuning& Tuning)
{
    if(!Pawn)return EStaminaActivity::Inactive;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead())return EStaminaActivity::Inactive;
    const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    if(Sword&&Sword->IsGuarding())return EStaminaActivity::Guarding;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(Tuning.SprintPerSecond>0&&Pawn->IsSprinting()&&Pawn->GetVelocity().SizeSquared2D()>2500&&PC&&!PC->IsMoveInputIgnored()&&!PC->bShowMouseCursor)
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
    Read(TEXT("harvestCost"),StaminaTuning.HarvestCost,0,1000);Read(TEXT("dodgeCost"),StaminaTuning.DodgeCost,0,1000);
    Read(TEXT("recoveryPerSecond"),StaminaTuning.RecoveryPerSecond,0,1000);Read(TEXT("recoveryDelay"),StaminaTuning.RecoveryDelay,0,60);
    Read(TEXT("sprintRestartRatio"),StaminaTuning.SprintRestartRatio,.01f,1);
}
float UColdSteelStatusModel::MaxStamina() const
{ return 100+EquipmentBonus(TEXT("maxStamina")); }
float UColdSteelStatusModel::StaminaRecoveryRate() const
{ return StaminaTuning.RecoveryPerSecond*Derived(TEXT("staminaRegen")); }
FColdSteelMeleeStaminaReadout UColdSteelStatusModel::MeleeStaminaReadout(const AFPSGAMECharacter* Pawn) const
{
    FColdSteelMeleeStaminaReadout Result;
    const float Available=FMath::Max(0.f,Current.Stamina),Cost=StaminaTuning.MeleeCost;
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
    const float Maximum=100+EquipmentBonusFor(P,TEXT("maxStamina"));
    const bool Migrated=P.StaminaVersion==0;
    if(Migrated){P.StaminaVersion=1;P.Stamina=Maximum;P.StaminaRecoveryDelay=0;P.bSprintExhausted=false;}
    P.Stamina=FMath::Clamp(P.Stamina,0.f,Maximum);
    return Migrated;
}
bool UColdSteelStatusModel::CanSprint() const
{ return Current.Stamina>0 && !Current.bSprintExhausted; }
bool UColdSteelStatusModel::CanSpendStamina(float Amount) const
{ return FMath::IsFinite(Amount)&&Amount>=0&&Current.Stamina>=Amount; }
bool UColdSteelStatusModel::SpendStamina(float Amount)
{
    if(!CanSpendStamina(Amount)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    if(Amount==0)return true;
    Current.Stamina=FMath::Max(0.f,Current.Stamina-Amount);Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0)Current.bSprintExhausted=true;
    OnStaminaChanged.Broadcast();return true;
}
void UColdSteelStatusModel::DelayStaminaRecovery()
{
    Current.StaminaRecoveryDelay=FMath::Max(Current.StaminaRecoveryDelay,StaminaTuning.RecoveryDelay);
    OnStaminaChanged.Broadcast();
}
void UColdSteelStatusModel::TickStamina(float Delta,AFPSGAMECharacter* Pawn)
{
    if(Delta<=0||!Pawn)return;
    const EStaminaActivity Activity=StaminaActivity(Pawn,StaminaTuning);
    if(Activity==EStaminaActivity::Inactive)return;
    const float Before=Current.Stamina,BeforeWait=Current.StaminaRecoveryDelay;
    const bool BeforeExhausted=Current.bSprintExhausted;
    if(Activity==EStaminaActivity::Guarding)
    {
        Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    }
    else if(Activity==EStaminaActivity::Sprinting)
    {
        Current.Stamina=FMath::Max(0.f,Current.Stamina-StaminaTuning.SprintPerSecond*Delta);
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
    if(Before!=Current.Stamina||BeforeWait!=Current.StaminaRecoveryDelay||BeforeExhausted!=Current.bSprintExhausted)OnStaminaChanged.Broadcast();
}
