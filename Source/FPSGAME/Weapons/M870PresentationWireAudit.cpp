#include "ShotgunWireAudit.h"
#include "SniperZhimingWire.h"
#include "M870WeaponAssets.h"
#include "Saiga12KWeaponAssets.h"
#include "Saiga12KMagazineAssets.h"
#include "Saiga12KSpecialStockAssets.h"
#include "SVCHWeaponAssets.h"
#include "M24WeaponAssets.h"
#include "M24Attachments.h"
#include "WeaponReloadStages.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "../Multiplayer/ColdSteelPreparedHit.h"
#include "Engine/TargetPoint.h"
#include "GameFramework/GameStateBase.h"
#include "FPSWeaponFXComponent.h"
#include "SniperSkeletonStock.h"
#include "SniperSuppressorAssets.h"
#include "FPSGunplayAnimInstance.h"
#include "TacticalDeviceComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace ShotgunWire
{
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Pass,const TCHAR* Role);
}
namespace M870Wire
{
bool Saiga(){return FParse::Param(FCommandLine::Get(),TEXT("Saiga12K"));}
bool SVCH(){return FParse::Param(FCommandLine::Get(),TEXT("SVCH"));}
bool M24(){return FParse::Param(FCommandLine::Get(),TEXT("M24"));}
bool ExpectsLaser(int32 Phase){return !M24()||Phase==1||Phase==3||Phase==4;}
bool ProfileRifle(){return Saiga()||SVCH()||M24();}
int32 Capacity(int32 P){return M24()?(P==3||P==4?10:5):SVCH()?(P==0||P==5?10:20):(P==0?8:P==5?12:20);}
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("M870PresentationWire"));}
float Pitch(int32 P){return P==0?25.f:P==1?-30.f:P==2?40.f:-15.f;}
bool Pump(int32 P){return !ProfileRifle()&&(P==2||P==3);}
bool ChannelMatches(const FFPSBodyState& S,int32 P)
{return ProfileRifle()?S.Contacts.Channel==(P==2?FName(TEXT("Inspect")):P==3||((SVCH()||M24())&&P==5)?FName(TEXT("Reload")):NAME_None):(S.Contacts.Channel==TEXT("Pump"))==Pump(P);}
bool Recipe(const FFPSBodyWeapon& W,int32 P)
{
    if(M24())
    {
        const bool Advanced=P>0&&P<5,Skeleton=Advanced&&P>=2,Carbon=Advanced&&P>=3;
        const auto Has=[&](const FString& Name){return W.Parts.ContainsByPredicate([&](const FFPSBodyAttachment& Part){return Part.bVisible&&Part.Mesh.ToSoftObjectPath().ToString().Contains(Name);});};
        const FString Grip=P==1?TEXT("phantom_reargrip"):P==2?TEXT("balanced_reargrip"):P==3||P==4?TEXT("stable_antislip_reargrip"):TEXT("false");
        bool Wet=true;
        const auto WetMaterial=[&](const TSoftObjectPtr<UMaterialInterface>& Ref)
        {
            const FString Path=Ref.ToSoftObjectPath().ToString();
            if(Path.Contains(TEXT("/StockContinuity20261031/"))||Path.Contains(TEXT("/StockMetalFinish20261031/"))
                ||Path.Contains(TEXT("/FinishUnified20261103/"))||Path.Contains(TEXT("/FactoryStockSeam20261105/")))
            {
                auto* Material=Ref.LoadSynchronous();float Value=0;
                // Match WeatherViewEffectsComponent::ResolveWet: contemporary
                // surface masters self-route through the exposed wet parameter.
                Wet&=Material&&Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("WeaponWetness")),Value);
            }
        };
        for(const auto& Ref:W.Materials)WetMaterial(Ref);
        for(const auto& Part:W.Parts)for(const auto& Ref:Part.Materials)WetMaterial(Ref);
        const bool Body=Has(TEXT("SM_M24_AdvancedFront_ForIndependentGrip"))==(Advanced&&Skeleton)
            &&Has(TEXT("SM_M24_m24_advanced_action"))==(Advanced&&!Skeleton)
            &&Has(TEXT("SM_M24_ReceiverStock_Advanced"))==(Advanced&&Skeleton&&!Carbon)
            &&Has(TEXT("SM_M24_ReceiverStock_Native"))==(!Advanced&&Skeleton&&!Carbon)
            &&Has(TEXT("SM_M24_CarbonSpine_Advanced"))==(Carbon&&Advanced)
            &&Has(TEXT("SM_M24_CarbonSpine_Native"))==(Carbon&&!Advanced);
        int32 MountedDevices=0;
        for(const auto& Part:W.Parts)
            if(Part.bVisible&&!Part.TacticalKind.IsNone())
            {
                ++MountedDevices;
                const FString Expected=P==1?TEXT("blessed_laser"):P==2?TEXT("flashlight"):TEXT("laser");
                if(Part.TacticalKind.ToString()!=Expected
                    ||Part.Mesh.ToSoftObjectPath().GetLongPackageName()!=TEXT("/Game/Weapons/M24/Tactical20261104/SM_")+Expected)return false;
            }
        const bool Audio=W.GunFireSound.ToSoftObjectPath().GetLongPackageName()==M24WeaponAssets::FireSoundPath
            &&W.GunSuppressedSound.ToSoftObjectPath().GetLongPackageName()==M24WeaponAssets::SuppressedSoundPath
            &&W.bGunSuppressed==Advanced;
        const bool Rear=Skeleton?Has(SniperSkeletonStock::M24GripMeshPath(Grip)):!Has(TEXT("/SM_M24_PistolGrip_"));
        const bool Profile=!Skeleton||W.GripProfile.ToSoftObjectPath().GetLongPackageName()==SniperSkeletonStock::M24ProfilePath(SniperSkeletonStock::M24GripFamilyForVariant(Grip,P==3||P==4));
        bool Finish=true,Sections=true;
        for(const auto& Part:W.Parts)
        {
            const FString Mesh=Part.Mesh.ToSoftObjectPath().GetAssetName();
            if(Mesh==TEXT("SM_M24_m24_advanced_action")||Mesh==TEXT("SM_M24_AdvancedFront_ForIndependentGrip")||Mesh==TEXT("SM_M24_ReceiverStock_Advanced"))
            {
                const TCHAR* Expected=Mesh==TEXT("SM_M24_m24_advanced_action")?TEXT("/FactoryStockSeam20261105/"):TEXT("/FinishUnified20261103/");
                Finish&=!Part.Materials.IsEmpty()&&Part.Materials[0].ToSoftObjectPath().ToString().Contains(Expected);
            }
        }
        if(const auto* Mesh=W.Mesh.LoadSynchronous())
        {
            for(int32 I=0;I<Mesh->GetMaterials().Num();++I)
            {
                const FName Slot=Mesh->GetMaterials()[I].MaterialSlotName;
                if(Slot==TEXT("M24_FactoryFront"))Sections&=W.HiddenMaterials.Contains(I)==Advanced;
                if(Slot==TEXT("M24_FactoryRearSeat"))Sections&=W.HiddenMaterials.Contains(I)==(Advanced||Skeleton);
                if(Slot==TEXT("M24_FactoryStock")||Slot==TEXT("M24_FactoryChassis"))Sections&=W.HiddenMaterials.Contains(I)==Skeleton;
            }
        }
        else Sections=false;
        if(!(Body&&Rear&&Wet&&Profile&&Finish&&Sections))UE_LOG(LogTemp,Warning,TEXT("M24_WIRE_RECIPE phase=%d body=%d rear=%d wet=%d profile=%d finish=%d sections=%d grip=%s"),P,Body,Rear,Wet,Profile,Finish,Sections,*W.GripProfile.ToString());
        return W.GunDefinition==M24WeaponAssets::Definition&&Body&&Rear&&Wet&&Profile&&Finish&&Sections
            &&Audio&&MountedDevices==int32(Advanced);
    }
    if(SVCH())
    {
        const bool Modified=P>0&&P<5;
        const auto Has=[&](const TCHAR* Name){return W.Parts.ContainsByPredicate([&](const FFPSBodyAttachment& Part){return Part.bVisible&&Part.Mesh.ToSoftObjectPath().ToString().Contains(Name);});};
        return W.GunDefinition==SVCHWeaponAssets::Definition
            &&W.GripProfile.ToSoftObjectPath().GetAssetName()==(P==5?TEXT("DA_SVCH_Grip_vertical"):TEXT("DA_SVCH_Grip_angled"))
            &&Has(P==5?TEXT("SM_SVD_vertical"):TEXT("SM_SVD_angled"))
            &&Has(Modified?TEXT("SM_SVCH_Magazine20"):TEXT("SM_SVCH_Magazine10"))
            &&Has(TEXT("SM_SniperHeavySuppressor"))==Modified&&W.bGunSuppressed==Modified;
    }
    if(!Saiga())return true;
    const bool Drum=P>0&&P<5;
    const auto Has=[&](const TCHAR* Name){return W.Parts.ContainsByPredicate([&](const FFPSBodyAttachment& Part){return Part.bVisible&&Part.Mesh.ToSoftObjectPath().ToString().Contains(Name);});};
    return W.GunDefinition==Saiga12KWeaponAssets::Definition
        &&W.GripProfile.ToSoftObjectPath().GetAssetName()==(P==5?TEXT("DA_vertical"):TEXT("DA_angled"))
        &&Has(P==5?TEXT("SM_Saiga12K_vertical"):TEXT("SM_Saiga12K_angled"))
        &&Has(TEXT("SM_Saiga12K_Drum20"))==Drum&&Has(TEXT("SM_Saiga12K_SpecialStock"))==Drum
        &&W.bGunSuppressed==Drum&&W.GunFireSound.ToSoftObjectPath().GetLongPackageName()==Saiga12KWeaponAssets::FireSoundPath;
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id,int32 Phase)
{
    auto S=Model->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};
    auto W=Model->CreateItem(SniperZhimingWire::Enabled()?SniperZhimingWire::Definition(Phase):M24()?M24WeaponAssets::Definition:SVCH()?SVCHWeaponAssets::Definition:Saiga()?Saiga12KWeaponAssets::Definition:M870WeaponAssets::Definition);W.InstanceId=Id;W.Place=1;W.Cell=6;W.Magazine=ProfileRifle()?Capacity(Phase):7;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(W.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("tactical"),Phase==1?TEXT("blessed_laser"):TEXT("laser"));
    if(SniperZhimingWire::Enabled())
    {
        Parts->Values.Reset();
        Parts->SetStringField(TEXT("muzzle"),Phase%2==0?SniperSuppressorAssets::Zhiming:TEXT("none"));
        W.Magazine=3;
    }
    else if(M24())
    {
        Parts->SetStringField(TEXT("tactical"),Phase==1?TEXT("blessed_laser"):Phase==2?TEXT("flashlight"):TEXT("laser"));
        Parts->SetStringField(TEXT("muzzle"),Phase>0&&Phase<5?M24Attachments::Suppressor:TEXT("none"));
        Parts->SetStringField(TEXT("body"),Phase>0&&Phase<5?M24Attachments::AdvancedAction:TEXT("false"));
        Parts->SetStringField(TEXT("stock"),Phase>=3?SniperSkeletonStock::M24CarbonId:Phase==2?SniperSkeletonStock::Id:TEXT("none")); // Legacy factory selection.
        Parts->SetStringField(TEXT("reargrip"),Phase==2?TEXT("balanced_reargrip"):Phase==3||Phase==4?TEXT("stable_antislip_reargrip"):TEXT("phantom_reargrip")); // Must clear when native.
        Parts->SetStringField(TEXT("magazine"),Phase==3||Phase==4?M24Attachments::ExtendedMagazine:TEXT("false"));
        if(Phase==5)
        {
            Data->SetBoolField(TEXT("reload_pending_cycle"),true);
            Data->SetBoolField(TEXT("reload_cycle_empty"),true);
        }
    }
    else if(SVCH())
    {
        Parts->SetStringField(TEXT("underbarrel"),Phase==5?TEXT("vertical_foregrip"):TEXT("angled_foregrip"));
        Parts->SetStringField(TEXT("magazine"),Phase>0&&Phase<5?TEXT("ext_mag"):TEXT("false"));
        if(Phase>0&&Phase<5){Parts->SetStringField(TEXT("muzzle"),SniperSuppressorAssets::Part);Parts->SetStringField(TEXT("optic"),TEXT("kv_scope_4x"));}
    }
    else if(Saiga())
    {
        Parts->SetStringField(TEXT("underbarrel"),Phase==5?TEXT("vertical_foregrip"):TEXT("angled_foregrip"));
        Parts->SetStringField(TEXT("magazine"),Phase==0?TEXT("false"):Phase==5?Saiga12KMagazineAssets::Part:Saiga12KMagazineAssets::DrumPart);
        if(Phase>0&&Phase<5){Parts->SetStringField(TEXT("stock"),Saiga12KSpecialStockAssets::Part);Parts->SetStringField(TEXT("muzzle"),TEXT("shotgun_suppressor"));Parts->SetStringField(TEXT("optic"),TEXT("panoramic_red_dot"));}
    }
    else if(Phase>=3)Parts->SetStringField(TEXT("stock"),TEXT("skeleton"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);W.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&W.Data));
    S.Items={W};return S;
}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {
        FPacketSimulationSettings Settings;Settings.PktLag=60;Settings.PktLoss=5;
        Driver->SetPacketSimulationSettings(Settings);
        UE_LOG(LogTemp,Display,TEXT("M870_PRESENTATION_NET lag_ms=%d loss_percent=%d role=%d"),
            Driver->PacketSimulationSettings.PktLag,Driver->PacketSimulationSettings.PktLoss,int32(World->GetNetMode()));
    }
#endif
}
}

void AShotgunWireAuditController::PoseM870Presentation(AFPSGAMECharacter* Pawn,int32 Phase,bool Muted)
{
    if(!Pawn)return;
    Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCharacterMovement()->DisableMovement();Pawn->GetCharacterMovement()->StopMovementImmediately();
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->bIsSprinting=false;Pawn->SprintPoseFactor=0;
    Pawn->bIsAiming=Phase!=0;Pawn->WeaponADSFactor=Pawn->bIsAiming?1.f:0.f;
    if(auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()))Move->bWantsToAim=Pawn->bIsAiming;
    if(auto* Controller=Pawn->GetController())Controller->SetControlRotation(FRotator(M870Wire::Pitch(Phase),0,0));
    // Actor ticking is paused for deterministic source frames. Normally its
    // UpdateCamera synchronizes this component; GetBaseAimRotation reads the
    // player camera cache, not just Controller.ControlRotation.
    Pawn->FirstPersonCamera->SetWorldRotation(FRotator(M870Wire::Pitch(Phase),0,0));
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();if(Body)Body->SetComponentTickEnabled(!Muted);
    if(SniperZhimingWire::Enabled())
    {
        Pawn->bInventoryWeaponReady=true;
        if(Body)Body->SetComponentTickEnabled(true);
        return;
    }
    if(!Pawn->IsLocallyControlled())return;
    if(M870Wire::ProfileRifle())
    {
        Pawn->bInventoryWeaponReady=true;
        const bool Normal=(M870Wire::SVCH()||M870Wire::M24())&&Phase==5;
        Pawn->WeaponState=Normal?EAKMWeaponState::Reloading:Phase==2?EAKMWeaponState::Inspecting:Phase==3?EAKMWeaponState::ReloadingEmpty:EAKMWeaponState::Idle;
        auto* Clip=Normal?Pawn->ReloadAnimation.Get():Phase==2?Pawn->InspectAnimation.Get():Phase==3?((M870Wire::SVCH()||M870Wire::M24())?Pawn->ReloadEmptyAnimation.Get():Pawn->DrumReloadEmptyAnimation.Get()):Pawn->IdleAnimation.Get();
        Pawn->ActiveActionAnimation=Phase==2||Phase==3||Normal?Clip:nullptr;Pawn->bPendingEmptyReload=Phase==3;
        Pawn->ActionPlayRate=1.f;Pawn->ActionStartPosition=0.f;Pawn->WeaponStateDuration=Pawn->ActionDuration=Clip?Clip->GetPlayLength():1.f;
        Pawn->WeaponStateElapsed=(Phase==2?.5f:Phase==3?.88f:0.f)*Pawn->WeaponStateDuration;
        if(M870Wire::SVCH()&&(Phase==3||Normal))Pawn->WeaponStateElapsed=(Phase==3?325.f:220.f)/120.f;
        Pawn->UpdateActionPose(0.f);Pawn->AKMViewmodel->TickAnimation(0.f,false);Pawn->AKMViewmodel->RefreshBoneTransforms();Pawn->AKMViewmodel->UpdateChildTransforms();
        return;
    }
    // The fixture samples held authored frames with SingleNode. Keep the real
    // manifest captured before that temporary sampling mode; runtime uses its
    // gunplay anim instance and does not need this fixture-only refresh pause.
    if(Body){Body->RefreshCountdown=600.f;Body->bEquipmentDirty=false;}
    const bool Pump=M870Wire::Pump(Phase);
    if(Pump&&Pawn->ActiveActionAnimation!=Pawn->FireAnimation)Pawn->LastShotWorldTime=Pawn->GetWorld()->GetTimeSeconds();
    Pawn->ActiveActionAnimation=Pump?Pawn->FireAnimation.Get():nullptr;Pawn->ActionDuration=600.f;
    auto* Mesh=Pawn->AKMViewmodel.Get();auto* Clip=Pump?Pawn->FireAnimation.Get():Pawn->IdleAnimation.Get();
    if(!Mesh||!Clip)return;
    if(!Mesh->GetSingleNodeInstance()||Mesh->GetSingleNodeInstance()->GetCurrentAsset()!=Clip)Mesh->PlayAnimation(Clip,false);
    Mesh->SetPlayRate(0.f);Mesh->SetPosition(Pump?.35f:0.f,false);Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();Mesh->UpdateChildTransforms();
}

void AShotgunWireAuditController::SetupM870Presentation(int32 Phase,const FString& Id,AFPSGAMECharacter* Host)
{
    if(HasAuthority()||Phase==Current||!Host)return;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!Model||!Model->IsAudit())return;
    if(Current<0)M870Wire::Network(GetWorld());
    if(M870Wire::ProfileRifle()&&Current<0)
    {
        Model->Current=M870Wire::Seed(Model,Id,Phase);Model->CurrentPawn=Subject;Subject->ApplyColdSteelProfile(Model);
        // Only the client previews these. A coalesced server loadout must not
        // retain a different schema because of local component creation order.
        if(M870Wire::M24())
        {
            Subject->SetGunsmithStock(SniperSkeletonStock::Id);
            Subject->SetGunsmithHandstop(M24Attachments::AdvancedAction);
            Subject->SetGunsmithRearGrip(TEXT("balanced_reargrip"));
            Subject->SetGunsmithStock(M24Attachments::CheekRest);
        }
        else for(const TCHAR* Grip:{TEXT("canted_foregrip"),TEXT("prism_handstop"),TEXT("vertical_foregrip")})Subject->SetGunsmithHandstop(Grip);
        Subject->bWeaponVisualPartsApplied=false;
    }
    if(M870Wire::M24()&&Phase>0&&Phase<5)
    {
        // Deliberately create the final stock before the body on the owner.
        // Authority uses the normal body -> stock -> grip application order.
        Subject->SetGunsmithStock(Phase>=2?SniperSkeletonStock::Id:M24Attachments::CheekRest);
        Subject->SetGunsmithHandstop(M24Attachments::AdvancedAction);
        Subject->bWeaponVisualPartsApplied=false;
    }
    Model->Current=M870Wire::Seed(Model,Id,Phase);Model->CurrentPawn=Subject;
    Subject->AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());Subject->ApplyColdSteelProfile(Model);
    if(M870Wire::M24()&&Phase!=4)
    {
        // Exercise the owner's real interrupt/draw clock in an isolated profile.
        // The fixture holds source frames so packet delay cannot move a boundary.
        const auto Ready=[&](){return Subject->EquipAnimation&&Subject->EquipAnimation->GetPathName()
            ==FString(M24WeaponAssets::ReadyEquipPath)+TEXT(".A_M24_equip_ready");};
        bM24CycleCasePassed=Ready()&&!Subject->bM24EquipBoltPending;
        if(Phase==5)bM24CycleCasePassed&=Subject->bM24DeferReloadTail;
        if(Phase==2||Phase==3)
        {
            const bool BeforeExtraction=Phase==3;
            const double Now=GetWorld()->GetTimeSeconds();
            Subject->WeaponState=EAKMWeaponState::Idle;
            Subject->ActiveActionAnimation=Subject->FireAnimation;
            Subject->LastShotWorldTime=Now-(BeforeExtraction?.33:1.17);
            Subject->ActionPlayRate=1.f;Subject->ActionDuration=M24WeaponAssets::FireDuration;
            Subject->InterruptActionsForPriority(true);
            const auto Marked=*Model->FindItem(Id);
            auto Merged=Marked;WeaponReloadStages::SetNeedsCycle(Merged,0);
            ColdSteelProfileRecovery::LoadedAmmo(Merged,Marked);
            bM24CycleCasePassed&=WeaponReloadStages::NeedsM24ShotCycle(Merged)
                &&WeaponReloadStages::HasM24PendingCasing(Merged)==BeforeExtraction;
            Subject->StartEquipCharge();
            bM24CycleCasePassed&=!Ready()&&Subject->bM24EquipBoltPending;
            if(Phase==2)
            {
                const float EquipRate=Subject->FirearmEquipRate;
                const float Lift=23.f/30.f,Lock=42.f/30.f;
                bM24CycleCasePassed&=FMath::IsNearlyEqual(Subject->M24EquipSourceTime(.5f/EquipRate),.5f,.002f)
                    &&FMath::IsNearlyEqual(Subject->M24EquipSourceTime((Lift+(Lock-Lift)/1.2f)/EquipRate),Lock,.002f);
                const float SecondsPerFrame=Subject->GetReloadSeconds(false)/123.f;
                TGuardValue<float> Duration(Subject->WeaponStateDuration,Subject->GetReloadSeconds(true));
                TGuardValue<TObjectPtr<UAnimSequence>> EmptyClip(Subject->ActiveActionAnimation,Subject->ReloadEmptyAnimation);
                const float Seat=Subject->ReloadRuntimeTime(M24WeaponAssets::MagazineSeat);
                const float BoltSeconds=Subject->ReloadRuntimeTime(M24WeaponAssets::ChargeRelease)
                    -Subject->ReloadRuntimeTime(M24WeaponAssets::ChargeLift);
                bM24CycleCasePassed&=FMath::IsNearlyEqual(Seat,93.f*SecondsPerFrame,.003f)
                    &&FMath::IsNearlyEqual(BoltSeconds,22.f*SecondsPerFrame/1.2f,.003f);
            }
            Subject->WeaponActionStartedAt=Now-.1/Subject->ActionPlayRate;
            Subject->InterruptActionsForPriority(true);Subject->StartEquipCharge();
            bM24CycleCasePassed&=Subject->bM24EquipBoltPending&&Subject->bM24PendingCasing==BeforeExtraction;
            Subject->WeaponActionStartedAt=Now-(M24WeaponAssets::EquipBoltEject+.01)/Subject->ActionPlayRate;
            Subject->AdvanceM24EquipBolt();
            bM24CycleCasePassed&=WeaponReloadStages::NeedsM24ShotCycle(*Model->FindItem(Id))
                &&!WeaponReloadStages::HasM24PendingCasing(*Model->FindItem(Id));
            Subject->WeaponActionStartedAt=Now-(M24WeaponAssets::EquipBoltClosed+.01)/Subject->ActionPlayRate;
            Subject->AdvanceM24EquipBolt();
            ColdSteelProfileRecovery::LoadedAmmo(Merged,*Model->FindItem(Id));
            bM24CycleCasePassed&=!WeaponReloadStages::NeedsCycle(Merged)&&!WeaponReloadStages::HasM24PendingCasing(Merged)
                &&Merged.Magazine==Marked.Magazine;
            Subject->StartEquipCharge();bM24CycleCasePassed&=Ready();
        }
    }
    Subject->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);
    auto* Body=Subject->FindComponentByClass<UFPSPlayerBodyComponent>();
    Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    ObserverSubject=Host;Current=Phase;Weapon=Id;Started=GetWorld()->GetRealTimeSeconds();bReported=false;bSent=false;
    if(SniperZhimingWire::Enabled())
    {
        bObservedSniperStun=false;SniperStunPeak=0.f;
        SniperStunFirstAt=SniperStunLastAt=-1.;SentAt=-1.;
    }
    PoseM870Presentation(Subject,Phase,Phase==4);
    UE_LOG(LogTemp,Display,TEXT("M870_PRESENTATION_CLIENT_SETUP phase=%d"),Phase);
}

bool AShotgunWireAuditController::TickM870Presentation(float Delta)
{
    if(!M870Wire::Enabled())return false;
    Super::Tick(Delta);if(HasAuthority()||!IsLocalController())return true;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(Current<0||bReported)return true;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());PoseM870Presentation(Subject,Current,Current==4);
    if(SniperZhimingWire::Enabled()){TickSniperZhiming(Subject,Now);return true;}
    if(M870Wire::M24()&&Current==1&&!bSent&&Now-Started>=4.)
    {
        if(auto* PS=GetPlayerState<AColdSteelPlayerState>())PS->ServerRememberM24Launch(Subject,Weapon,1,1);
        bSent=true;
    }
    if(Now-Started<5.)return true;
    auto* Seen=ObserverSubject?ObserverSubject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Own=Subject?Subject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Seen||!Own)return true;
    const auto& State=Seen->ReplicatedState;
    const bool Aim=FMath::IsNearlyEqual(State.AimPitch,M870Wire::Pitch(Current),1.f)&&State.bAiming==(Current!=0);
    const bool Rig=Seen->BodyAnimation&&Seen->BodyAnimation->RifleHold.bValid&&Seen->HasMatchingMotionRig(0);
    const bool Pump=M870Wire::ChannelMatches(State,Current);
    FFPSBodyLaserSample Laser;bool Beam=false;
    if(State.Lasers.Num()==1)Beam=Seen->ResolveLaserSample(0,State.Lasers[0].PartIndex,State.Lasers[0].Schema,Laser);
    if(!M870Wire::ExpectsLaser(Current))Beam=State.Lasers.IsEmpty();
    const bool Applied=Seen->BodyAnimation&&Seen->BodyAnimation->LeftGripFromRight.GetLocation().Equals(State.Contacts.SupportGrip.GetLocation(),.15);
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Current);
    Row->SetBoolField(TEXT("remote_aim"),Aim);Row->SetBoolField(TEXT("remote_rig"),Rig);Row->SetBoolField(TEXT("remote_pump"),Pump);
    Row->SetBoolField(TEXT("remote_laser"),Beam);Row->SetBoolField(TEXT("remote_applied_grip"),Applied);
    Row->SetNumberField(TEXT("aim_pitch"),State.AimPitch);Row->SetBoolField(TEXT("aiming"),State.bAiming);
    Row->SetNumberField(TEXT("grip_error_cm"),Seen->BodyAnimation?FVector::Distance(Seen->BodyAnimation->LeftGripFromRight.GetLocation(),State.Contacts.SupportGrip.GetLocation()):-1.);
    const bool Parts=Seen->MotionBindings.Num()==1&&M870Wire::Recipe(Seen->MotionBindings[0].Definition,Current)
        &&(!M870Wire::ProfileRifle()||Subject->GetMagazineCapacity()==M870Wire::Capacity(Current));
    const bool FXReady=!M870Wire::M24()||(Subject->WeaponFX&&Subject->WeaponFX->IsReady()
        &&Seen->RemoteGunHands[0].FX&&Seen->RemoteGunHands[0].FX->IsReady());
    Row->SetBoolField(TEXT("owner_fx_ready"),FXReady);
    Row->SetBoolField(TEXT("stock_socket_present"),Subject->AKMViewmodel->DoesSocketExist(TEXT("WPN_StockContact")));
    Row->SetBoolField(TEXT("equipment_recipe"),Parts);
    Row->SetBoolField(TEXT("owner_m24_cycle"),bM24CycleCasePassed);
    const bool Passed=Aim&&Rig&&Pump&&Beam&&Applied&&Parts&&FXReady&&bM24CycleCasePassed;
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=Passed;bReported=true;
    const FVector OwnerEnd=Own->DisplayState.Lasers.Num()==1?FVector(Own->DisplayState.Lasers[0].End):FVector::ZeroVector;
    ServerPresentationResult(Current,Passed,Laser.End,OwnerEnd,Own->DisplayState.Contacts.SupportGrip.GetLocation());
    ShotgunWire::Save(Results,bAllPassed,TEXT("client"));
    return true;
}

void AShotgunWireAuditController::ServerPresentationResult_Implementation(int32 Phase,bool ObserverOK,FVector HostLaser,FVector OwnerLaser,FVector OwnerGrip)
{
    if(!M870Wire::Enabled()||Phase!=Expected||Finished!=Phase)return;
    if(SniperZhimingWire::Enabled())
    {
        if(Results.Num()!=Phase+1)return;
        Results.Last()->AsObject()->SetBoolField(TEXT("client_passed"),ObserverOK);
        bAllPassed&=ObserverOK;++Finished;return;
    }
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());auto* Body=Subject?Subject->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    UFPSPlayerBodyComponent* HostBody=nullptr;
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController()&&It->Get()->GetPawn())HostBody=It->Get()->GetPawn()->FindComponentByClass<UFPSPlayerBodyComponent>();
    bool Identity=false,Aim=false,Support=false,Laser=false,HostEnd=false;
    if(Body&&HostBody)
    {
        const auto& State=Body->ReplicatedState;
        const auto* PS=GetPlayerState<AColdSteelPlayerState>();
        const auto* Item=PS&&PS->ShadowModel?PS->ShadowModel->Equipped():nullptr;
        Identity=Item&&State.WeaponInstance==Item->InstanceId;
        Aim=FMath::IsNearlyEqual(State.AimPitch,M870Wire::Pitch(Phase),1.f)&&State.bAiming==(Phase!=0);
        if(Phase==4){Support=!State.Contacts.HasSupportGrip;Laser=State.Lasers.IsEmpty();}
        else
        {
            Support=Body->HasMatchingMotionRig(0)&&State.Contacts.HasSupportGrip&&State.Contacts.SupportGrip.GetLocation().Equals(OwnerGrip,.05)
                &&M870Wire::ChannelMatches(State,Phase);
            // Inspection/reload stop sight convergence, not the physical ray.
            // The observer still receives the owner's actual emitter ray.
            Laser=M870Wire::ExpectsLaser(Phase)?State.Lasers.Num()==1&&FVector(State.Lasers[0].End).Equals(OwnerLaser,.5):State.Lasers.IsEmpty();
        }
        HostEnd=M870Wire::ExpectsLaser(Phase)?HostBody->DisplayState.Lasers.Num()==1&&FVector(HostBody->DisplayState.Lasers[0].End).Equals(HostLaser,.5):HostBody->DisplayState.Lasers.IsEmpty();
        Identity&=Body->LocalWeapons.Num()==1&&M870Wire::Recipe(Body->LocalWeapons[0],Phase);
        if(M870Wire::M24())
        {
            Identity&=Subject->WeaponFX&&Subject->WeaponFX->IsReady();
            Identity&=Body->RemoteGunHands[0].FX&&Body->RemoteGunHands[0].FX->IsReady();
            if(auto* Host=Cast<AFPSGAMECharacter>(HostBody->GetOwner()))Identity&=Host->WeaponFX&&Host->WeaponFX->IsReady();
        }
    }
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("phase"),Phase);
    Row->SetBoolField(TEXT("client_observer"),ObserverOK);Row->SetBoolField(TEXT("server_identity"),Identity);Row->SetBoolField(TEXT("server_aim"),Aim);
    if(M870Wire::M24()&&Phase==1)
    {
        bool Matched=false,UnknownRejected=false,ReplayRejected=false,RedirectRejected=false;
        auto* PS=GetPlayerState<AColdSteelPlayerState>();
        if(PS&&PS->ShadowModel&&HostBody&&Subject)
        {
            const auto* Fired=PS->ShadowModel->Equipped();
            const auto* Launch=PS->M24Launches.Find(1);
            if(Fired&&Launch)
            {
                FColdSteelNetHitReport Hit;
                Hit.ItemInstance=Fired->InstanceId;Hit.ItemDefinition=Fired->Definition;Hit.FireSequence=1;
                Hit.Flags=(1<<1)|(1<<6);Hit.ConvergenceRounds=1;
                // A fixed world target isolates shot identity from the frozen
                // observer pawn's unrelated pose history. Normal LOS still runs.
                auto* Target=GetWorld()->SpawnActor<ATargetPoint>(Launch->Eye+Launch->ViewForward*1000.f,FRotator::ZeroRotator);
                Hit.Target=Target;Hit.AimOrigin=Launch->Eye;Hit.ImpactPoint=Launch->Eye+Launch->ViewForward*1000.f;
                Hit.ClientFireTime=GetWorld()->GetGameState()->GetServerWorldTimeSeconds();
                Hit.Direction=(FVector(Hit.ImpactPoint)-FVector(Hit.AimOrigin)).GetSafeNormal();
                Hit.HitNormal=-FVector(Hit.Direction);
                // The owner registered the launch through its real PlayerState RPC.
                // Put it out of the active group and shorten the replacement range.
                TGuardValue<int32> OtherSlot(PS->ShadowModel->Current.ActiveWeaponSlot,9);
                TGuardValue<float> ShortRange(Subject->TraceDistance,5.f);
                FColdSteelPreparedHit Prepared;
                auto Redirected=Hit;Redirected.ImpactPoint=Launch->Eye-Launch->ViewForward*1000.f;
                RedirectRejected=!PS->PrepareHitReport(Redirected,Prepared);
                Matched=PS->PrepareHitReport(Hit,Prepared)&&Prepared.Item.InstanceId==Hit.ItemInstance&&Prepared.Damage>0;
                ReplayRejected=!PS->PrepareHitReport(Hit,Prepared);
                ++Hit.FireSequence;UnknownRejected=!PS->PrepareHitReport(Hit,Prepared);
                if(Target)Target->Destroy();
            }
        }
        Row->SetBoolField(TEXT("registered_m24_after_swap"),Matched);
        Row->SetBoolField(TEXT("duplicate_m24_target_rejected"),ReplayRejected);
        Row->SetBoolField(TEXT("unregistered_stowed_m24_rejected"),UnknownRejected);
        Row->SetBoolField(TEXT("redirected_stowed_m24_rejected"),RedirectRejected);
        Identity&=Matched&&UnknownRejected&&ReplayRejected&&RedirectRejected;
        Row->SetBoolField(TEXT("server_identity"),Identity);
    }
    Row->SetBoolField(TEXT("server_support_or_expiry"),Support);Row->SetBoolField(TEXT("owner_laser_or_expiry"),Laser);Row->SetBoolField(TEXT("host_laser_endpoint"),HostEnd);
    if(Body)
    {
        Row->SetNumberField(TEXT("aim_pitch"),Body->ReplicatedState.AimPitch);Row->SetBoolField(TEXT("aiming"),Body->ReplicatedState.bAiming);
        Row->SetBoolField(TEXT("rig_matches"),Body->HasMatchingMotionRig(0));Row->SetBoolField(TEXT("has_support"),Body->ReplicatedState.Contacts.HasSupportGrip);
        Row->SetStringField(TEXT("motion_channel"),Body->ReplicatedState.Contacts.Channel.ToString());
        Row->SetNumberField(TEXT("grip_error_cm"),FVector::Distance(Body->ReplicatedState.Contacts.SupportGrip.GetLocation(),OwnerGrip));
        Row->SetNumberField(TEXT("received_age"),Body->ServerClock()-Body->LastPresentationReceivedAt);
    }
    Results.Add(MakeShared<FJsonValueObject>(Row));bAllPassed&=ObserverOK&&Identity&&Aim&&Support&&Laser&&HostEnd;++Finished;
    UE_LOG(LogTemp,Display,TEXT("M870_PRESENTATION_WIRE_CASE phase=%d observer=%d identity=%d aim=%d grip=%d laser=%d host_end=%d"),Phase,ObserverOK,Identity,Aim,Support,Laser,HostEnd);
}

bool AShotgunWireAuditGameMode::TickM870Presentation(float Delta)
{
    if(!M870Wire::Enabled())return false;
    Super::Tick(Delta);const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return true;}
    if(!Guest)return true;
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Pawn||!PS||!Model||!Model->IsAudit())return true;
    if(!HostPawn)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())HostPawn=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    if(!HostPawn)return true;
    if(Guest->Finished>=6||Now-Joined>150.)
    {
        bPresentationPassed&=Guest->Finished==6&&Guest->bAllPassed;PresentationHistory.Append(Guest->Results);
        Guest->ClientFinish(Guest->Finished==6&&Guest->bAllPassed);++PresentationConnections;
        if(PresentationConnections==1)
        {
            Guest=nullptr;Prepared=INDEX_NONE;
            UE_LOG(LogTemp,Display,TEXT("M870_PRESENTATION_REJOIN_READY"));return true;
        }
        ShotgunWire::Save(PresentationHistory,bPresentationPassed,TEXT("listen_host"));ExitAt=Now+3.;return true;
    }
    if(Prepared!=Guest->Finished)
    {
        if(Prepared==INDEX_NONE)M870Wire::Network(GetWorld());
        Prepared=Guest->Finished;
        if(SniperZhimingWire::Enabled()?Prepared%2==0:Prepared!=4)Weapon=FGuid::NewGuid().ToString();
        Guest->Expected=Prepared;
        if(SniperZhimingWire::Enabled())SniperZhimingWire::EnsureTarget(GetWorld());
        const auto Seed=M870Wire::Seed(Model,Weapon,Prepared);
        if(!PS->ShadowModel)PS->ShadowModel=Model->CreateShadowModel(Seed);else PS->ShadowModel->Current=Seed;
        PS->ShadowModel->CurrentPawn=Pawn;Pawn->NetShadowProfile=PS->ShadowModel;
        Pawn->AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());Pawn->ApplyColdSteelProfile(PS->ShadowModel);
        Model->Current=M870Wire::Seed(Model,TEXT("M870Host_")+Weapon,Prepared);Model->CurrentPawn=HostPawn;
        HostPawn->AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());HostPawn->ApplyColdSteelProfile(Model);
        Pawn->SetActorLocationAndRotation(FVector(0,0,500),FRotator::ZeroRotator);HostPawn->SetActorLocationAndRotation(FVector(0,1000,500),FRotator::ZeroRotator);
        for(auto* C:{Pawn,HostPawn.Get()})if(auto* B=C->FindComponentByClass<UFPSPlayerBodyComponent>())
        {B->SetComponentTickEnabled(true);B->DisplayState=C->IsLocallyControlled()?B->SampleLocalState():B->SampleRemoteAuthorityState();B->CaptureEquipment();}
        LastSetup=-10;
    }
    AShotgunWireAuditController::PoseM870Presentation(Pawn,Prepared,false);
    AShotgunWireAuditController::PoseM870Presentation(HostPawn,Prepared,false);
    if(Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Prepared,Weapon,HostPawn);}
    return true;
}
