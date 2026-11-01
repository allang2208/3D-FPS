#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/M24WeaponAssets.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

// Explicit, isolated -game fixture. Exercises the production state machine,
// pose graph, component framing, camera, optics and animation recovery together.
void AFPSGAMECharacter::RunM24ActionReview(float DeltaSeconds)
{
    struct FRun {FString Out;int32 Phase=-1,Frame=-1;double Start=0,End=0;TArray<TSharedPtr<FJsonValue>> Rows;};
    static FRun R;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PC=Cast<APlayerController>(GetController());const double Now=GetWorld()->GetTimeSeconds();
    if(Now<2||!PC)return;
    if(!Profile||!Profile->IsAudit()||!Profile->ProfileSlot().Contains(TEXT("M24ActionAudit")))
    {UE_LOG(LogTemp,Error,TEXT("M24_ACTION_REVIEW_UNSAFE_PROFILE"));FPlatformMisc::RequestExitWithStatus(false,1);return;}
    const auto TF=[](const FTransform& T){TArray<TSharedPtr<FJsonValue>> A;const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})A.Add(MakeShared<FJsonValueNumber>(V));return A;};
    if(R.Out.IsEmpty())
    {
        FParse::Value(FCommandLine::Get(),TEXT("M24ReviewOutput="),R.Out);
        if(R.Out.IsEmpty()){FPlatformMisc::RequestExitWithStatus(false,2);return;}
        IFileManager::Get().MakeDirectory(*(R.Out/TEXT("Frames")),true);
        auto S=Profile->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=Profile->CreateItem(M24WeaponAssets::Definition);W.Place=1;W.Cell=9;W.Magazine=5;S.Items.Add(W);
        auto Ammo=Profile->CreateItem(TEXT("ammo_m24_762x51"));Ammo.Place=0;Ammo.Cell=0;Ammo.Count=90;S.Items.Add(Ammo);
        S.ActiveWeaponSlot=9;S.Stamina=Profile->MaxStamina();
        if(!Profile->CommitState(S)){FPlatformMisc::RequestExitWithStatus(false,3);return;}
        bMPAutoInputActive=true; // This isolated fixture supplies input without physical keys.
        R.End=Now+2.;return;
    }
    static const TCHAR* Names[]={TEXT("equip"),TEXT("idle"),TEXT("hip_fire_cycle"),TEXT("normal_reload"),TEXT("ads_in"),TEXT("ads_fire_cycle"),TEXT("ads_out"),TEXT("empty_reload"),TEXT("cycle_only"),TEXT("inspect"),TEXT("quick_melee"),TEXT("walk"),TEXT("sprint"),TEXT("sprint_to_ads")};
    const int32 PhaseCount=FParse::Param(FCommandLine::Get(),TEXT("M24Baseline"))?4:UE_ARRAY_COUNT(Names);
    if(Now>=R.End)
    {
        ++R.Phase;R.Start=Now;
        if(R.Phase>=PhaseCount)
        {
            auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("frames"),R.Rows);
            Report->SetStringField(TEXT("mesh"),GetPathNameSafe(AKMViewmodel->GetSkeletalMeshAsset()));
            Report->SetNumberField(TEXT("phase_count"),PhaseCount);Report->SetBoolField(TEXT("complete"),true);
            FString JSON;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&JSON));
            FFileHelper::SaveStringToFile(JSON,*(R.Out/TEXT("runtime.json")));
            UE_LOG(LogTemp,Display,TEXT("M24_ACTION_REVIEW_COMPLETE phases=%d samples=%d"),PhaseCount,R.Rows.Num());
            FPlatformMisc::RequestExitWithStatus(false,0);return;
        }
        float Duration=1.f;
        switch(R.Phase)
        {
        case 0:StartEquipCharge();Duration=WeaponStateDuration+.7f;break;
        case 1:Duration=2.f;break;
        case 2:FirePressed();FireReleased();Duration=ActionDuration+.7f;break;
        case 3:ReloadPressed();Duration=WeaponStateDuration+.7f;break;
        case 4:bAimHeld=true;SetAimingState(true);Duration=1.2f;break;
        case 5:FirePressed();FireReleased();Duration=ActionDuration+.7f;break;
        case 6:bAimHeld=false;SetAimingState(false);Duration=.8f;break;
        case 7:
        {
            auto S=Profile->Snapshot();for(auto& W:S.Items)if(W.InstanceId==ActiveInventoryWeapon)W.Magazine=0;
            Profile->CommitState(S);MagazineAmmo=0;ReloadPressed();Duration=WeaponStateDuration+.7f;break;
        }
        case 8:Profile->MarkM24CycleInterrupted(ActiveInventoryWeapon);ReloadPressed();Duration=WeaponStateDuration-WeaponStateElapsed+.7f;break;
        case 9:InspectPressed();Duration=WeaponStateDuration+.7f;break;
        case 10:TriggerRifleStockMelee();Duration=WeaponStateDuration+.7f;break;
        case 11:Duration=1.5f;break;
        case 12:bSprintHeld=true;MoveInput=FVector2D(0,1);Duration=2.f;break;
        case 13:bSprintHeld=false;MoveInput=FVector2D::ZeroVector;bAimHeld=true;SetAimingState(true);Duration=1.2f;break;
        }
        R.End=Now+Duration;
        UE_LOG(LogTemp,Display,TEXT("M24_ACTION_REVIEW_PHASE %s duration=%.3f clip=%s"),Names[R.Phase],Duration,*GetPathNameSafe(ActiveActionAnimation));
    }
    if(R.Phase<0)return;
    if(R.Phase==11||R.Phase==12)AddMovementInput(GetActorForwardVector(),1.f);
    const int32 Frame=FMath::FloorToInt(Now*30);
    if(Frame==R.Frame||FScreenshotRequest::IsScreenshotRequested())return;R.Frame=Frame;
    AKMViewmodel->TickAnimation(0,false);AKMViewmodel->RefreshBoneTransforms();AKMViewmodel->UpdateChildTransforms();
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("phase"),Names[R.Phase]);
    Row->SetNumberField(TEXT("phase_time"),Now-R.Start);Row->SetNumberField(TEXT("time"),Now);
    Row->SetStringField(TEXT("clip"),GetPathNameSafe(ActiveActionAnimation));Row->SetNumberField(TEXT("source_time"),GunplayAnimation?GunplayAnimation->ActionTime:0);
    Row->SetNumberField(TEXT("action_alpha"),GunplayAnimation?GunplayAnimation->ActionAlpha:0);
    Row->SetNumberField(TEXT("action_framing"),M4ActionFramingAlpha);Row->SetNumberField(TEXT("ads"),WeaponADSFactor);
    Row->SetNumberField(TEXT("horizontal_fov"),FirstPersonCamera->FieldOfView);Row->SetNumberField(TEXT("scope_alpha"),GetScopePresentationAlpha());
    Row->SetNumberField(TEXT("magazine"),MagazineAmmo);Row->SetNumberField(TEXT("weapon_state"),int32(WeaponState));
    Row->SetBoolField(TEXT("sprinting"),bIsSprinting);Row->SetNumberField(TEXT("speed"),GetVelocity().Size2D());
    Row->SetBoolField(TEXT("cycle_only"),bReloadCycleOnly);Row->SetNumberField(TEXT("reload_resume"),ReloadResumeElapsed);
    Row->SetArrayField(TEXT("camera"),TF(FirstPersonCamera->GetComponentTransform()));Row->SetArrayField(TEXT("mesh_world"),TF(AKMViewmodel->GetComponentTransform()));
    Row->SetArrayField(TEXT("mesh_relative"),TF(AKMViewmodel->GetRelativeTransform()));
    auto Bones=MakeShared<FJsonObject>();for(const TCHAR* N:{TEXT("WPN_root"),TEXT("WPN_SOCKET_Muzzle"),TEXT("WPN_StockContact"),TEXT("hand_l"),TEXT("hand_r"),TEXT("upperarm_l"),TEXT("upperarm_r"),TEXT("lowerarm_l"),TEXT("lowerarm_r")})Bones->SetArrayField(N,TF(AKMViewmodel->GetSocketTransform(N)));
    Row->SetObjectField(TEXT("bones"),Bones);
    const FString Name=FString::Printf(TEXT("%04d_%s.png"),R.Rows.Num(),Names[R.Phase]);Row->SetStringField(TEXT("image"),Name);R.Rows.Add(MakeShared<FJsonValueObject>(Row));
    // The scope mask/reticle is viewport UI; omitting it would falsely present
    // the scoped action as an empty zoomed world after the rig is owner-hidden.
    FScreenshotRequest::RequestScreenshot(R.Out/TEXT("Frames")/Name,true,false);
}
