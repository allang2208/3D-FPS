#include "ColdSteelPlayerState.h"
#include "../Combat/RangedAttackQuery.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "../Weapons/Super90SpeedloaderAssets.h"
#include "../Weapons/Super90Spread.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Perception/AISense_Hearing.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"

namespace Super90Net
{
const TCHAR* AmmoIds[]={TEXT("ammo_12g"),TEXT("ammo_12g_flechette"),TEXT("ammo_12g_slug")};
double Clock(const UWorld* World)
{return World->GetGameState()?World->GetGameState()->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
void CopyMagazine(FColdSteelItem& To,const FColdSteelItem& From)
{
    To.Magazine=From.Magazine;To.VirtualMagazineAmmo=From.VirtualMagazineAmmo;
    To.LoadedAmmoType=From.LoadedAmmoType;
    WeaponReloadStages::SetNeedsCycle(To,WeaponReloadStages::NeedsCycle(From)?1:0);
}
}

uint32 AColdSteelPlayerState::RequestSuper90Shot(const FString& Weapon,const FVector& Eye,const FVector& Muzzle,
    const FVector& Aim,bool Aiming,int32 PredictedRounds)
{
    const uint32 Sequence=++Super90LocalSequence;
    Super90PredictedShots.Add({Sequence,Weapon,PredictedRounds});
    ServerSuper90Shot(Sequence,Weapon,Eye,Muzzle,Aim,Aiming,Super90Net::Clock(GetWorld()),GetPawn());
    return Sequence;
}
void AColdSteelPlayerState::RequestSuper90Reload(const FString& Weapon,const FString& Ammo)
{
    bSuper90ReloadPending=true;bSuper90SoftCancelSent=false;
    ServerSuper90Reload(++Super90LocalSequence,Weapon,Ammo,GetPawn());
}
void AColdSteelPlayerState::CancelSuper90Reload(bool Soft)
{
    if(!bSuper90ReloadPending||(Soft&&bSuper90SoftCancelSent))return;
    if(Soft)bSuper90SoftCancelSent=true;
    ServerSuper90Cancel(++Super90LocalSequence,Soft,GetPawn());
}

void AColdSteelPlayerState::RequestM870PumpInterrupt(const FString& Weapon,uint32 ShotSequence)
{
    const uint32 Sequence=++Super90LocalSequence;
    M870PredictedPumpInterrupts.Add(Weapon,Sequence);
    ServerM870PumpInterrupt(Sequence,Weapon,ShotSequence,Super90Net::Clock(GetWorld()),GetPawn());
}

void AColdSteelPlayerState::ServerM870PumpInterrupt_Implementation(uint32 Sequence,const FString& Weapon,
    uint32 ShotSequence,double InterruptedAt,APawn* SourcePawn)
{
    if(static_cast<int32>(Sequence-Super90ProcessedSequence)<=0)return;
    Super90ProcessedSequence=Sequence;
    const double Now=Super90Net::Clock(GetWorld());
    // Validate against the accepted shot, including its original rate. The
    // outgoing gun need not still occupy the active slot when this arrives.
    // Do not call Super90AuthorityPawn: it would select that old slot again.
    if(!ShadowModel||!SourcePawn||SourcePawn!=GetPawn()||SourcePawn!=M870AuthorityShotPawn.Get()
        ||Weapon!=M870AuthorityShotWeapon||ShotSequence!=M870AuthorityShotSequence
        ||!FMath::IsFinite(InterruptedAt)||InterruptedAt<Now-.9||InterruptedAt>Now+.1
        ||InterruptedAt+1.e-4<M870AuthorityShotTime||InterruptedAt>=M870AuthorityPumpClosedTime)
    {SendSuper90Ammo(true);return;}
    auto State=ShadowModel->Snapshot();
    auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Weapon&&I.Definition==M870WeaponAssets::Definition;});
    if(!Gun||!WeaponReloadStages::SetNeedsCycle(*Gun,1)){SendSuper90Ammo(true);return;}
    ShadowModel->AdoptNetMirror(State);
    bServerDirty=true;ServerSaveTimer=20.f;
    SendSuper90Ammo();
}

AFPSGAMECharacter* AColdSteelPlayerState::Super90AuthorityPawn(const FString& Weapon)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!HasAuthority()||!ShadowModel||!Pawn||Pawn->IsLocallyControlled())return nullptr;
    const auto* Gun=ShadowModel->FindItem(Weapon);
    if(!Gun||!TubeShotgunAssets::Supports(Gun->Definition)||Gun->Place!=1)return nullptr;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return nullptr;
    // The intent names an owned, equipped instance. Do not wait for the slow
    // profile heartbeat to discover an ordinary active-weapon-slot change.
    if(ShadowModel->Snapshot().ActiveWeaponSlot!=Gun->Cell)
    {
        auto State=ShadowModel->Snapshot();State.ActiveWeaponSlot=Gun->Cell;State.ActiveProductionTool.Reset();
        ShadowModel->AdoptNetMirror(State);ApplyShadowToServerPawn();
    }
    return Pawn;
}

void AColdSteelPlayerState::ServerSuper90Shot_Implementation(uint32 Sequence,const FString& Weapon,
    FVector_NetQuantize Eye,FVector_NetQuantize Muzzle,FVector_NetQuantizeNormal Aim,bool Aiming,double FiredAt,APawn* SourcePawn)
{
    if(static_cast<int32>(Sequence-Super90ProcessedSequence)<=0)return;
    Super90ProcessedSequence=Sequence;
    if(!SourcePawn||SourcePawn!=GetPawn()){SendSuper90Ammo(true);return;}
    auto* Pawn=Super90AuthorityPawn(Weapon);
    const double Now=Super90Net::Clock(GetWorld());
    const FVector Direction=FVector(Aim).GetSafeNormal();
    const auto* Gun=ShadowModel?ShadowModel->FindItem(Weapon):nullptr;
    const bool BadGeometry=!Pawn||!SourcePawn||SourcePawn!=Pawn||Eye.ContainsNaN()||Muzzle.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero()
        ||FVector::DistSquared(Eye,Pawn->GetPawnViewLocation())>FMath::Square(150.f)
        ||FVector::DistSquared(Muzzle,Eye)>FMath::Square(200.f)
        ||FVector::DotProduct(Direction,Pawn->GetBaseAimRotation().Vector())<FMath::Cos(FMath::DegreesToRadians(25.f));
    if(BadGeometry||!Gun||Gun->Magazine<=0||WeaponReloadStages::NeedsCycle(*Gun)||Super90Reload.Active
        ||Pawn->IsTraversing()
        ||!FMath::IsFinite(FiredAt)||FiredAt<Now-.9||FiredAt>Now+.1||FiredAt+1.e-4<Super90NextFireTime)
    {SendSuper90Ammo(true);return;}
    const auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    if(Move&&Move->bWantsToSprint){SendSuper90Ammo(true);return;}
    // Aim is part of this reliable fire intent. A movement packet travels on
    // a different channel and can still carry the previous hip/ADS flag.
    const FColdSteelItem FiredWeapon=*Gun;
    const int32 Spent=Pawn->ConvergenceParams.Enabled?Gun->Magazine:1;
    const float Scale=float(ColdSteelCombat::ConvergenceShotScale(Pawn->ConvergenceParams,Spent));
    const int32 Pellets=ShadowModel->AmmoProjectileCount(FiredWeapon,Super90WeaponAssets::PelletCount);
    const float Damage=Pawn->DamagePerShot*Scale/Pellets;
    const float Speed=Pawn->ProjectileSpeedCM,Range=Pawn->TraceDistance,EffectiveRange=Pawn->EffectiveWeaponRangeCM;
    const float Spread=Aiming?0.f:Pawn->GetHipSpread();
    const float PelletCone=Super90Spread::ConeRadians(Pellets,Aiming,Pawn->GetShotgunPelletSpreadMultiplier());
    const bool Duckbill=Pellets>1&&Pawn->HasShotgunDuckbill();
    FRandomStream Random(Super90Spread::Seed(Sequence));
    const FRotationMatrix Basis(Direction.Rotation());
    const float X=Random.FRandRange(-Spread,Spread),Y=Random.FRandRange(-Spread,Spread);
    const FVector Center=(Direction+Basis.GetUnitAxis(EAxis::Y)*X+Basis.GetUnitAxis(EAxis::Z)*Y).GetSafeNormal();
    const bool Suppressed=Pawn->IsMuzzleSuppressed();
    const auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* WorldFX=GetNetMode()==NM_DedicatedServer?nullptr:Body?Body->GetRemoteGunFX():nullptr;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Super90Authority),true,Pawn);FHitResult Obstruction;
    // Never start a server projectile on the far side of nearby cover.
    const bool Blocked=RangedAttackQuery::LineTraceSingle(GetWorld(), Pawn, Obstruction,Eye,Muzzle,ECC_Visibility,Params);
    const FVector Start=Blocked?FVector(Eye):FVector(Muzzle);
    const float TravelRange=Blocked?FMath::Min(Range,float(FVector::Distance(Eye,Obstruction.ImpactPoint))+1.f):Range;
    TArray<FVector_NetQuantizeNormal> Directions;Directions.Reserve(Pellets);
    // 服务端这一发的全部弹丸共用一个暴击样本（与客户端开火同口径）。
    Pawn->ShotCriticalRoll=FMath::FRand();
    for(int32 P=0;P<Pellets;++P)
    {
        const FVector Ray=Duckbill?Super90Spread::HorizontalFan(Center,PelletCone,P,Pellets,Random.FRand()):
            Pellets>1?Random.VRandCone(Center,PelletCone):Center;
        FHitResult Target;
        const FVector End=FVector(Eye)+Ray*Range;
        const FVector AimPoint=Blocked?Obstruction.ImpactPoint:
            RangedAttackQuery::LineTraceSingle(GetWorld(), Pawn, Target,Eye,End,ECC_Visibility,Params)?Target.ImpactPoint:End;
        const FVector Flight=(AimPoint-Start).GetSafeNormal();Directions.Add(Flight);
        // The server owns every projectile and its per-target penetration ledger.
        // Captured item/skill/ammo data remain valid after a subsequent switch.
        Pawn->Ballistics->Launch(Start,Flight,Speed,TravelRange,Damage,WorldFX,nullptr,EffectiveRange,&FiredWeapon,Pawn->ConvergenceParams.Enabled);
    }
    auto State=ShadowModel->Snapshot();
    if(auto* Item=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Weapon;}))
    {Item->Magazine-=Spent;Item->VirtualMagazineAmmo=FMath::Max(0,Item->VirtualMagazineAmmo-Spent);}
    ShadowModel->AdoptNetMirror(State);Pawn->MagazineAmmo=FMath::Max(0,FiredWeapon.Magazine-Spent);
    Super90LastFireTime=FiredAt;Super90NextFireTime=FiredAt+Pawn->EffectiveFireInterval();
    if(Pawn->IsM870Weapon())
    {
        M870AuthorityShotSequence=Sequence;M870AuthorityShotWeapon=Weapon;M870AuthorityShotPawn=Pawn;
        M870AuthorityShotTime=FiredAt;
        M870AuthorityPumpClosedTime=FiredAt+M870WeaponAssets::PumpClosed/Pawn->M870PumpPlayRate();
    }
    if(!Aiming)Pawn->CurrentSpread=FMath::Min(.018f,Pawn->CurrentSpread+.003f);
    LastValidatedShotAt=Now;bServerDirty=true;ServerSaveTimer=20.f;
    UAISense_Hearing::ReportNoiseEvent(Pawn,Pawn->GetActorLocation(),1.f,Pawn,Suppressed?1000.f:3600.f,
        Suppressed?TEXT("GunshotSuppressed"):TEXT("Gunshot"));
    MulticastSuper90Shot(Pawn,Start,Directions,Speed,TravelRange,Aiming,Suppressed,Weapon,GetWorld()->GetTimeSeconds(),Pawn->M870PumpPlayRate());
    SendSuper90Ammo();
}

void AColdSteelPlayerState::ServerSuper90Reload_Implementation(uint32 Sequence,const FString& Weapon,const FString& Ammo,APawn* SourcePawn)
{
    if(static_cast<int32>(Sequence-Super90ProcessedSequence)<=0)return;
    Super90ProcessedSequence=Sequence;
    if(!SourcePawn||SourcePawn!=GetPawn()){SendSuper90Ammo(true);return;}
    auto* Pawn=Super90AuthorityPawn(Weapon);
    if(!Pawn||!SourcePawn||SourcePawn!=Pawn||Super90Reload.Active||Pawn->IsTraversing()||Pawn->IsCastBlockingLeftHandAction())
    {SendSuper90Ammo(true);return;}
    const auto* Gun=ShadowModel->FindItem(Weapon);
    const bool Switch=!Ammo.IsEmpty();
    if(Switch&&!ShadowModel->CanSwitchAmmo(Weapon,Ammo)){SendSuper90Ammo(true);return;}
    using namespace Super90WeaponAssets;
    FSuper90ServerReload R;R.Pawn=Pawn;R.Weapon=Weapon;R.Ammo=Ammo;R.Started=GetWorld()->GetTimeSeconds();
    R.CycleOnly=!Switch&&WeaponReloadStages::NeedsCycle(*Gun);
    R.Empty=Switch||R.CycleOnly||Gun->Magazine==0;R.Loader=Pawn->bSuper90LoaderInstalled;
    const int32 Available=Switch?int32(FMath::Min<int64>(Pawn->MagazineCapacity,ShadowModel->PouchCount(Ammo))):
        Pawn->HasInfiniteReserveAmmo()?Pawn->MagazineCapacity:ShadowModel->AmmoCount();
    R.Count=R.CycleOnly?0:FMath::Min(Pawn->MagazineCapacity-(Switch?0:Gun->Magazine),Available);
    if(R.Loader)R.Count=FMath::Min(R.Count,Super90SpeedloaderAssets::Capacity);
    if(!R.CycleOnly&&R.Count<=0){SendSuper90Ammo(true);return;}
    UAnimSequence* Clip=R.Empty?Pawn->ReloadEmptyAnimation.Get():Pawn->ReloadAnimation.Get();
    if(R.Loader)
    {
        const auto& Clips=R.Empty?Pawn->Super90LoaderEmpty:Pawn->Super90LoaderNormal;
        const int32 Index=FMath::Min(R.Count,Super90SpeedloaderAssets::Capacity);
        Clip=Clips.IsValidIndex(Index)?Clips[Index].Get():nullptr;
    }
    else if(R.CycleOnly)Clip=Pawn->Super90LoaderEmpty.IsValidIndex(0)?Pawn->Super90LoaderEmpty[0].Get():nullptr;
    if(!Clip){SendSuper90Ammo(true);return;}
    R.Length=Clip->GetPlayLength();
    R.Rate=R.Empty?FullReload/FMath::Max(.01f,Pawn->EmptyReloadDuration):SingleReload/FMath::Max(.01f,Pawn->ReloadDuration);
    if(R.Loader)R.Rate=R.Empty?Super90SpeedloaderAssets::EmptyPacedReferenceFor(Pawn->IsM870Weapon())/FMath::Max(.01f,Pawn->EmptyReloadDuration):
        Super90SpeedloaderAssets::NormalPacedReference/FMath::Max(.01f,Pawn->ReloadDuration);
    R.Tail=TailForCount(R.Count);
    R.Duration=(R.Tail+R.Length-TailBegin)/R.Rate;
    if(R.Loader||R.CycleOnly)R.Duration=(R.Length+(R.Loader&&R.Count>0?Super90LoaderPushTiming::ExtraDuration:0.f))/R.Rate;
    R.Active=true;Super90Reload=R;SendSuper90Ammo();
}

void AColdSteelPlayerState::ServerSuper90Cancel_Implementation(uint32 Sequence,bool Soft,APawn* SourcePawn)
{
    if(static_cast<int32>(Sequence-Super90ProcessedSequence)<=0)return;
    Super90ProcessedSequence=Sequence;
    if(Super90Reload.Active&&SourcePawn&&SourcePawn==Super90Reload.Pawn.Get()&&SourcePawn==GetPawn())
    {
        if(Soft)Super90Reload.StopRequested=true;
        TickSuper90Authority(0.f);
        if(!Soft&&Super90Reload.Active)FinishSuper90AuthorityReload();
    }
    SendSuper90Ammo();
}

void AColdSteelPlayerState::TickSuper90Authority(float Delta)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(Pawn&&!Pawn->IsLocallyControlled()&&Pawn->IsTubeShotgunWeapon())
    {
        // Same movement/bloom response as the owner; only cosmetic recoil is local.
        Pawn->CurrentSpread=FMath::Max(0.f,Pawn->CurrentSpread-Delta*.018f);
        Pawn->MoveSpread=FMath::Lerp(Pawn->MoveSpread,FMath::Clamp(Pawn->HorizontalSpeed()/100.f*.004f,0.f,.020f),1.f-FMath::Exp(-6.f*Delta));
        const auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
        const float Air=Move&&!Move->IsMovingOnGround()&&!Move->bWantsToAim?.025f:0.f;
        Pawn->AirSpread=FMath::Lerp(Pawn->AirSpread,Air,1.f-FMath::Exp(-10.f*Delta));
    }
    if(!Super90Reload.Active)return;
    auto& R=Super90Reload;
    const auto* Gun=ShadowModel?ShadowModel->FindItem(R.Weapon):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||R.Pawn.Get()!=Pawn||!Gun||Pawn->ActiveInventoryWeapon!=R.Weapon||(Health&&Health->IsDead())||Pawn->IsTraversing()||Pawn->IsCastBlockingLeftHandAction())
    {FinishSuper90AuthorityReload();return;}
    using namespace Super90WeaponAssets;
    const float Time=float(GetWorld()->GetTimeSeconds()-R.Started)*R.Rate;
    if(R.StopRequested&&!R.Loader&&R.Count>0)
    {
        const int32 Stop=FMath::Clamp(R.Committed+(Time>TailForCount(R.Committed)+1.e-6f?1:0),1,R.Count);
        if(Stop<R.Count){R.Count=Stop;R.Tail=TailForCount(Stop);R.Duration=(R.Tail+R.Length-TailBegin)/R.Rate;SendSuper90Ammo();}
    }
    const float Source=R.Loader?(R.Count?Super90LoaderPushTiming::SourceTime(Time):Time):
        R.CycleOnly?Time:FeedClipTime(Time,R.Tail,R.Length);
    const bool LoaderContact=R.Loader&&R.Count>0&&R.Committed==0&&Source+1.e-6f>=Super90SpeedloaderAssets::LastContact(R.Count);
    while(R.Committed<R.Count&&(LoaderContact||(!R.Loader&&Time+1.e-6f>=Insert+R.Committed*LoopStep)))
    {
        const auto Before=ShadowModel->Snapshot();
        const int32 Want=R.Loader?R.Count:1;
        int32 Loaded=0;
        if(!R.Ammo.IsEmpty())
        {
            if(ShadowModel->CommitAmmoSwitch(R.Weapon,R.Ammo,Pawn->MagazineCapacity,1,Want,R.Loader||R.Committed+1==R.Count))
            {if(const auto* Current=ShadowModel->FindItem(R.Weapon))Loaded=Current->Magazine;R.Ammo.Reset();}
        }
        else Loaded=ShadowModel->ConsumeAmmo(Want,R.Loader||R.Committed+1==R.Count,!R.Loader,R.Empty?1:0);
        if(Loaded<=0){FinishSuper90AuthorityReload();SendSuper90Ammo(true);return;}
        R.Committed+=Loaded;RecordSuper90PouchChange(Before,ShadowModel->Snapshot());SendSuper90Ammo();
        if(R.Loader)break;
    }
    const float Ready=R.Loader?Super90SpeedloaderAssets::Release(R.Count,Pawn->IsM870Weapon()):Pawn->IsM870Weapon()?(R.CycleOnly?M870WeaponAssets::PumpClosed:M870WeaponAssets::ReloadClosed):(R.CycleOnly?CycleBoltReady:BoltRelease);
    if(R.Empty&&Source+1.e-6f>=Ready)
    {
        const auto* Current=ShadowModel->FindItem(R.Weapon);
        if(Current&&WeaponReloadStages::NeedsCycle(*Current))
        {if(!ShadowModel->CompleteWeaponReloadCycle(R.Weapon)){FinishSuper90AuthorityReload();return;}SendSuper90Ammo();}
    }
    if(GetWorld()->GetTimeSeconds()-R.Started+1.e-6>=R.Duration)FinishSuper90AuthorityReload();
}

void AColdSteelPlayerState::FinishSuper90AuthorityReload()
{
    Super90Reload.Active=false;bServerDirty=true;ServerSaveTimer=20.f;SendSuper90Ammo();
}
void AColdSteelPlayerState::RecordSuper90PouchChange(const FColdSteelProfile& Before,const FColdSteelProfile& After)
{
    if(Super90PouchHistory.IsEmpty())Super90PouchHistory.Add(0,{0,0,0});
    for(int32 I=0;I<3;++I)Super90PouchDelta[I]+=After.AmmoPouch.FindRef(Super90Net::AmmoIds[I])-Before.AmmoPouch.FindRef(Super90Net::AmmoIds[I]);
    Super90PouchHistory.Add(++Super90Revision,Super90PouchDelta);
    if(Super90Revision>512)Super90PouchHistory.Remove(Super90Revision-512);
    bServerDirty=true;ServerSaveTimer=20.f;
}
bool AColdSteelPlayerState::RebaseSuper90Upload(FColdSteelProfile& Incoming,const FColdSteelProfile& Previous,bool KeepServerPouch) const
{
    const TArray<int64> Zero={0,0,0};
    const auto* Base=IncomingSuper90Revision==0?&Zero:Super90PouchHistory.Find(IncomingSuper90Revision);
    if(!KeepServerPouch&&!Base)return false; // An expired upload cannot restore spent ammunition.
    for(int32 I=0;I<3;++I)
    {
        auto& Count=Incoming.AmmoPouch.FindOrAdd(Super90Net::AmmoIds[I]);
        Count=KeepServerPouch?Previous.AmmoPouch.FindRef(Super90Net::AmmoIds[I]):FMath::Clamp<int64>(Count+Super90PouchDelta[I]-(*Base)[I],0,ColdSteelAmmo::MaxCount);
    }
    const auto* Gunsmith=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    TMap<FString,int64> ResizeRefunds;bool Resized=false;
    for(auto& Item:Incoming.Items)if(TubeShotgunAssets::Supports(Item.Definition))
        if(const auto* Old=Previous.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;}))
        {
            Super90Net::CopyMagazine(Item,*Old);
            if(!Gunsmith)continue;
            const int32 Capacity=Gunsmith->CalculateItem(Item,Gunsmith->Installed(Item)).Capacity;
            const int32 OldCapacity=Gunsmith->CalculateItem(*Old,Gunsmith->Installed(*Old)).Capacity;
            if(Capacity==OldCapacity&&Item.Magazine<=Capacity)continue;
            Resized=true;
            const int32 Overflow=FMath::Max(0,Item.Magazine-Capacity);
            const int32 Virtual=FMath::Min(Overflow,Item.VirtualMagazineAmmo);
            Item.Magazine-=Overflow;Item.VirtualMagazineAmmo-=Virtual;
            // The owner already predicted a refund. Recompute this ammo type
            // from authority, including shots/reloads accepted after that preview.
            if(Capacity<OldCapacity||Overflow>0)
                ResizeRefunds.FindOrAdd(ShadowModel->AmmoDefinitionFor(Item))+=Overflow-Virtual;
        }
    for(const auto& Refund:ResizeRefunds)
    {
        const int64 Count=Previous.AmmoPouch.FindRef(Refund.Key)+Refund.Value;
        if(Count>ColdSteelAmmo::MaxCount)return false;
        Incoming.AmmoPouch.Add(Refund.Key,Count);
    }
    // Make the resize/refund one authoritative inventory revision. Repeated
    // or stale uploads then take the existing KeepServerPouch/items path.
    if(Resized)Incoming.CampfireInventoryRevision=Previous.CampfireInventoryRevision+1;
    return true;
}
void AColdSteelPlayerState::SendSuper90Ammo(bool Rejected)
{
    if(!ShadowModel)return;
    FSuper90NetAmmoState State;State.Acknowledged=Super90ProcessedSequence;State.Revision=Super90Revision;
    State.SourcePawn=GetPawn();State.InventoryRevision=ShadowModel->InventoryRevision();
    for(const auto* Id:Super90Net::AmmoIds)State.PouchCounts.Add(ShadowModel->PouchCount(Id));
    State.PouchDelta=Super90PouchDelta;State.Reloading=Super90Reload.Active;State.Rejected=Rejected;
    State.ReloadWeapon=Super90Reload.Weapon;State.ReloadCount=Super90Reload.Count;
    State.ReloadRate=Super90Reload.Rate;State.ReloadEmpty=Super90Reload.Empty;
    State.ReloadLoader=Super90Reload.Loader;State.ReloadCycleOnly=Super90Reload.CycleOnly;
    State.ReloadStopRequested=Super90Reload.StopRequested;
    for(const auto& I:ShadowModel->Items())if(TubeShotgunAssets::Supports(I.Definition))
    {
        auto& Mag=State.Magazines.AddDefaulted_GetRef();Mag.Instance=I.InstanceId;Mag.Ammo=ShadowModel->AmmoDefinitionFor(I);
        Mag.Count=I.Magazine;Mag.Virtual=I.VirtualMagazineAmmo;Mag.NeedsCycle=WeaponReloadStages::NeedsCycle(I);
    }
    ClientSuper90Ammo(State);
}
void AColdSteelPlayerState::TickSuper90Recovery()
{
    if(GetNetMode()!=NM_Client)return;
    if(Super90ClientPawn.Get()!=GetPawn())
    {
        Super90ClientPawn=GetPawn();Super90PredictedShots.Reset();M870PredictedPumpInterrupts.Reset();
        Super90ServerWeapons.Reset();
        bSuper90ReloadPending=bSuper90SoftCancelSent=false;
    }
    if(!bPendingSuper90State)return;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!GetPawn()||PendingSuper90State.SourcePawn!=GetPawn()||Model->RuntimePawn()!=GetPawn()||PendingSuper90State.InventoryRevision>Model->InventoryRevision())return;
    const auto Receipt=PendingSuper90State;bPendingSuper90State=false;
    ClientSuper90Ammo_Implementation(Receipt);
}
void AColdSteelPlayerState::ClientSuper90Ammo_Implementation(const FSuper90NetAmmoState& Receipt)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Receipt.PouchDelta.Num()!=3||Receipt.PouchCounts.Num()!=3)return;
    // The new pawn's receipt may precede possession on another actor channel.
    // Retain it until its identity matches; an old-pawn receipt never writes
    // magazine/chamber state into a different life while waiting.
    if(!Pawn||Receipt.SourcePawn!=Pawn||!Pawn->IsLocallyControlled()||Model->RuntimePawn()!=Pawn||Receipt.InventoryRevision>Model->InventoryRevision())
    {PendingSuper90State=Receipt;bPendingSuper90State=true;return;}
    if(Super90ClientPawn.Get()!=Pawn)
    {Super90ClientPawn=Pawn;Super90PredictedShots.Reset();M870PredictedPumpInterrupts.Reset();Super90ServerWeapons.Reset();bSuper90ReloadPending=bSuper90SoftCancelSent=false;}
    if(static_cast<int32>(Receipt.Revision-Super90AppliedRevision)<0)return;
    bPendingSuper90State=false;Model->SyncRuntime();auto State=Model->Snapshot();
    for(int32 I=0;I<3;++I)
    {
        auto& Count=State.AmmoPouch.FindOrAdd(Super90Net::AmmoIds[I]);
        // Counts are tied to the inventory revision; an old receipt cannot undo a newer pickup/trade.
        if(Receipt.InventoryRevision==State.CampfireInventoryRevision)
            Count=FMath::Clamp<int64>(Receipt.PouchCounts[I],0,ColdSteelAmmo::MaxCount);
    }
    Super90AppliedRevision=Receipt.Revision;Super90AppliedPouchDelta=Receipt.PouchDelta;
    Super90ServerWeapons.Reset();
    for(const auto& Mag:Receipt.Magazines)Super90ServerWeapons.Add(Mag.Instance);
    Super90PredictedShots.RemoveAll([&](const auto& Shot){return static_cast<int32>(Shot.Sequence-Receipt.Acknowledged)<=0;});
    for(auto It=M870PredictedPumpInterrupts.CreateIterator();It;++It)
        if(static_cast<int32>(It.Value()-Receipt.Acknowledged)<=0)It.RemoveCurrent();
    for(const auto& Mag:Receipt.Magazines)if(auto* Item=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Mag.Instance;}))
    {
        Item->Magazine=Mag.Count;Item->VirtualMagazineAmmo=Mag.Virtual;Item->LoadedAmmoType=Mag.Ammo;
        WeaponReloadStages::SetNeedsCycle(*Item,(Mag.NeedsCycle||M870PredictedPumpInterrupts.Contains(Mag.Instance))?1:0);
        for(const auto& Prediction:Super90PredictedShots)if(Prediction.Weapon==Mag.Instance)
        {Item->Magazine=FMath::Max(0,Item->Magazine-Prediction.Rounds);Item->VirtualMagazineAmmo=FMath::Max(0,Item->VirtualMagazineAmmo-Prediction.Rounds);}
    }
    Model->AdoptNetMirror(State);Pawn->ApplyColdSteelProfile(Model);
    // A reply for an older shot must not clear a newer local reload request.
    if(Receipt.SourcePawn==Pawn&&Receipt.Acknowledged==Super90LocalSequence)
    {
        const bool FinishedReload=bSuper90ReloadPending&&!Receipt.Reloading;
        bSuper90ReloadPending=Receipt.Reloading;
        if(Receipt.Reloading)Pawn->ReconcileSuper90Reload(Receipt);
        // A rejected stale profile upload is not a rejected active reload.
        if(Receipt.Rejected&&!Receipt.Reloading&&Pawn->IsTubeShotgunWeapon()&&Pawn->IsReloading())Pawn->InterruptReload();
        if(FinishedReload)Model->SaveNow();
    }
}
void AColdSteelPlayerState::PreserveSuper90ClientAmmo(FColdSteelProfile& Incoming) const
{
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model)return;
    const auto Current=Model->Snapshot();
    for(const auto* Id:Super90Net::AmmoIds)Incoming.AmmoPouch.Add(Id,Current.AmmoPouch.FindRef(Id));
    for(auto& I:Incoming.Items)if(TubeShotgunAssets::Supports(I.Definition))
        if(const auto* Local=Current.Items.FindByPredicate([&](const auto& V){return V.InstanceId==I.InstanceId;}))Super90Net::CopyMagazine(I,*Local);
}
void AColdSteelPlayerState::MulticastSuper90Shot_Implementation(AFPSGAMECharacter* Shooter,FVector_NetQuantize Muzzle,
    const TArray<FVector_NetQuantizeNormal>& Directions,float Speed,float Range,bool Aiming,bool Suppressed,const FString& Weapon,float FiredAt,float PumpRate)
{
    if(!Shooter||Shooter->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer)return;
    auto* Body=Shooter->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(Body)Body->PresentSuper90Shot(Weapon,FiredAt,Aiming,Suppressed,PumpRate);
    // Remote tracers are cosmetic; only the server rounds above can apply hits.
    // Listen-server observers already have the authoritative rounds above.
    // Give those rounds their world FX at launch, never launch a duplicate here.
    if(!Shooter->HasAuthority())for(const auto& Direction:Directions)
        Shooter->Ballistics->Launch(Muzzle,Direction,Speed,Range,0.f,Body?Body->GetRemoteGunFX():nullptr,nullptr,0.f,nullptr,false,true);
}
