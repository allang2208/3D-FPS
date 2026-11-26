#include "ColdSteelPlayerState.h"
#include "PistolAmmoHelpers.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/DanWesson715WeaponAssets.h"
#include "../Weapons/RSH12WeaponAssets.h"
#include "../Weapons/DualPistolReloadTiming.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void AColdSteelPlayerState::ServerPistolReload_Implementation(uint32 Serial,const FString& Instance,
    const FString& Ammo,int32 ActiveSlot,APawn* SourcePawn)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!HasAuthority()||!Pawn||SourcePawn!=Pawn||!Serial||static_cast<int32>(Serial-PistolProcessedControl)<=0)return;
    PistolProcessedControl=Serial;
    TickPistolAuthority();
    if(const auto* Existing=PistolReloads.Find(Instance);Existing&&Existing->Active){SendPistolAmmo();return;}
    FPistolServerReload R;R.Serial=Serial;R.Instance=Instance;R.Pawn=Pawn;R.ActiveSlot=ActiveSlot;
    const auto Reject=[&](){R.Rejected=true;PistolReloads.Add(Instance,R);SendPistolAmmo();};
    const auto* Gun=ShadowModel?ShadowModel->FindItem(Instance):nullptr;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!Gun||!G||!ColdSteelInventory::IsDualPistol(*Gun)||Gun->Place!=1||(ActiveSlot!=6&&ActiveSlot!=9)
        ||(Gun->Cell!=ActiveSlot&&Gun->Cell!=(ActiveSlot==6?8:11))||(Health&&Health->IsDead())
        ||Pawn->IsTraversing()||ShadowModel->ActiveProductionTool()){Reject();return;}
    const int32 OffSlot=ActiveSlot==6?8:11;
    const auto* Main=ShadowModel->Equipped(ActiveSlot);const auto* Off=ShadowModel->Equipped(OffSlot);
    if(Off&&ColdSteelInventory::IsWoodenTorch(*Off)&&
        (HasGenericMeleeBusy(Pawn)||IsQuickCombatExecuting(Pawn)||HasAuthorityConsumableReservation(Pawn))){Reject();return;}
    R.Side=Gun->Cell==OffSlot?1:0;
    if(R.Side&&Main&&!ColdSteelInventory::IsDualPistol(*Main)&&!ColdSteelInventory::UsesStaffMelee(*Main)&&!G->IsStaff(Main->Definition)
        &&!UKukriWeaponComponent::IsKukri(*Main)){Reject();return;}
    R.DualExecutor=R.Side==1||(Off&&ColdSteelInventory::IsDualPistol(*Off));
    if((R.Side==1||!R.DualExecutor)&&Pawn->IsCastBlockingLeftHandAction()){Reject();return;}
    if(ShadowModel->Current.ActiveWeaponSlot!=ActiveSlot)
    {ShadowModel->Current.ActiveWeaponSlot=ActiveSlot;ApplyShadowToServerPawn();Gun=ShadowModel->FindItem(Instance);}
    if(!Gun){Reject();return;}
    R.Switching=!Ammo.IsEmpty();R.Ammo=R.Switching?Ammo:ShadowModel->AmmoDefinitionFor(*Gun);
    if(R.Switching&&!ShadowModel->CanSwitchAmmo(Instance,Ammo)){Reject();return;}
    const auto Parts=G->Installed(*Gun);const auto* Definition=G->Weapon(Gun->Definition);
    if(!Definition){Reject();return;}
    const auto Stats=R.DualExecutor?G->Calculate(Gun->Definition,Parts,true):G->CalculateItem(*Gun,Parts);
    R.Capacity=Stats.Capacity;R.Revolver=PistolAmmo::Revolver(*Gun);
    R.Loader=R.Revolver&&Parts.FindRef(TEXT("reload_device"))==
        (Gun->Definition==TEXT("ue_rsh12")?RSH12WeaponAssets::Speedloader:DanWesson715WeaponAssets::Speedloader);
    R.CycleOnly=!R.Switching&&WeaponReloadStages::NeedsCycle(*Gun);
    R.Empty=R.Switching||R.CycleOnly||Gun->Magazine==0||R.Loader;
    const bool Infinite=!R.Switching&&Pawn->HasInfiniteReserveAmmoFor(R.Ammo);
    const int32 Available=Infinite?R.Capacity:int32(FMath::Min<int64>(R.Capacity,ShadowModel->PouchCount(R.Ammo)));
    R.Count=R.CycleOnly?0:FMath::Min(R.Capacity-(R.Switching||R.Loader?0:Gun->Magazine),Available);
    if(R.Capacity<=0||(!R.CycleOnly&&R.Count<=0)){Reject();return;}
    const bool Lone=R.Side==1&&!Main;
    const bool DualClock=R.DualExecutor&&!Lone;
    const int32 ClipCount=R.CycleOnly?1:R.Count;
    const int32 Start=R.Empty?0:Gun->Magazine;
    const FString ClipRole=!R.Revolver?(R.Empty?TEXT("reload_empty"):TEXT("reload")):
        R.Loader?TEXT("speed_0"):FString::Printf(TEXT("single_%d_%d"),Start,ClipCount);
    float SourceLength=R.Revolver?(R.Loader?3.85f:DanWesson715WeaponAssets::SingleDuration(ClipCount,R.Empty)):(R.Empty?2.25f:1.75f);
    float ClipLength=SourceLength;
    if(R.DualExecutor&&Pawn->DualPistols&&Pawn->DualPistols->IsActive())
    {if(const auto* Clip=Pawn->DualPistols->Hand(R.Side).Clips.FindRef(ClipRole).Get())ClipLength=Clip->GetPlayLength();}
    else if(!R.Revolver)
    {
        const auto* Clip=R.Empty?Pawn->ReloadEmptyAnimation.Get():Pawn->ReloadAnimation.Get();
        if(Clip)SourceLength=ClipLength=Clip->GetPlayLength();
    }
    const float Modified=float(ColdSteelWeaponStats::Reload(Gun,ShadowModel,R.Empty?Stats.EmptyReload:Stats.Reload));
    const float Base=R.Loader&&(!R.DualExecutor||Gun->Definition==TEXT("ue_rsh12"))?3.85f:
        float(R.Empty?Definition->Base.EmptyReload:Definition->Base.Reload);
    const float SourceRate=FMath::Max(.01f,Base)/FMath::Max(.05f,Modified*(DualClock?DualPistolReload::TimeScale:1.f))*SourceLength/FMath::Max(.01f,ClipLength);
    const auto Stages=WeaponReloadStages::ForWeapon(Gun->Definition,R.Empty,false,R.Revolver&&!R.Loader,ClipCount);
    const auto Linear=[&](float Source){return DualClock?DualPistolReloadTiming::LinearSourceTime(Source,R.Revolver,R.Loader):Source;};
    const float LinearStart=R.CycleOnly?Linear(Stages.CycleBegin):0.f;
    const auto Seconds=[&](float Source){return FMath::Max(0.f,(Linear(Source)-LinearStart)/SourceRate);};
    R.Duration=Seconds(SourceLength);R.ReadyAt=Seconds(Stages.Ready);
    using namespace DanWesson715WeaponAssets;
    const float EjectSource=R.Loader?Eject/NormalReload*3.85f:
        R.Empty?(Gun->Definition==TEXT("ue_rsh12")&&R.DualExecutor?Eject:EmptyCaseClear):R.DualExecutor?Open+.06f:Open;
    R.EjectAt=Seconds(EjectSource);R.Cleared=R.CycleOnly||R.Switching||!R.Revolver;
    if(!R.CycleOnly)
    {
        if(R.Revolver&&!R.Loader)for(int32 I=0;I<R.Count;++I)R.Seats.Add(Seconds(SingleSeatTime(I,R.Empty)));
        else R.Seats.Add(Seconds(R.Loader?Seat/NormalReload*3.85f:Stages.Insert));
    }
    R.Started=GetWorld()->GetTimeSeconds();R.Active=true;
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire")))UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_SERVER_BEGIN id=%s serial=%u side=%d cycle=%d count=%d duration=%f"),*Instance,Serial,R.Side,R.CycleOnly,R.Count,R.Duration);
    PistolReloads.Add(Instance,MoveTemp(R));SendPistolAmmo();
}

void AColdSteelPlayerState::ServerPistolCancel_Implementation(uint32 Serial,const FString& Instance,uint32 ReloadSerial,APawn* SourcePawn)
{
    if(!SourcePawn||SourcePawn!=GetPawn()||!Serial||static_cast<int32>(Serial-PistolProcessedControl)<=0)return;
    PistolProcessedControl=Serial;
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire")))UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_SERVER_CANCEL id=%s serial=%u reload=%u active_serial=%u"),*Instance,Serial,ReloadSerial,PistolReloads.FindRef(Instance).Serial);
    // Commit only contacts already reached before cancellation. Never let an
    // old cancel end a newer action on the same pistol instance.
    TickPistolAuthority();
    if(auto* R=PistolReloads.Find(Instance);R&&R->Serial==ReloadSerial)FinishPistolReload(*R);
    SendPistolAmmo();
}

void AColdSteelPlayerState::TickPistolAuthority()
{
    if(!HasAuthority()||!ShadowModel)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    bool Changed=false;
    for(auto& Pair:PistolReloads)
    {
        auto& R=Pair.Value;if(!R.Active)continue;
        auto* Gun=ShadowModel->Current.Items.FindByPredicate([&](const auto& I){return I.InstanceId==R.Instance;});
        if(!Pawn||R.Pawn.Get()!=Pawn||!Gun||Gun->Place!=1||ShadowModel->Current.ActiveWeaponSlot!=R.ActiveSlot
            ||Gun->Cell!=(R.Side?(R.ActiveSlot==6?8:11):R.ActiveSlot)||ShadowModel->ActiveProductionTool()
            ||(Health&&Health->IsDead())||Pawn->IsTraversing()
            ||((R.Side==1||!R.DualExecutor)&&Pawn->IsCastBlockingLeftHandAction()))
        {FinishPistolReload(R);Changed=true;continue;}
        const float Time=float(GetWorld()->GetTimeSeconds()-R.Started);
        if(!R.Cleared&&Time+1.e-5f>=R.EjectAt)
        {
            if(R.Loader){Gun->Magazine=0;Gun->VirtualMagazineAmmo=0;}
            PistolAmmo::SetCases(*Gun,Gun->Magazine);
            WeaponReloadStages::SetNeedsCycle(*Gun,1);R.Cleared=true;Changed=true;
        }
        while(!R.CycleOnly&&R.Committed<R.Count)
        {
            const int32 SeatIndex=R.Revolver&&!R.Loader?R.Committed:0;
            if(!R.Seats.IsValidIndex(SeatIndex)||Time+1.e-5f<R.Seats[SeatIndex])break;
            const auto Before=ShadowModel->Current.AmmoPouch;
            auto& P=ShadowModel->Current;
            const int32 Want=R.Revolver&&!R.Loader?1:R.Count;
            const bool SwitchNow=R.Switching&&R.Committed==0;
            const bool Infinite=!R.Switching&&Pawn->HasInfiniteReserveAmmoFor(R.Ammo);
            const int32 Room=R.Capacity-(SwitchNow?0:Gun->Magazine);
            const int32 Taken=FMath::Min(Want,FMath::Min(Room,Infinite?R.Capacity:int32(FMath::Min<int64>(R.Capacity,P.AmmoPouch.FindRef(R.Ammo)))));
            if(Taken<=0){FinishPistolReload(R,true);Changed=true;break;}
            if(SwitchNow)
            {
                const FString OldAmmo=ShadowModel->AmmoDefinitionFor(*Gun);
                const int32 Refund=FMath::Max(0,Gun->Magazine-Gun->VirtualMagazineAmmo);
                if(P.AmmoPouch.FindRef(OldAmmo)>ColdSteelAmmo::MaxCount-Refund){FinishPistolReload(R,true);Changed=true;break;}
                P.AmmoPouch.FindOrAdd(OldAmmo)+=Refund;Gun->Magazine=Gun->VirtualMagazineAmmo=0;Gun->LoadedAmmoType=R.Ammo;
                if(R.Revolver)PistolAmmo::SetCases(*Gun,0);
            }
            if(!Infinite)P.AmmoPouch.FindOrAdd(R.Ammo)-=Taken;
            Gun->Magazine+=Taken;if(Infinite)Gun->VirtualMagazineAmmo+=Taken;
            if(R.Revolver)PistolAmmo::SetCases(*Gun,FMath::Max(Gun->Magazine,PistolAmmo::Cases(*Gun)));
            WeaponReloadStages::SetNeedsCycle(*Gun,R.Revolver||R.Empty?1:0);
            R.Committed+=Taken;R.Cleared=true;Changed=true;
            RecordPistolPouchChange(Before);
            if(!R.Revolver||R.Loader){R.Count=R.Committed;break;}
        }
        if(!R.Active)continue;
        if((R.CycleOnly||R.Committed>0)&&!R.Closed&&Time+1.e-5f>=R.ReadyAt)
        {WeaponReloadStages::SetNeedsCycle(*Gun,0);R.Closed=true;Changed=true;}
        if(Time+1.e-5f>=R.Duration){FinishPistolReload(R);Changed=true;}
    }
    if(Changed){RefreshPistolAmmoCounters(Pawn,ShadowModel);SendPistolAmmo();}
}

void AColdSteelPlayerState::FinishPistolReload(FPistolServerReload& R,bool Rejected)
{
    const bool Completed=R.Active&&!Rejected&&!R.CycleOnly&&R.Committed==R.Count;
    R.Active=false;R.Rejected=Rejected;
    if(Completed)
    {
        auto P=ShadowModel->Snapshot();
        ColdSteelSkills::AddExperience(P,ShadowModel->DexterousHandsSkill,ShadowModel->DexterousHandsSkill.ReloadExperience);
        ShadowModel->StageTraining(MoveTemp(P));
    }
    bServerDirty=true;ServerSaveTimer=20.f;
}

bool AColdSteelPlayerState::ConsumePistolAmmo(const FColdSteelItem& Item,int32 Rounds,FString& Reason)
{
    if(!ShadowModel){Reason=TEXT("no pistol authority");return false;}
    auto* Gun=ShadowModel->Current.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;});
    const auto* R=PistolReloads.Find(Item.InstanceId);
    if(!Gun||Rounds<=0||Gun->Magazine<Rounds){Reason=TEXT("magazine empty");return false;}
    if((R&&R->Active)||WeaponReloadStages::NeedsCycle(*Gun)){Reason=TEXT("reloading");return false;}
    Gun->Magazine-=Rounds;Gun->VirtualMagazineAmmo=FMath::Max(0,Gun->VirtualMagazineAmmo-Rounds);
    auto& Ledger=ServerGunLedgers.FindOrAdd(Item.InstanceId);Ledger.Magazine=Gun->Magazine;Ledger.ReloadReadyAt=0.;
    RefreshPistolAmmoCounters(Cast<AFPSGAMECharacter>(GetPawn()),ShadowModel);
    bServerDirty=true;ServerSaveTimer=20.f;return true;
}

void AColdSteelPlayerState::StopPistolAuthority()
{
    for(auto& Pair:PistolReloads)Pair.Value.Active=false;
    PistolReloads.Reset();PistolProcessedShot=0;
}

void AColdSteelPlayerState::PistolCowboyReload()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());if(!HasAuthority()||!ShadowModel||!Pawn||!Pawn->IsSliding())return;
    const int32 Main=ShadowModel->Current.ActiveWeaponSlot;
    bool Changed=false;const auto Before=ShadowModel->Current.AmmoPouch;
    for(const int32 Cell:{Main,Main==6?8:11})
    {
        const auto* Gun=ShadowModel->Equipped(Cell);if(!Gun||!ColdSteelInventory::IsDualPistol(*Gun))continue;
        const FString Id=Gun->InstanceId;
        const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();if(!G)continue;
        RefreshPistolAmmoCounters(Pawn,ShadowModel);
        if(ShadowModel->ReloadCowboyPistol(Id,G->CalculateItem(*Gun,G->Installed(*Gun)).Capacity)<=0)continue;
        if(auto* R=PistolReloads.Find(Id))R->Active=false;
        Changed=true;
    }
    if(Changed){RecordPistolPouchChange(Before);RefreshPistolAmmoCounters(Pawn,ShadowModel);SendPistolAmmo(true);}
}
