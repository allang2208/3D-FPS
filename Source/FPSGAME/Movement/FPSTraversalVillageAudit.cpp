#include "FPSTraversalComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

void UFPSTraversalComponent::RunVillageAudit()
{
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* PC=GetWorld()->GetFirstPlayerController();
    auto* P=C->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const float Now=GetWorld()->GetTimeSeconds();
    const FString Out=FPaths::ProjectSavedDir()/TEXT("TraversalRuntimeAudit")/P->ProfileSlot();
    const auto Check=[&](bool OK,const TCHAR* Label)
    { if(!OK) ++AuditFailures; UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_VILLAGE %s case=%d %s"),OK?TEXT("PASS"):TEXT("FAIL"),AuditCase,Label); };
    if (Now<12.f) return;
    if (AuditStage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        Check(GetWorld()->GetMapName().Contains(TEXT("L_Normandy_FPS_Test")),TEXT("actual village map and possessed FPS character"));
        Check(Arms && VaultClip && MantleClip && ClimbClip,TEXT("native traversal assets loaded in village"));
        auto S=P->Snapshot(); S.Items.Reset(); S.Hotbar.Init(TEXT(""),4); S.HotbarDefinitions.Init(TEXT(""),4);
        auto W=P->CreateItem(TEXT("ue_m4a1")); W.Place=1; W.Cell=6; W.Magazine=17; S.Items.Add(W); S.ActiveWeaponSlot=6;
        P->CommitState(S); AuditAt=Now; AuditStage=1; return;
    }
    if (AuditStage==1 && Now-AuditAt>2.f && !C->IsWeaponBusy())
    {
        const FVector Positions[]={
            {-2592.542,34917.466,-11402.279},{-3179.054,34373.355,-11391.550},
            {-4848.637,33606.409,-11359.744},{-4269.553,32848.110,-11363.992},
            {-4269.328,32660.176,-11385.821},{-3977.526,32289.667,-11396.383},
            {-3718.254,32852.775,-11376.188},{-3946.361,32849.745,-11360.201},
            {-3910.044,32851.213,-11361.555},{-3981.697,32851.550,-11358.195}};
        TSet<UPrimitiveComponent*> Selected;
        for (int32 I=0;I<UE_ARRAY_COUNT(Positions);++I)
        {
            C->SetActorLocation(Positions[I]); C->GetCharacterMovement()->StopMovementImmediately();
            C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            for (int32 Yaw=0;Yaw<360;Yaw+=15)
            {
                C->SetActorRotation(FRotator(0,Yaw,0));
                PC->SetControlRotation(FRotator(0,Yaw,0));
                const auto T=FindTarget(true,true);
                if (!T.Obstacle) continue;
                const auto* Mesh=Cast<UStaticMeshComponent>(T.Obstacle);
                UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_VILLAGE_PROBE index=%d yaw=%d reason=%s action=%d height=%.2f depth=%.2f facing=%.3f mobility=%d top=%d approach=%d path=%d actor=%s mesh=%s pos=%s"),
                    I,Yaw,*T.Reason,(int32)T.Action,T.Probe.Height,T.Probe.Depth,T.Probe.FacingDot,(int32)T.Obstacle->Mobility,
                    T.Probe.bTopStandingSpace,T.Probe.bApproachClear,T.Probe.bMantlePathClear,*GetNameSafe(T.Obstacle->GetOwner()),
                    Mesh?*GetNameSafe(Mesh->GetStaticMesh()):TEXT("none"),*Positions[I].ToString());
                if ((T.Action==EFPSTraversalAction::Vault || T.Action==EFPSTraversalAction::Mantle) && !Selected.Contains(T.Obstacle))
                { Selected.Add(T.Obstacle); AuditVillageStarts.Add(C->GetActorTransform()); }
            }
        }
        Check(AuditVillageStarts.Num()>0,TEXT("eligible existing village obstacles found at user failure positions"));
        UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_VILLAGE_CANDIDATES count=%d"),AuditVillageStarts.Num());
        AuditStage=2; AuditAt=Now;
    }
    if (AuditStage==2 && Now-AuditAt>.5f)
    {
        if (!AuditVillageStarts.IsValidIndex(AuditCase))
        {
            UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_VILLAGE_RESULT cases=%d failures=%d"),AuditCase,AuditFailures);
            bRuntimeAudit=false; PC->ConsoleCommand(TEXT("quit")); return;
        }
        C->GetCharacterMovement()->StopMovementImmediately(); C->SetActorTransform(AuditVillageStarts[AuditCase]);
        C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        PC->SetControlRotation(C->GetActorRotation());
        AuditAmmo=C->MagazineAmmo; AuditFrame=0;
        FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("case_%d_before.png"),AuditCase),false,false);
        AuditStage=3; AuditAt=Now; return;
    }
    if (AuditStage==3 && Now-AuditAt>.15f)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Pressed,1));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::SpaceBar,IE_Released,0));
        AuditStage=4; AuditAt=Now; return;
    }
    if (AuditStage==4)
    {
        Check(bTraversing,TEXT("space tap enters traversal on existing village geometry"));
        AuditStage=5;
    }
    if (AuditStage==5)
    {
        if (Now-AuditCaptureAt>.033f)
        {
            AuditCaptureAt=Now;
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("case_%d_frame_%04d.png"),AuditCase,AuditFrame++),false,false);
        }
        if (!bTraversing || Now-AuditAt>5.f)
        {
            Check(!bTraversing && bLastTraversalSucceeded && C->GetCharacterMovement()->IsMovingOnGround() &&
                LastExitLocation.Equals(LastJumpTarget.Destination,5.f),TEXT("capsule reaches live supported village destination"));
            Check(C->MagazineAmmo==AuditAmmo && C->GetCharacterMovement()->MovementMode!=MOVE_None,TEXT("ammunition preserved and movement restored"));
            ++AuditCase; AuditStage=2; AuditAt=Now;
        }
    }
}
