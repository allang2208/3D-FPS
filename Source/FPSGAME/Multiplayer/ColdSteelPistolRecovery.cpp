#include "ColdSteelPlayerState.h"
#include "PistolAmmoHelpers.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void AColdSteelPlayerState::EnsurePistolAmmoIds()
{
    if(!PistolAmmoIds.IsEmpty()||!ShadowModel)return;
    TSet<FString> Groups;
    for(const TCHAR* Id:{TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")})
        Groups.Add(ShadowModel->AmmoGroupFor(ShadowModel->CreateItem(Id)));
    for(const auto& Type:ShadowModel->AmmoCatalog())if(Groups.Contains(Type.Group))PistolAmmoIds.Add(Type.Id);
    PistolPouchHistory.FindOrAdd(0);
}

void AColdSteelPlayerState::RequestPistolShot(uint32 Sequence,const FString& Instance,int32 ActiveSlot,int32 Rounds)
{
    PistolPredictedShots.Add({Sequence,Instance,Rounds});
    ServerRememberPistolShot(Sequence,Instance,ActiveSlot,Rounds,GetPawn());
}

bool AColdSteelPlayerState::RequestPistolReload(const FString& Instance,const FString& Ammo)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!GetPawn()||!IsPistolServerReady(Instance)||IsPistolReloadPending(Instance))return false;
    const uint32 Serial=++PistolControlSequence;PistolPendingReloads.Add(Instance,Serial);
    ServerPistolReload(Serial,Instance,Ammo,Model->Snapshot().ActiveWeaponSlot,GetPawn());return true;
}

void AColdSteelPlayerState::CancelPistolReload(const FString& Instance)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire")))UE_LOG(LogTemp,Display,TEXT("PISTOL_AMMO_CANCEL_REQUEST id=%s pending=%u applying=%d sent=%d"),*Instance,PistolPendingReloads.FindRef(Instance),bApplyingPistolReceipt,PistolCancelPending.Contains(Instance));
    if(bApplyingPistolReceipt||PistolCancelPending.Contains(Instance))return;
    const auto* Serial=PistolPendingReloads.Find(Instance);if(!Serial)return;
    const uint32 ReloadSerial=*Serial;PistolCancelPending.Add(Instance);
    ServerPistolCancel(++PistolControlSequence,Instance,ReloadSerial,GetPawn());
}

void AColdSteelPlayerState::RefreshPistolAmmoCounters(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,bool AmmoChanged)
{
    if(!Pawn||!Model)return;
    if(AmmoChanged){Pawn->ApplyColdSteelProfile(Model);return;}
    if(Pawn->DualPistols&&Pawn->DualPistols->IsActive())Pawn->DualPistols->RefreshNetworkAmmo(Model);
    else if(const auto* Gun=Model->FindItem(Pawn->ActiveInventoryWeapon);Gun&&ColdSteelInventory::IsDualPistol(*Gun))
    {Pawn->MagazineAmmo=Gun->Magazine;Pawn->RevolverCaseCount=PistolAmmo::Cases(*Gun);Pawn->ReserveAmmo=Model->AmmoCountFor(*Gun);}
}

void AColdSteelPlayerState::RecordPistolPouchChange(const TMap<FString,int64>& Before)
{
    EnsurePistolAmmoIds();
    for(const auto& Id:PistolAmmoIds)PistolPouchDelta.FindOrAdd(Id)+=ShadowModel->Current.AmmoPouch.FindRef(Id)-Before.FindRef(Id);
    PistolPouchHistory.Add(++PistolAmmoRevision,PistolPouchDelta);
    if(PistolAmmoRevision>512)PistolPouchHistory.Remove(PistolAmmoRevision-512);
    bServerDirty=true;ServerSaveTimer=20.f;
}

bool AColdSteelPlayerState::RebasePistolUpload(FColdSteelProfile& Incoming,const FColdSteelProfile& Previous,bool KeepServerPouch) const
{
    const TMap<FString,int64> Zero;
    const auto* Base=IncomingPistolAmmoRevision==0?&Zero:PistolPouchHistory.Find(IncomingPistolAmmoRevision);
    if(!KeepServerPouch&&!Base)return false;
    for(const auto& Id:PistolAmmoIds)
        Incoming.AmmoPouch.FindOrAdd(Id)=KeepServerPouch?Previous.AmmoPouch.FindRef(Id):
            FMath::Clamp<int64>(Incoming.AmmoPouch.FindRef(Id)+PistolPouchDelta.FindRef(Id)-Base->FindRef(Id),0,ColdSteelAmmo::MaxCount);
    const auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    TMap<FString,int64> Refunds;bool Resized=false;
    for(auto& Gun:Incoming.Items)if(ColdSteelInventory::IsDualPistol(Gun))
        if(const auto* Old=Previous.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Gun.InstanceId;}))
        {
            PistolAmmo::CopyMagazine(Gun,*Old);
            if(!G)continue;
            const int32 Cap=G->CalculateItem(Gun,G->Installed(Gun)).Capacity;
            const int32 OldCap=G->CalculateItem(*Old,G->Installed(*Old)).Capacity;
            if(Cap==OldCap&&Gun.Magazine<=Cap)continue;
            Resized=true;const int32 Extra=FMath::Max(0,Gun.Magazine-Cap),Virtual=FMath::Min(Extra,Gun.VirtualMagazineAmmo);
            Gun.Magazine-=Extra;Gun.VirtualMagazineAmmo-=Virtual;
            if(PistolAmmo::Revolver(Gun))PistolAmmo::SetCases(Gun,FMath::Clamp(PistolAmmo::Cases(Gun),Gun.Magazine,Cap));
            if(Cap<OldCap||Extra>0)Refunds.FindOrAdd(ShadowModel->AmmoDefinitionFor(Gun))+=Extra-Virtual;
        }
    for(const auto& Pair:Refunds)
    {
        const int64 Count=Previous.AmmoPouch.FindRef(Pair.Key)+Pair.Value;
        if(Count>ColdSteelAmmo::MaxCount)return false;
        Incoming.AmmoPouch.Add(Pair.Key,Count);
    }
    if(Resized)Incoming.CampfireInventoryRevision=Previous.CampfireInventoryRevision+1;
    // A chunked snapshot begun before a newer reload/cancel cannot undo that
    // intent's held group. The next fresh snapshot carries the current serial.
    if(static_cast<int32>(IncomingPistolIntent-PistolProcessedControl)<0)
        Incoming.ActiveWeaponSlot=Previous.ActiveWeaponSlot;
    return true;
}

void AColdSteelPlayerState::SendPistolAmmo(bool Cowboy)
{
    if(!HasAuthority()||!ShadowModel)return;
    EnsurePistolAmmoIds();
    FPistolNetAmmoState State;State.Pawn=GetPawn();State.Revision=++PistolReceiptRevision;
    State.AmmoRevision=PistolAmmoRevision;State.AcknowledgedShot=PistolProcessedShot;
    State.InventoryRevision=ShadowModel->InventoryRevision();State.Cowboy=Cowboy;
    for(const auto& Id:PistolAmmoIds)
    {auto& Row=State.Pouch.AddDefaulted_GetRef();Row.Ammo=Id;Row.Count=ShadowModel->PouchCount(Id);Row.Delta=PistolPouchDelta.FindRef(Id);}
    for(const auto& I:ShadowModel->Items())if(ColdSteelInventory::IsDualPistol(I)&&
        (I.Place==1||ServerGunLedgers.Contains(I.InstanceId)||PistolReloads.Contains(I.InstanceId)))
    {
        auto& M=State.Magazines.AddDefaulted_GetRef();M.Instance=I.InstanceId;M.Ammo=ShadowModel->AmmoDefinitionFor(I);
        M.Rounds=I.Magazine;M.VirtualRounds=I.VirtualMagazineAmmo;M.Cases=PistolAmmo::Cases(I);
        M.NeedsCycle=WeaponReloadStages::NeedsCycle(I);M.EmptyCycle=WeaponReloadStages::UsesEmptyCycle(I);
        if(auto* L=ServerGunLedgers.Find(I.InstanceId))L->Magazine=I.Magazine;
    }
    for(const auto& Pair:PistolReloads)
    {const auto& R=Pair.Value;auto& Row=State.Reloads.AddDefaulted_GetRef();Row.Instance=R.Instance;Row.Serial=R.Serial;Row.Active=R.Active;Row.Rejected=R.Rejected;}
    ClientPistolAmmo(State);
}

void AColdSteelPlayerState::TickPistolRecovery()
{
    if(GetNetMode()!=NM_Client)return;
    if(PistolClientPawn.Get()!=GetPawn())
    {PistolClientPawn=GetPawn();PistolPredictedShots.Reset();PistolPendingReloads.Reset();PistolCancelPending.Reset();PistolServerWeapons.Reset();}
    if(!bPendingPistolState)return;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!GetPawn()||PendingPistolState.Pawn!=GetPawn()||Model->RuntimePawn()!=GetPawn()||PendingPistolState.InventoryRevision>Model->InventoryRevision())return;
    const auto Receipt=PendingPistolState;bPendingPistolState=false;ClientPistolAmmo_Implementation(Receipt);
}

void AColdSteelPlayerState::ClientPistolAmmo_Implementation(const FPistolNetAmmoState& Receipt)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||static_cast<int32>(Receipt.Revision-PistolAppliedReceipt)<=0)return;
    if(!Pawn||Receipt.Pawn!=Pawn||!Pawn->IsLocallyControlled()||Model->RuntimePawn()!=Pawn||Receipt.InventoryRevision>Model->InventoryRevision())
    {if(!bPendingPistolState||static_cast<int32>(Receipt.Revision-PendingPistolState.Revision)>0){PendingPistolState=Receipt;bPendingPistolState=true;}return;}
    if(PistolClientPawn.Get()!=Pawn)
    {PistolClientPawn=Pawn;PistolPredictedShots.Reset();PistolPendingReloads.Reset();PistolCancelPending.Reset();PistolServerWeapons.Reset();}
    TGuardValue<bool> Applying(bApplyingPistolReceipt,true);
    bPendingPistolState=false;Model->SyncRuntime();auto& State=Model->Current;
    bool PouchChanged=false,AmmoChanged=false;
    for(const auto& Row:Receipt.Pouch)
    {
        auto& Count=State.AmmoPouch.FindOrAdd(Row.Ammo);const int64 Previous=Count;
        // A newer inventory receipt already includes its reload debits. Adopt
        // that revision's absolute baseline once, then apply only later deltas
        // so local reloads on other weapons sharing this ammo remain intact.
        if(Receipt.InventoryRevision==State.CampfireInventoryRevision)
        {
            if(!bPistolAmmoInitialized||PistolAppliedInventoryRevision!=Receipt.InventoryRevision)Count=Row.Count;
            else Count=FMath::Clamp<int64>(Count+Row.Delta-PistolAppliedPouchDelta.FindRef(Row.Ammo),0,ColdSteelAmmo::MaxCount);
        }
        PistolAppliedPouchDelta.Add(Row.Ammo,Row.Delta);PouchChanged|=Previous!=Count;
    }
    bPistolAmmoInitialized=true;PistolAppliedReceipt=Receipt.Revision;PistolAppliedAmmoRevision=Receipt.AmmoRevision;
    PistolAppliedInventoryRevision=Receipt.InventoryRevision;
    PistolPredictedShots.RemoveAll([&](const auto& Shot){return static_cast<int32>(Shot.Sequence-Receipt.AcknowledgedShot)<=0;});
    for(const auto& M:Receipt.Magazines)
    {
        PistolServerWeapons.Add(M.Instance);
        if(auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==M.Instance;}))
        {
            AmmoChanged|=Model->AmmoDefinitionFor(*Gun)!=M.Ammo;
            Gun->Magazine=M.Rounds;Gun->VirtualMagazineAmmo=M.VirtualRounds;Gun->LoadedAmmoType=M.Ammo;
            if(WeaponReloadStages::NeedsCycle(*Gun)!=M.NeedsCycle||(M.NeedsCycle&&WeaponReloadStages::UsesEmptyCycle(*Gun)!=M.EmptyCycle))
                WeaponReloadStages::SetNeedsCycle(*Gun,M.NeedsCycle?(M.EmptyCycle?1:2):0);
            PistolAmmo::SetCases(*Gun,M.Cases);
            for(const auto& Shot:PistolPredictedShots)if(Shot.Instance==M.Instance)
            {Gun->Magazine=FMath::Max(0,Gun->Magazine-Shot.Rounds);Gun->VirtualMagazineAmmo=FMath::Max(0,Gun->VirtualMagazineAmmo-Shot.Rounds);}
        }
    }
    RefreshPistolAmmoCounters(Pawn,Model,AmmoChanged);
    bool Finished=false;
    for(const auto& R:Receipt.Reloads)
    {
        const auto* Pending=PistolPendingReloads.Find(R.Instance);
        if(!Pending||*Pending!=R.Serial||R.Active)continue;
        PistolPendingReloads.Remove(R.Instance);PistolCancelPending.Remove(R.Instance);Finished=true;
        if(Pawn->DualPistols&&Pawn->DualPistols->IsActive())Pawn->DualPistols->FinishNetworkReload(R.Instance);
        else if(Pawn->ActiveInventoryWeapon==R.Instance&&Pawn->IsReloading())Pawn->InterruptReload();
    }
    if(Receipt.Cowboy)
    {
        Pawn->NotifyCowboyReload();
        Finished=true;
    }
    if(PouchChanged||AmmoChanged)Model->NotifyChanged();
    if(Finished)Model->SaveNow();
}

void AColdSteelPlayerState::PreservePistolClientAmmo(FColdSteelProfile& Incoming) const
{
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!bPistolAmmoInitialized)return;
    if(Incoming.CampfireInventoryRevision==Model->Current.CampfireInventoryRevision)
        for(const auto& Pair:PistolAppliedPouchDelta)Incoming.AmmoPouch.Add(Pair.Key,Model->Current.AmmoPouch.FindRef(Pair.Key));
    for(auto& Gun:Incoming.Items)if(ColdSteelInventory::IsDualPistol(Gun))
        if(const auto* Old=Model->FindItem(Gun.InstanceId))PistolAmmo::CopyMagazine(Gun,*Old);
}
