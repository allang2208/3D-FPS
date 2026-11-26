#include "FPSConsumableAuditCommandlet.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelPreparedHit.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

void UFPSConsumableAuditCommandlet::RunAuthorityFoodAudit(UWorld* World,UColdSteelStatusModel* Model,
    TFunctionRef<void(bool,const FString&,const FString&)> Check)
{
    auto Report=[&](bool Pass,const FString& Name)
    {Check(Pass,TEXT("generic launch authority: ")+Name,FString());return Pass;};
    FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/FoodSpoilage20261015/TestRuns"));
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
    FPaths::NormalizeDirectoryName(Root);FPaths::NormalizeDirectoryName(Saved);
    if(!Report(World&&Model&&Model->IsAudit()&&World==Model->GetWorld()
        &&Model->ProfileSlot().StartsWith(TEXT("ColdSteel_FoodSpoilageAudit_"))&&Saved.StartsWith(Root+TEXT("/"))
        &&World->GetNetMode()==NM_Standalone&&!World->GetNetDriver(),
        TEXT("requires isolated real catalog; direct authority calls, no network transport")))return;
    auto* Gunsmith=World->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!Report(Gunsmith!=nullptr,TEXT("real gunsmith catalog initialized")))return;
    const auto HostBefore=Model->Snapshot();const double OriginalTime=World->GetTimeSeconds();
    auto* Controller=World->SpawnActor<ASkillAuditRemoteController>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
    auto* State=World->SpawnActor<AColdSteelPlayerState>();
    auto* Target=World->SpawnActor<AActor>();
    if(!Report(Controller&&Pawn&&State&&Target&&!Pawn->HasActorBegunPlay(),TEXT("isolated authority actors created without BeginPlay")))return;
    ON_SCOPE_EXIT
    {
        State->ShadowModel=nullptr;Pawn->NetShadowProfile=nullptr;
        Controller->UnPossess();Pawn->Destroy();State->Destroy();Controller->Destroy();Target->Destroy();
        World->TimeSeconds=OriginalTime;
    };
    State->SetOwner(Controller);Controller->SetPlayerState(State);Controller->Possess(Pawn);Pawn->SetPlayerState(State);
    auto Gun=Model->CreateItem(TEXT("ue_m4a1"));Gun.Place=1;Gun.Cell=6;Gun.Magazine=5;
    auto Bread=Model->CreateItem(TEXT("bread"));Bread.Place=0;Bread.Cell=0;
    auto Profile=HostBefore;Profile.Items={Gun,Bread};Profile.ActiveWeaponSlot=6;Profile.ActiveProductionTool.Reset();
    Profile.Health=100.;Profile.DungeonRun={};
    auto* Shadow=Model->CreateShadowModel(Profile);State->ShadowModel=Shadow;Pawn->NetShadowProfile=Shadow;
    Pawn->ActiveInventoryWeapon=Gun.InstanceId;Pawn->ActiveInventoryWeaponDefinition=Gun.Definition;
    Pawn->bInventoryWeaponReady=true;Pawn->WeaponState=EAKMWeaponState::Idle;
    Pawn->MagazineCapacity=Gunsmith->CalculateItem(Gun,Gunsmith->Installed(Gun)).Capacity;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Report(Shadow&&Health&&Pawn->MagazineCapacity>0&&State->IsGenericFirearm(Gun)
        &&State->CanAuthorityBeginConsumable(Pawn),TEXT("actual equipped rifle and living authority pawn are ready")))return;
    const double Now=World->GetTimeSeconds();
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,1,1);
    FColdSteelNetHitReport Hit;Hit.FireSequence=1;Hit.ItemInstance=Gun.InstanceId;
    Hit.ItemDefinition=Gun.Definition;Hit.ConvergenceRounds=1;
    if(!Report(State->FindGenericLaunch(Hit,Pawn)!=nullptr,
        TEXT("real begin accepts a held rifle and creates its trusted launch receipt")))return;
    const auto First=*State->FindGenericLaunch(Hit,Pawn);
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,1,1);
    Report(State->GenericLaunches.Num()==1&&State->GenericLaunches.FindChecked(1).Expires==First.Expires,
        TEXT("duplicate begin cannot renew a launch or create a second receipt"));
    Report(!State->CanAuthorityBeginConsumable(Pawn),TEXT("accepted shot recovery blocks a new food action"));
    // Advance only the isolated world clock; no gameplay or assets are ticked.
    World->TimeSeconds=First.ReadyAt+1.e-4;
    const FGuid UseId=FGuid::NewGuid();
    State->ServerBeginConsumableUse_Implementation(Pawn,UseId,Bread.InstanceId,TEXT("bread"));
    if(!Report(State->HasAuthorityConsumableReservation(Pawn),TEXT("real food begin reserves hands after shot recovery")))return;
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,2,1);
    Report(!State->GenericLaunches.Contains(2)&&State->LastGenericLaunchSequence==2,
        TEXT("real rifle begin is refused during food and retires its rejected sequence"));
    Report(State->FindGenericLaunch(Hit,Pawn)!=nullptr,
        TEXT("food reservation preserves the legitimate already launched projectile receipt"));
    State->ServerCancelConsumableUse_Implementation(UseId);
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,2,1);
    Report(!State->GenericLaunches.Contains(2),TEXT("cancelling food cannot replay the rejected rifle begin"));
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,3,1);
    Report(State->GenericLaunches.Contains(3),TEXT("a genuinely new rifle begin succeeds after food cancellation"));
    State->GenericLaunches.FindChecked(1).Expires=Now-1.;
    Report(!State->FindGenericLaunch(Hit,Pawn),TEXT("expired old projectile receipt cannot be reused"));
    auto Empty=Shadow->Snapshot();Empty.Items[0].Magazine=0;Shadow->AdoptNetMirror(Empty);
    auto& Ledger=State->ServerGunLedgers.FindOrAdd(Gun.InstanceId);Ledger.Magazine=0;Ledger.ReloadReadyAt=Now-1.;
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,4,1);
    Report(State->GenericLaunches.Contains(4)&&State->GenericLaunches.FindChecked(4).Item.Magazine==Pawn->MagazineCapacity
        &&Ledger.Magazine==0,TEXT("completed authority reload accepts first shot before stale zero-ammo shadow upload; no double debit"));
    Ledger.ReloadReadyAt=Now+1.;
    State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,5,1);
    Report(!State->GenericLaunches.Contains(5),TEXT("incomplete authority reload rejects a new shot"));
    Ledger.Magazine=5;Ledger.ReloadReadyAt=0.;
    Health->Health=0.;State->ServerRememberGenericLaunch_Implementation(Pawn,Gun.InstanceId,6,1);
    Report(!State->GenericLaunches.Contains(6),TEXT("dead pawn cannot acquire a new launch receipt"));
    Health->Health=100.;Ledger.Magazine=5;Ledger.ReloadReadyAt=0.;
    State->ServerRememberGenericLaunch_Implementation(Pawn,TEXT("another-instance"),7,1);
    Report(!State->GenericLaunches.Contains(7),TEXT("mismatched weapon instance cannot acquire a new receipt"));
    // A collision-free target is enough for preparation: no SettleHitReport,
    // ApplyHit or actor damage is called by this fixture.
    Pawn->SetActorLocation(FVector(100000,100000,100000));
    Target->SetActorLocation(Pawn->GetPawnViewLocation()+FVector(100,0,0));
    const auto HitFor=[&](const FColdSteelItem& Weapon,uint32 Sequence)
    {
        FColdSteelNetHitReport R;R.Target=Target;R.ItemInstance=Weapon.InstanceId;R.ItemDefinition=Weapon.Definition;
        R.FireSequence=Sequence;R.ConvergenceRounds=1;R.Flags=(1<<1)|(1<<6);
        R.AimOrigin=Pawn->GetPawnViewLocation();R.ImpactPoint=Pawn->GetPawnViewLocation()+FVector(100,0,0);
        R.Direction=FVector::ForwardVector;R.HitNormal=-FVector::ForwardVector;R.ClientFireTime=World->GetTimeSeconds();
        return R;
    };
    const auto Prepare=[&](const FColdSteelNetHitReport& R)
    {State->FireTokenBucket=6.f;State->LastFireTokenRefillAt=World->GetTimeSeconds();FColdSteelPreparedHit P;return State->PrepareHitReport(R,P);};
    World->TimeSeconds=FMath::Max(World->GetTimeSeconds(),State->GenericLaunchReadyAt+1.e-4);
    const FGuid LaterUse=FGuid::NewGuid();
    State->ServerBeginConsumableUse_Implementation(Pawn,LaterUse,Bread.InstanceId,TEXT("bread"));
    const auto OldBullet=HitFor(Gun,3);
    Report(State->HasAuthorityConsumableReservation(Pawn)&&Prepare(OldBullet),
        TEXT("real hit preparation accepts the earlier rifle projectile during food without settling damage"));
    State->ServerCancelConsumableUse_Implementation(LaterUse);
    auto Ricochet=OldBullet;Ricochet.Flags|=1<<4;FString Reject;const FColdSteelItem* Declared=nullptr;
    Report(!State->ValidateHitReport(Ricochet,Pawn,Reject,Declared)&&Reject==TEXT("ricochet is server simulated"),
        TEXT("client cannot disguise a new attack as a server-simulated ricochet"));
    const auto Equip=[&](const TCHAR* Definition)
    {
        auto Weapon=Model->CreateItem(Definition);Weapon.Place=1;Weapon.Cell=6;Weapon.Magazine=5;
        auto P=Profile;P.Items={Weapon,Bread};Shadow->AdoptNetMirror(P);
        Pawn->ActiveInventoryWeapon=Weapon.InstanceId;Pawn->ActiveInventoryWeaponDefinition=Weapon.Definition;
        Pawn->MagazineCapacity=Gunsmith->CalculateItem(Weapon,Gunsmith->Installed(Weapon)).Capacity;
        return Weapon;
    };
    const auto Pistol=Equip(TEXT("ue_m1911"));
    const auto MissingPistol=HitFor(Pistol,0);
    Report(!Prepare(MissingPistol),TEXT("zero-sequence pistol hit cannot bypass its reliable start"));
    auto& PistolLaunch=State->RegisteredPistolShots.Add(900);
    PistolLaunch.Item=Pistol;PistolLaunch.Pawn=Pawn;PistolLaunch.At=World->GetTimeSeconds();PistolLaunch.Rounds=1;
    State->ServerGunLedgers.FindOrAdd(Pistol.InstanceId).CriticalRolls.Add(900,.5f);
    Report(Prepare(HitFor(Pistol,900)),TEXT("positive control: matching existing pistol receipt still prepares normally"));
    const auto Sniper=Equip(TEXT("ue_m24"));
    Report(!Prepare(HitFor(Sniper,901)),TEXT("unknown sniper launch cannot fall back to the currently held gun"));
    auto& SniperLaunch=State->M24Launches.Add(901);
    SniperLaunch.Item=Sniper;SniperLaunch.Pawn=Pawn;SniperLaunch.At=World->GetTimeSeconds();SniperLaunch.Expires=World->GetTimeSeconds()+10.;
    SniperLaunch.Rounds=1;SniperLaunch.Eye=Pawn->GetPawnViewLocation();SniperLaunch.ViewForward=FVector::ForwardVector;
    SniperLaunch.TraceRange=SniperLaunch.EffectiveRange=10000.f;SniperLaunch.Interval=.5;SniperLaunch.MaxTargets=1;
    State->ServerGunLedgers.FindOrAdd(Sniper.InstanceId).CriticalRolls.Add(901,.5f);
    Report(Prepare(HitFor(Sniper,901)),TEXT("positive control: matching existing sniper receipt still prepares normally"));
    const auto Bow=Equip(TEXT("bow_dark"));Reject.Reset();Declared=nullptr;
    Report(ColdSteelInventory::IsBow(Bow)&&!State->ValidateHitReport(HitFor(Bow,902),Pawn,Reject,Declared)
        &&Reject==TEXT("bow projectile is server simulated"),TEXT("client bow projectile cannot bypass the server-owned arrow"));
    Pawn->ActiveInventoryWeaponDefinition=Gun.Definition;Pawn->FireInterval=.1f;
    Pawn->TurboRampParams.Enabled=true;Pawn->TurboRampParams.StartMultiplier=1.;Pawn->TurboRampParams.PeakMultiplier=.5;
    Pawn->TurboRampParams.Seconds=3.;Pawn->TurboRampSeconds=0.;
    const double Fast=State->FastestAuthorityFireInterval(Pawn);
    Pawn->TurboRampSeconds=3.;
    Report(Fast>0.&&Fast<.051&&FMath::IsNearlyEqual(Fast,State->FastestAuthorityFireInterval(Pawn),1.e-8),
        TEXT("allowed turbo endpoint is independent of remote trigger-held ramp presentation time"));
    State->RecordAuthorityShotRecovery(Pawn,.2);
    Report(!State->CanAuthorityBeginConsumable(Pawn)&&State->FindGenericLaunch(OldBullet,Pawn),
        TEXT("trusted firearm recovery blocks new food without invalidating earlier projectile receipts"));
    World->TimeSeconds=State->AuthorityShotRecoveryUntil+1.e-4;
    Report(State->CanAuthorityBeginConsumable(Pawn),TEXT("firearm recovery releases hands without waiting for projectile expiry"));
    const auto HostAfter=Model->Snapshot();bool HostUnchanged=HostBefore.Items.Num()==HostAfter.Items.Num();
    if(HostUnchanged)for(int32 I=0;I<HostBefore.Items.Num();++I)
        HostUnchanged&=FColdSteelItem::StaticStruct()->CompareScriptStruct(&HostBefore.Items[I],&HostAfter.Items[I],0);
    Report(HostUnchanged&&HostBefore.CampfireInventoryRevision==HostAfter.CampfireInventoryRevision,
        TEXT("authority entry checks never mutate the host inventory or its durable revision"));
}
