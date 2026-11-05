#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Weapons/M24WeaponAssets.h"
#include "../Weapons/WeaponReloadStages.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

void AColdSteelPlayerState::ServerRememberM24Launch_Implementation(APawn* SourcePawn,const FString& Instance,uint32 Sequence,int32 Rounds)
{
    auto* Shooter=Cast<AFPSGAMECharacter>(GetPawn());
    if(!HasAuthority()||!Shooter||SourcePawn!=Shooter||!ShadowModel||!Shooter->IsM24Weapon()||!Sequence)return;
    if(LastM24LaunchSequence&&int32(Sequence-LastM24LaunchSequence)<=0)return;
    const auto* Gun=ShadowModel->Equipped();
    if(!Gun||Gun->Definition!=M24WeaponAssets::Definition||Gun->InstanceId!=Instance||Instance!=Shooter->ActiveInventoryWeapon)return;
    if(const auto* Health=Shooter->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(WeaponReloadStages::NeedsCycle(*Gun)||Rounds<1||Rounds>Gun->Magazine||Rounds>Shooter->GetMagazineCapacity())return;
    if(Rounds>1&&(!Shooter->ConvergenceParams.Enabled||Rounds!=Gun->Magazine))return;

    const double Now=GetWorld()->GetTimeSeconds();
    for(auto It=M24Launches.CreateIterator();It;++It)
    {
        const auto& Old=It.Value();
        if(Old.Pawn.Get()!=Shooter||Now>Old.Expires){It.RemoveCurrent();continue;}
        if(Old.Item.InstanceId==Instance&&Now-Old.At+.05<Old.Interval)return;
    }
    if(M24Launches.Num()>=64)return;
    LastM24LaunchSequence=Sequence;
    auto& Launch=M24Launches.Add(Sequence);
    Launch.Item=*Gun;Launch.Pawn=Shooter;Launch.Rounds=Rounds;Launch.At=Now;
    Launch.Eye=Shooter->GetPawnViewLocation();Launch.TraceRange=Shooter->TraceDistance;
    Launch.ViewForward=Shooter->GetBaseAimRotation().Vector();
    Launch.EffectiveRange=Shooter->EffectiveWeaponRangeCM;Launch.Interval=Shooter->EffectiveFireInterval();
    Launch.MaxTargets=1+FMath::Max(0,ColdSteelCombat::Snapshot(Shooter,Gun).Piercing);
    static const auto* Scale=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Ballistics.SpeedScale"));
    const float Speed=Shooter->ProjectileSpeedCM*(Scale?FMath::Clamp(Scale->GetFloat(),.05f,10.f):1.f);
    Launch.Expires=Now+FMath::Clamp(Launch.TraceRange/FMath::Max(1.f,Speed)+1.f,1.f,60.f);
    ServerReportShotStamp_Implementation();
}

const AColdSteelPlayerState::FM24Launch* AColdSteelPlayerState::FindM24Launch(const FColdSteelNetHitReport& Report,const APawn* Shooter) const
{
    if(Report.ItemDefinition!=M24WeaponAssets::Definition||Report.AttackMeta!=0||!Report.FireSequence
        ||(Report.Flags&(1<<4))||!(Report.Flags&(1<<6)))return nullptr;
    const auto* Launch=M24Launches.Find(Report.FireSequence);
    return Launch&&Launch->Pawn.Get()==Shooter&&Launch->Item.InstanceId==Report.ItemInstance
        &&Launch->Rounds==Report.ConvergenceRounds&&GetWorld()->GetTimeSeconds()<=Launch->Expires?Launch:nullptr;
}
