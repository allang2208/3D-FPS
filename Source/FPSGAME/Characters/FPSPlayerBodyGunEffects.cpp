#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/PKMLowpolyWeaponAssets.h"
#include "../Weapons/LMG201WeaponAssets.h"
#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundConcurrency.h"
#include "Sound/SoundBase.h"

bool UFPSPlayerBodyComponent::CurrentGun(uint8 Hand,FFPSBodyWeapon& W) const
{
    if(!Character.IsValid()||Hand>1)return false;
    W.AttachHand=Hand;
    if(Character->DualPistols&&Character->DualPistols->IsActive())
    {
        if(Hand==0&&Character->DualPistols->IsOffhandOnly())return false;
        W.Source=Character->DualPistols->Hand(Hand).Mesh;
    }
    else if(Hand==0&&Character->HasInventoryWeapon())W.Source=Character->AKMViewmodel;
    else return false;
    const bool Dual=Character->DualPistols&&Character->DualPistols->IsActive();
    const FString& Instance=Dual?Character->DualPistols->Hand(Hand).Item.InstanceId:Character->ActiveInventoryWeapon;
    // Reuse the prepared equipment manifest during sustained automatic fire.
    if(!bEquipmentDirty)for(const auto& Cached:LocalWeapons)
        if(Cached.AttachHand==Hand&&Cached.Source==W.Source&&Cached.GunInstance==Instance)
        {
            W.GunInstance=Cached.GunInstance;W.GunDefinition=Cached.GunDefinition;
            W.bGunSuppressed=Dual?Character->DualPistols->Hand(Hand).Suppressed:Character->IsMuzzleSuppressed();
            W.GunSounds=Cached.GunSounds;W.GunCartridges=Cached.GunCartridges;return true;
        }
    DescribeGun(W);
    return !W.GunInstance.IsEmpty();
}

void UFPSPlayerBodyComponent::DescribeGun(FFPSBodyWeapon& W) const
{
    const auto* C=Character.Get();auto* Source=W.Source.Get();
    if(!C||!Source||W.AttachHand>1)return;
    const FDualPistolHand* H=nullptr;
    if(C->DualPistols&&C->DualPistols->IsActive()
        &&(W.AttachHand!=0||!C->DualPistols->IsOffhandOnly()))
    {
        const auto& Candidate=C->DualPistols->Hand(W.AttachHand);
        if(Candidate.Mesh==Source)H=&Candidate;
    }
    if(!H&&(W.AttachHand!=0||!C->HasInventoryWeapon()||Source!=C->AKMViewmodel))return;
    W.GunInstance=H?H->Item.InstanceId:C->ActiveInventoryWeapon;
    W.GunDefinition=FName(*(H?H->Item.Definition:C->ActiveInventoryWeaponDefinition));
    W.bGunPistol=H||C->IsPistolWeapon();W.bGunRevolver=H?H->Revolver:C->bUseDanWesson715;
    W.bGunSuppressed=H?H->Suppressed:C->IsMuzzleSuppressed();
    W.GunSounds.Reset();W.GunCartridges.Reset();
    const auto AddSound=[&W](USoundBase* S){if(S)W.GunSounds.AddUnique(TSoftObjectPtr<USoundBase>(S));};
    FTransform Muzzle;
    if(H)
    {
        W.GunFireSound=H->Sounds.FindRef(TEXT("Fire")).Get();
        W.GunSuppressedSound=H->Sounds.FindRef(TEXT("Suppressed")).Get();
        for(const auto& Pair:H->Sounds)AddSound(Pair.Value);
        if(H->FX)if(auto* Exit=H->FX->GetIndependentMuzzle())Muzzle=Exit->GetComponentTransform();
        if(H->FX&&H->FX->bUseCharacterMuzzle)Muzzle=C->GetNativeMuzzleTransform();
        else if(!H->FX||!H->FX->GetIndependentMuzzle())
            Muzzle=FTransform((Source->GetSocketLocation(TEXT("WPN_FrontSight"))-Source->GetSocketLocation(TEXT("WPN_RearSight"))).Rotation(),Source->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle")));
        if(H->FX)if(auto* Exit=H->FX->GetIndependentMuzzle())
            for(int32 I=0;I<W.SourceParts.Num();++I)if(W.SourceParts[I].Get()==Exit->GetAttachParent())
            {W.MuzzlePart=I;W.MuzzleTip=Exit->GetRelativeLocation();W.MuzzleAxis=Exit->GetRelativeRotation().Vector();break;}
        for(const auto& Mesh:H->ReloadCaseMeshes)if(Mesh)W.GunCartridges.AddUnique(TSoftObjectPtr<UStaticMesh>(Mesh.Get()));
        for(const auto& Mesh:H->ReloadLiveMeshes)if(Mesh)W.GunCartridges.AddUnique(TSoftObjectPtr<UStaticMesh>(Mesh.Get()));
    }
    else
    {
        W.GunFireSound=C->FireSound.Get();W.GunSuppressedSound=C->SuppressedFireSound.Get();
        Muzzle=C->GetNativeMuzzleTransform();
        for(auto* S:{C->FireSound.Get(),C->SuppressedFireSound.Get(),C->BoltReleaseSound.Get(),C->EquipSound.Get(),
            C->MagOutSound.Get(),C->MagInsertSound.Get(),C->MagSeatSound.Get(),C->ChargePullSound.Get(),C->ChargeReleaseSound.Get(),C->DryClickSound.Get()})AddSound(S);
        const auto AddBank=[&AddSound](const auto& Bank){for(auto S:Bank)AddSound(S);};
        AddBank(C->RifleFireVariants);AddBank(C->RifleSuppressedVariants);AddBank(C->RevolverSpeedloaderSounds);AddBank(C->Super90LoaderSounds);
        // These contact cuts are normally loaded when reloading starts. Publish their
        // trusted paths at equip time so observers can prepare them asynchronously.
        if(W.GunDefinition==FName(PKMLowpolyWeaponAssets::Definition)||W.GunDefinition==FName(LMG201WeaponAssets::Definition))
            for(const TCHAR* Cue:{TEXT("CoverOpen"),TEXT("BeltLift"),TEXT("BoxOut"),TEXT("BoxInsert"),TEXT("BeltSeat"),TEXT("CoverClose"),TEXT("ChargePullMove"),TEXT("ChargeRearStop"),TEXT("ChargePushMove"),TEXT("ChargeFrontStop")})
            {
                const FString Path=FString(Cue).StartsWith(TEXT("Charge"))?PKMLowpolyWeaponAssets::ChargeSoundPath(Cue):PKMLowpolyWeaponAssets::ReloadSoundPath(Cue);
                W.GunSounds.AddUnique(TSoftObjectPtr<USoundBase>(FSoftObjectPath(Path)));
            }
    }
    W.GunMuzzleInRoot=Muzzle.GetRelativeTransform(Source->GetSocketTransform(TEXT("WPN_root")));
    W.GunSounds.Sort([](const auto& A,const auto& B){return A.ToSoftObjectPath().ToString()<B.ToSoftObjectPath().ToString();});
}

void UFPSPlayerBodyComponent::ReportGunShot(uint8 Hand,USoundBase* Sound,float Volume,float Pitch,bool Aiming)
{
    FFPSGunEvent E;E.Hand=Hand;E.Sound=Sound;E.Volume=Volume;E.Pitch=Pitch;E.bAiming=Aiming;SendGunEvent(E);
}
void UFPSPlayerBodyComponent::ReportGunMechanical(uint8 Hand,USoundBase* Sound,float Volume,float StartTime)
{
    if(!Sound)return;
    FFPSGunEvent E;E.Kind=EFPSGunEvent::Mechanical;E.Hand=Hand;E.Sound=Sound;E.Volume=Volume;E.StartTime=StartTime;SendGunEvent(E);
}
void UFPSPlayerBodyComponent::ReportGunMechanicalStop(uint8 Hand)
{
    FFPSGunEvent E;E.Kind=EFPSGunEvent::StopMechanical;E.Hand=Hand;SendGunEvent(E);
}
void UFPSPlayerBodyComponent::ReportGunCartridge(uint8 Hand,UStaticMesh* Mesh,const FTransform& Frame,const FVector& Velocity,float Age)
{
    FFPSBodyWeapon W;if(!CurrentGun(Hand,W))return;
    const auto Root=W.Source->GetSocketTransform(TEXT("WPN_root"));
    FFPSGunEvent E;E.Kind=EFPSGunEvent::Cartridge;E.Hand=Hand;E.Cartridge=Mesh;
    E.Release=Frame.GetRelativeTransform(Root);E.ReleaseVelocity=Root.GetRotation().UnrotateVector(Velocity-GetOwner()->GetVelocity());E.StartTime=Age;SendGunEvent(E);
}
void UFPSPlayerBodyComponent::SendGunEvent(FFPSGunEvent E)
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||GetNetMode()==NM_Standalone)return;
    FFPSBodyWeapon W;if(!CurrentGun(E.Hand,W))return;
    // Super90 has its own accepted-shot multicast and predicted owner effects.
    if(E.Kind==EFPSGunEvent::Shot&&W.GunDefinition==TEXT("ue_super90"))return;
    E.Instance=W.GunInstance;E.bSuppressed=W.bGunSuppressed;E.SentAt=ServerClock();E.Sequence=++SentGunSequence;
    if(E.Kind==EFPSGunEvent::Shot)ServerGunShot(E);else ServerGunMechanical(E);
}
bool UFPSPlayerBodyComponent::AcceptGunEvent(FFPSGunEvent& E)
{
    FFPSBodyWeapon W;if(!CurrentGun(E.Hand,W)||W.GunInstance!=E.Instance)return false;
    if(!FMath::IsFinite(E.SentAt)||!FMath::IsFinite(E.Volume)||!FMath::IsFinite(E.Pitch)||!FMath::IsFinite(E.StartTime))return false;
    auto& Received=E.Kind==EFPSGunEvent::Shot?ReceivedGunSequence[E.Hand]:ReceivedGunMechanicalSequence[E.Hand];
    if(int32(E.Sequence-Received)<=0)return false;
    if(E.Kind==EFPSGunEvent::StopMechanical){Received=E.Sequence;return true;}
    const float Age=ServerClock()-E.SentAt;
    if(Age>1.f||Age<-.25f)return false;
    E.SentAt=FMath::Min(E.SentAt,ServerClock());E.Volume=FMath::Clamp(E.Volume,0.f,4.f);E.Pitch=FMath::Clamp(E.Pitch,.5f,2.f);E.StartTime=FMath::Clamp(E.StartTime,0.f,5.f);E.bSuppressed=W.bGunSuppressed;
    if(E.Kind==EFPSGunEvent::Cartridge)
    {
        const bool Valid=W.GunCartridges.Contains(E.Cartridge)&&!E.Release.ContainsNaN()&&!E.ReleaseVelocity.ContainsNaN()
            &&E.Release.GetRotation().IsNormalized()&&E.Release.GetTranslation().Size()<10.f&&E.Release.GetScale3D().GetAbsMax()<=1.f&&E.ReleaseVelocity.Size()<250.f;
        if(Valid)Received=E.Sequence;return Valid;
    }
    if(E.Kind!=EFPSGunEvent::Shot&&E.Kind!=EFPSGunEvent::Mechanical)return false;
    if(!E.Sound.IsNull()&&!W.GunSounds.Contains(E.Sound))return false;
    if(E.Kind==EFPSGunEvent::Shot&&W.GunDefinition==TEXT("ue_super90"))return false;
    Received=E.Sequence;return true;
}
void UFPSPlayerBodyComponent::RelayGunEvent(const FFPSGunEvent& Event)
{
    if(Event.Hand>1||!FMath::IsFinite(Event.SentAt))return;
    if(Event.Kind==EFPSGunEvent::StopMechanical)
        PendingAuthorityGunEvents.RemoveAll([&](const FFPSGunEvent& Old){return Old.Hand==Event.Hand&&Old.Instance==Event.Instance&&Old.Kind==EFPSGunEvent::Mechanical;});
    FFPSBodyWeapon W;
    // The owning pawn and PlayerState equipment publication use different actor
    // channels. A G18 can fire during equip, before the new loadout arrives here.
    if(!CurrentGun(Event.Hand,W)||W.GunInstance!=Event.Instance)
    {
        if(FMath::Abs(ServerClock()-Event.SentAt)>1.f)return;
        if(PendingAuthorityGunEvents.Num()>=64)PendingAuthorityGunEvents.RemoveAt(0);
        PendingAuthorityGunEvents.Add(Event);return;
    }
    auto E=Event;if(!AcceptGunEvent(E))return;
    if(E.Kind==EFPSGunEvent::Shot)MulticastGunShot(E);else MulticastGunMechanical(E);
}
void UFPSPlayerBodyComponent::FlushAuthorityGunEvents()
{
    for(int32 I=0;I<PendingAuthorityGunEvents.Num();)
    {
        auto E=PendingAuthorityGunEvents[I];
        if(ServerClock()-E.SentAt>1.f){PendingAuthorityGunEvents.RemoveAt(I);continue;}
        FFPSBodyWeapon W;
        if(!CurrentGun(E.Hand,W)||W.GunInstance!=E.Instance){++I;continue;}
        PendingAuthorityGunEvents.RemoveAt(I);
        if(AcceptGunEvent(E)){if(E.Kind==EFPSGunEvent::Shot)MulticastGunShot(E);else MulticastGunMechanical(E);}
    }
}
void UFPSPlayerBodyComponent::ServerGunShot_Implementation(const FFPSGunEvent& E)
{if(E.Kind==EFPSGunEvent::Shot)RelayGunEvent(E);}
void UFPSPlayerBodyComponent::ServerGunMechanical_Implementation(const FFPSGunEvent& E)
{if(E.Kind!=EFPSGunEvent::Shot)RelayGunEvent(E);}
void UFPSPlayerBodyComponent::MulticastGunShot_Implementation(const FFPSGunEvent& E){QueueGunEvent(E);}
void UFPSPlayerBodyComponent::MulticastGunMechanical_Implementation(const FFPSGunEvent& E){QueueGunEvent(E);}
void UFPSPlayerBodyComponent::QueueGunEvent(const FFPSGunEvent& E)
{
    if(!Character.IsValid()||Character->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer||E.Hand>1)return;
    if(E.Kind==EFPSGunEvent::StopMechanical)
    {
        PendingGunEvents.RemoveAll([&](const FFPSGunEvent& Old){return Old.Hand==E.Hand&&Old.Instance==E.Instance&&Old.Kind==EFPSGunEvent::Mechanical;});
        if(RemoteGunHands[E.Hand].Instance==E.Instance)StopRemoteGunMechanical(E.Hand);
        return;
    }
    // A short bounded queue covers equipment replication/async loading arriving after an RPC.
    if(PendingGunEvents.Num()>=64)PendingGunEvents.RemoveAt(0);
    PendingGunEvents.Add(E);
}
void UFPSPlayerBodyComponent::PresentGunEvents()
{
    const float Now=ServerClock();
    for(int32 I=0;I<PendingGunEvents.Num();)
    {
        const auto& E=PendingGunEvents[I];const float Age=FMath::Max(0.f,Now-E.SentAt);
        if(Age>(E.Kind==EFPSGunEvent::Shot?.6f:1.f)||PresentGunEvent(E,Age))PendingGunEvents.RemoveAt(I);
        else ++I;
    }
}
void UFPSPlayerBodyComponent::StopRemoteGunMechanical(uint8 Hand)
{
    for(const auto& Voice:RemoteGunHands[Hand].MechanicalVoices)if(IsValid(Voice))Voice->Stop();
    RemoteGunHands[Hand].MechanicalVoices.Reset();
}
void UFPSPlayerBodyComponent::ClearGunPresentation()
{
    for(uint8 H=0;H<2;++H)
    {
        StopRemoteGunMechanical(H);
        if(RemoteGunHands[H].FX)RemoteGunHands[H].FX->DestroyComponent();
        RemoteGunHands[H].FX=nullptr;RemoteGunHands[H].Instance.Reset();RemoteGunLoads[H].Reset();
    }
    RemoteGunFX=nullptr;
}
void UFPSPlayerBodyComponent::BuildGunPresentation(const FFPSBodyWeapon& W,UFPSBodyWeaponMeshComponent* Mesh)
{
    if(!Character.IsValid()||Character->IsLocallyControlled()||W.GunInstance.IsEmpty()||W.AttachHand>1)return;
    auto& Hand=RemoteGunHands[W.AttachHand];Hand.Instance=W.GunInstance;
    auto* FX=NewObject<UFPSWeaponFXComponent>(GetOwner(),NAME_None,RF_Transient);Hand.FX=FX;
    GetOwner()->AddInstanceComponent(FX);FX->RegisterComponent();
    FX->SetWorldGunSuppressed(W.bGunSuppressed);FX->SetWorldGunType(W.GunDefinition,W.bGunPistol,W.bGunRevolver,W.GunMuzzleInRoot);
    for(const auto& Binding:MotionBindings)if(Binding.Mesh.Get()==Mesh&&Binding.Parts.IsValidIndex(W.MuzzlePart))
        FX->SetWorldMuzzle(Binding.Parts[W.MuzzlePart].Get(),W.MuzzleTip,W.MuzzleAxis);
    FX->Initialize(Mesh,Character->FirstPersonCamera);
    if(W.GunDefinition==TEXT("ue_super90"))RemoteGunFX=FX;
    TArray<FSoftObjectPath> Assets;
    for(const auto& S:W.GunSounds)Assets.AddUnique(S.ToSoftObjectPath());
    for(const auto& M:W.GunCartridges)Assets.AddUnique(M.ToSoftObjectPath());
    if(!Assets.IsEmpty())RemoteGunLoads[W.AttachHand]=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets);
    if(!Hand.FireConcurrency)
    {
        Hand.FireConcurrency=NewObject<USoundConcurrency>(this);
        Hand.FireConcurrency->Concurrency.MaxCount=4;Hand.FireConcurrency->Concurrency.bLimitToOwner=true;
        Hand.FireConcurrency->Concurrency.ResolutionRule=EMaxConcurrentResolutionRule::StopOldest;
        Hand.FireConcurrency->Concurrency.VoiceStealReleaseTime=.02f;
    }
}
bool UFPSPlayerBodyComponent::PresentGunEvent(const FFPSGunEvent& E,float Age)
{
    auto& H=RemoteGunHands[E.Hand];if(H.Instance!=E.Instance||!H.FX)return false;
    for(const auto& B:MotionBindings)
    {
        if(B.Definition.AttachHand!=E.Hand||B.Definition.GunInstance!=E.Instance)continue;
        auto* Mesh=B.Mesh.Get();if(!Mesh)return false;
        // A fresh equipment property can precede its visible body state. Keep
        // the event briefly instead of consuming that first shot while hidden.
        if(!Mesh->IsVisible()||Mesh->bHiddenInGame||IsWorldWeaponStowed(Mesh))return false;
        if(E.Kind==EFPSGunEvent::Cartridge)
        {
            if(!B.Definition.GunCartridges.Contains(E.Cartridge))return true;
            auto* Geometry=E.Cartridge.Get();if(!Geometry)return false;
            const auto Root=Mesh->GetSocketTransform(TEXT("WPN_root"));
            H.FX->OnReloadCartridge(Geometry,E.Release*Root,Root.GetRotation().RotateVector(E.ReleaseVelocity)+GetOwner()->GetVelocity(),E.StartTime+Age);return true;
        }
        const bool Shot=E.Kind==EFPSGunEvent::Shot;
        auto SoundRef=E.Sound;
        if(Shot&&B.Definition.GunDefinition==TEXT("ue_super90"))
            SoundRef=E.bSuppressed&&!B.Definition.GunSuppressedSound.IsNull()?B.Definition.GunSuppressedSound:B.Definition.GunFireSound;
        if(!SoundRef.IsNull()&&!B.Definition.GunSounds.Contains(SoundRef))return true;
        auto* Sound=SoundRef.Get();if(!SoundRef.IsNull()&&!Sound)return false;
        if(Shot){H.FX->SetWorldGunSuppressed(E.bSuppressed);H.FX->OnShot(E.bAiming);}
        if(!Sound)return true;
        // Preserve short contact attacks across network latency. Source-clock
        // lateness/pre-roll is already supplied by the native cue executor.
        const float Offset=Shot?0.f:E.StartTime;
        if(Offset>=Sound->GetDuration())return true;
        auto* Audio=NewObject<UAudioComponent>(GetOwner());Audio->bAutoActivate=false;Audio->bAutoDestroy=true;
        Audio->bIsUISound=false;Audio->bAllowSpatialization=true;Audio->bStopWhenOwnerDestroyed=true;
        Audio->SetSound(Sound);Audio->SetVolumeMultiplier(E.Volume);Audio->SetPitchMultiplier(E.Pitch);
        FSoundAttenuationSettings Settings;Settings.bAttenuate=true;Settings.bSpatialize=true;
        Settings.AttenuationShapeExtents=FVector(Shot?150.f:80.f);Settings.FalloffDistance=Shot?(E.bSuppressed?3000.f:12000.f):1600.f;
        if(Shot){Audio->ConcurrencySet.Add(H.FireConcurrency);Audio->RegisterComponent();Audio->SetWorldLocation(H.FX->ShotOrigin());}
        else
        {
            H.MechanicalVoices.RemoveAll([](const auto& V){return !IsValid(V)||!V->IsPlaying();});
            if(H.MechanicalVoices.Num()>=12){H.MechanicalVoices[0]->Stop();H.MechanicalVoices.RemoveAt(0);}
            Audio->SetupAttachment(Mesh,TEXT("WPN_root"));Audio->RegisterComponent();H.MechanicalVoices.Add(Audio);
        }
        Audio->AdjustAttenuation(Settings);Audio->Play(Offset);return true;
    }
    return false;
}
void UFPSPlayerBodyComponent::PresentSuper90Shot(const FString& Instance,float FiredAt,bool Aiming,bool Suppressed)
{
    // The accepted-shot RPC carries identity even if its equipment property is
    // still in flight. The same bounded queue resolves that ordering below.
    FFPSGunEvent E;E.Instance=Instance;E.SentAt=FiredAt;E.bAiming=Aiming;E.bSuppressed=Suppressed;
    E.Volume=Suppressed?.65f:1.f;QueueGunEvent(E);
}
