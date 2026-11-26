#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/SniperSuppressorAssets.h"
#include "../Weapons/WeaponShotNoise.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/Saiga12KWeaponAssets.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

double AColdSteelPlayerState::FastestAuthorityFireInterval(const AFPSGAMECharacter* Pawn) const
{
    if(!Pawn)return .01;
    // Base stats and turbo entitlement are authoritative; remote trigger-held
    // and ramp presentation clocks are not. Admit the fastest allowed endpoint.
    const auto& Ramp=Pawn->TurboRampParams;
    const double Turbo=FMath::Min(ColdSteelCombat::TurboIntervalMultiplier(Ramp,0.),
        ColdSteelCombat::TurboIntervalMultiplier(Ramp,Ramp.Seconds));
    double Interval=FMath::Max(.001,double(Pawn->FireInterval))*Turbo;
    if(Pawn->IsSaiga12KWeapon())Interval=FMath::Max(double(Saiga12KWeaponAssets::MinimumAttackInterval),Interval);
    if(Pawn->IsTubeShotgunWeapon())Interval=FMath::Max(TubeShotgunAssets::MinimumInterval(Pawn->ActiveInventoryWeaponDefinition),Interval);
    return Interval/LightningHaste::ActionSpeed(Pawn);
}

void AColdSteelPlayerState::RecordAuthorityShotRecovery(APawn* Pawn,double Seconds)
{
    const double Until=GetWorld()->GetTimeSeconds()+FMath::Max(0.,Seconds);
    AuthorityShotRecoveryUntil=AuthorityShotRecoveryPawn.Get()==Pawn?FMath::Max(AuthorityShotRecoveryUntil,Until):Until;
    AuthorityShotRecoveryPawn=Pawn;
}

bool AColdSteelPlayerState::IsGenericFirearm(const FColdSteelItem& Item) const
{
    const auto* G=GetGameInstance()?GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    return ColdSteelInventory::Text(Item,TEXT("category")).StartsWith(TEXT("weapon"))
        &&!ColdSteelInventory::IsMeleeWeapon(Item)&&!ColdSteelInventory::IsBow(Item)
        &&!ColdSteelInventory::IsDualPistol(Item)&&!SniperSuppressorAssets::SupportsZhiming(Item.Definition)
        &&!TubeShotgunAssets::Supports(Item.Definition)&&G&&!G->IsStaff(Item.Definition)&&!G->IsTool(Item.Definition);
}

void AColdSteelPlayerState::ServerRememberGenericLaunch_Implementation(APawn* SourcePawn,const FString& Instance,uint32 Sequence,int32 Rounds)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!HasAuthority()||!Pawn||Pawn!=SourcePawn||!ShadowModel||!Sequence)return;
    if(GenericLaunchPawn.Get()!=Pawn)
    {GenericLaunches.Reset();LastGenericLaunchSequence=0;GenericLaunchReadyAt=0.;GenericLaunchTokenAt=0.;GenericLaunchTokens=6.f;GenericLaunchPawn=Pawn;}
    if(LastGenericLaunchSequence&&int32(Sequence-LastGenericLaunchSequence)<=0)return;
    // Rejected IDs cannot later be resurrected after cancelling food use.
    LastGenericLaunchSequence=Sequence;
    const auto* Item=ShadowModel->Equipped();
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const double Now=GetWorld()->GetTimeSeconds();
    if(!Item||!IsGenericFirearm(*Item)||Item->InstanceId!=Instance||Instance!=Pawn->GetActiveWeaponInstance()
        ||!Health||Health->IsDead()||HasAuthorityConsumableReservation(Pawn)||!PendingCastSkill.IsNone()
        ||Pawn->IsCastBlockingLeftHandAction()||Pawn->IsTraversing()||Pawn->IsDodging()||Pawn->IsSliding()
        ||WeaponReloadStages::NeedsCycle(*Item)
        ||Rounds<1||Rounds>Pawn->GetMagazineCapacity())return;
    // Match the existing generic ammo ledger: a completed reload can be newer
    // than the shadow item upload. Registration must not require that upload.
    const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const int32 Capacity=G?FMath::Clamp(G->CalculateItem(*Item,G->Installed(*Item)).Capacity,0,1000):Pawn->GetMagazineCapacity();
    const auto* Ledger=ServerGunLedgers.Find(Instance);
    int32 Available=Ledger&&Ledger->Magazine>=0?Ledger->Magazine:Item->Magazine;
    if(Available<=0&&Ledger&&Now>=Ledger->ReloadReadyAt)Available=Capacity;
    if(Rounds>Available||(Rounds>1&&(!Pawn->ConvergenceParams.Enabled||Rounds!=Available)))return;
    const double Interval=FMath::Max(.001,FastestAuthorityFireInterval(Pawn));
    GenericLaunchTokens=FMath::Min(6.f,GenericLaunchTokens+float(FMath::Max(0.,Now-GenericLaunchTokenAt)/Interval));
    GenericLaunchTokenAt=Now;
    if(GenericLaunchTokens<1.f)return;
    for(auto It=GenericLaunches.CreateIterator();It;++It)
        if(It.Value().Pawn.Get()!=Pawn||Now>It.Value().Expires)It.RemoveCurrent();
    if(GenericLaunches.Num()>=1024)return;
    GenericLaunchTokens-=1.f;
    auto& Launch=GenericLaunches.Add(Sequence);
    Launch.Item=*Item;Launch.Item.Magazine=Available;Launch.Pawn=Pawn;Launch.Sequence=Sequence;Launch.Rounds=Rounds;Launch.At=Now;
    Launch.ReadyAt=Now+Interval;GenericLaunchReadyAt=Launch.ReadyAt;
    static const auto* Scale=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Ballistics.SpeedScale"));
    const float Speed=Pawn->ProjectileSpeedCM*(Scale?FMath::Clamp(Scale->GetFloat(),.05f,10.f):1.f);
    Launch.Expires=Now+FMath::Clamp(Pawn->TraceDistance/FMath::Max(1.f,Speed)+1.f,1.f,60.f);
    // Keep existing hit-ledger debit/critical-roll semantics; registration does
    // not debit ammo a second time or fabricate a client inventory receipt.
    ServerReportShotStamp_Implementation();
    if (!Pawn->IsLocallyControlled()) WeaponShotNoise::Report(Pawn, Item->Definition, Pawn->GetGunsmithMuzzle(), Pawn->IsMuzzleSuppressed());
}

const AColdSteelPlayerState::FGenericLaunch* AColdSteelPlayerState::FindGenericLaunch(const FColdSteelNetHitReport& Report,const APawn* Pawn) const
{
    if(!Pawn||!Report.FireSequence||Report.AttackMeta!=0)return nullptr;
    const auto* Launch=GenericLaunches.Find(Report.FireSequence);
    return Launch&&Launch->Pawn.Get()==Pawn&&Launch->Item.InstanceId==Report.ItemInstance
        &&Launch->Item.Definition==Report.ItemDefinition&&Launch->Rounds==Report.ConvergenceRounds
        &&GetWorld()->GetTimeSeconds()<=Launch->Expires?Launch:nullptr;
}
