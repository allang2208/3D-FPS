#include "WeaponEquipCameraAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "M249Attachments.h"
#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

// Explicit follow-up only. No production inputs or saved player profiles change.
int32 UWeaponEquipCameraAuditCommandlet::RunM249WristReview(const FString& Params)
{
    FString Output; if(!FParse::Value(*Params,TEXT("Out="),Output))return 2;
    IFileManager::Get().MakeDirectory(*Output,true);
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(TEXT("WeaponEquipCameraAudit -ColdSteelProfile=M249WristAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    if(auto* V=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.body.AsyncPreload")))V->Set(0,ECVF_SetByCode);
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("M249WristReview"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 3;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    auto* Local=NewObject<ULocalPlayer>(GEngine);GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));PC->SetPlayer(Local);
    Pawn->DispatchBeginPlay();Model->AttachPawn(Pawn);Pawn->FirstPersonCamera->Activate(true);
    Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_None);Pawn->bWasGrounded=false;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto Present=[&](float Dt)
    {
        ++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,Dt);
        Pawn->UpdateWeaponState(Dt);Pawn->UpdateWeaponFeedback(Dt);Pawn->UpdateCamera(Dt);
        Pawn->UpdateViewmodel(Dt);Pawn->UpdateActionPose(Dt);
        Pawn->AKMViewmodel->TickAnimation(Dt,false);Pawn->AKMViewmodel->RefreshBoneTransforms();
        if(auto* C=Pawn->FindComponentByClass<UFPSArmJointCorrectiveComponent>())C->TickComponent(Dt,LEVELTICK_All,nullptr);
        Body->TickComponent(Dt,LEVELTICK_All,nullptr);
        if(auto* Mesh=Body->GetBodyMesh()){Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();}
    };
    const TCHAR* Variants[]={TEXT("false"),TEXT("vertical_foregrip"),TEXT("tactical_vertical_foregrip"),TEXT("angled_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")};
    TArray<TSharedPtr<FJsonValue>> Results;int32 Failures=0;
    for(const TCHAR* Variant:Variants)for(bool Empty:{false,true})for(int32 FPS:{30,60,120,0})
    {
        Pawn->AimReleased();auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
        auto W=Model->CreateItem(TEXT("ue_m249"));W.Place=1;W.Cell=6;W.Magazine=Empty?0:50;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(W.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("underbarrel"),Variant);Parts->SetStringField(TEXT("magazine"),TEXT("false"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);W.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&W.Data));
        Seed.Items.Add(W);auto Ammo=Model->CreateItem(TEXT("ammo_556"),200);Ammo.Place=0;Ammo.Cell=0;Seed.Items.Add(Ammo);
        bool Passed=Model->CommitState(Seed);
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
#endif
        for(int32 I=0;I<180;++I)Present(1.f/60.f);
        auto* Anim=Pawn->GunplayAnimation.Get();auto* Mesh=Pawn->AKMViewmodel.Get();
        const FString Family=M249Attachments::ForegripFamily(Variant),Expected=M249Attachments::ProfilePath(FName(Family));
        Passed&=Anim&&Anim->GripProfile&&Anim->GripProfile->GetPathName().StartsWith(Expected+TEXT("."))&&!Pawn->HasM249SideMagazine();
        const auto Rig=Mesh->GetSocketTransform(TEXT("WPN_root"));
        const auto Held=Mesh->GetSocketTransform(TEXT("hand_l")).GetRelativeTransform(Rig);
        double MaxHeldError=0,MaxHeldAngle=0,Boundary=0;bool Finite=true,Started=false,Ended=false,MirrorStable=true;
        TArray<float> Poses;TArray<TSharedPtr<FJsonValue>> Samples;int32 Frame=0;float Time=0;
        FTransform Previous=Mesh->GetSocketTransform(TEXT("hand_l"),RTS_Component);
        auto SaveFrame=[&](float Dt,int32 Phase)
        {
            const FTransform Root=Mesh->GetSocketTransform(TEXT("WPN_root"));
            const FTransform Hand=Mesh->GetSocketTransform(TEXT("hand_l")).GetRelativeTransform(Root);
            if(Phase<2||Phase==3){MaxHeldError=FMath::Max(MaxHeldError,FVector::Dist(Hand.GetLocation(),Held.GetLocation()));MaxHeldAngle=FMath::Max(MaxHeldAngle,FMath::RadiansToDegrees(Hand.GetRotation().AngularDistance(Held.GetRotation())));}
            const auto& Bones=Mesh->GetComponentSpaceTransforms();for(const auto& Bone:Bones)Finite&=!Bone.ContainsNaN();
            if(FPS==60)
            {
                Poses.Append({Time,float(Phase),Pawn->WeaponADSFactor,Anim->ActionTime,Anim->ActionAlpha,Anim->ArmIdleHandoffAlpha});
                for(const FTransform& T:Bones){const auto P=T.GetLocation();const auto Q=T.GetRotation();for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W})Poses.Add(X);}
                for(const FTransform& T:{Mesh->GetComponentTransform(),Pawn->FirstPersonCamera->GetComponentTransform()})
                {const auto P=T.GetLocation();const auto Q=T.GetRotation();for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W})Poses.Add(X);}
            }
            Time+=Dt;Previous=Mesh->GetSocketTransform(TEXT("hand_l"),RTS_Component);
        };
        auto Step=[&](int32 Phase){const float Dt=FPS?1.f/FPS:(Frame%11==4?.12f:1.f/90.f);++Frame;Present(Dt);SaveFrame(Dt,Phase);return Dt;};
        for(float T=0;T<.4f;)T+=Step(0);
        Pawn->AimPressed();for(float T=0;T<.8f;)T+=Step(1);
        Passed&=Pawn->WeaponADSFactor>.99f;
        Pawn->ReloadPressed();Started=Pawn->IsReloading();Passed&=Started&&Pawn->bPendingEmptyReload==Empty;
        for(float T=0;T<18.f;)
        {
            const bool Was=Pawn->IsReloading();const FTransform Before=Mesh->GetSocketTransform(TEXT("hand_l"),RTS_Component);
            T+=Step(2);
            if(Was&&!Pawn->IsReloading()){Boundary=FVector::Dist(Before.GetLocation(),Previous.GetLocation());Ended=true;break;}
        }
        Pawn->AimReleased();for(float T=0;T<.6f;)T+=Step(3);
        Pawn->AimPressed();for(float T=0;T<.6f;)T+=Step(3);
        const auto OldStart=Pawn->WeaponActionStartedAt;Model->AdoptNetMirror(Model->Snapshot(),true);Pawn->ApplyColdSteelProfile(Model);
        MirrorStable=Pawn->WeaponActionStartedAt==OldStart;
        Pawn->AimReleased();for(float T=0;T<.6f;)T+=Step(3);
        const bool Equipment=Body->LocalWeapons.Num()==1&&Body->LocalWeapons[0].GripProfile.ToSoftObjectPath().GetLongPackageName()==Expected;
        Passed&=Finite&&Started&&Ended&&MirrorStable&&Equipment&&MaxHeldError<.02&&MaxHeldAngle<.05&&Boundary<.3;
        const FString Name=Family+(FString(Variant).Contains(TEXT("tactical"))?TEXT("_tactical"):TEXT(""))+(Empty?TEXT("_empty"):TEXT("_normal"))+FString::Printf(TEXT("_%d"),FPS);
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Passed);
        Row->SetBoolField(TEXT("finite"),Finite);Row->SetBoolField(TEXT("reload_started"),Started);Row->SetBoolField(TEXT("reload_ended"),Ended);
        Row->SetBoolField(TEXT("mirror_stable"),MirrorStable);Row->SetBoolField(TEXT("body_profile_matches"),Equipment);
        Row->SetNumberField(TEXT("held_drift_cm"),MaxHeldError);Row->SetNumberField(TEXT("held_rotation_deg"),MaxHeldAngle);Row->SetNumberField(TEXT("return_boundary_cm"),Boundary);
        Row->SetStringField(TEXT("profile"),GetPathNameSafe(Anim->GripProfile));Row->SetNumberField(TEXT("bone_count"),Mesh->GetNumBones());
        if(FPS==60)
        {
            TArray<uint8> Bytes;Bytes.Append(reinterpret_cast<const uint8*>(Poses.GetData()),Poses.Num()*sizeof(float));
            FFileHelper::SaveArrayToFile(Bytes,*(Output/Name+TEXT(".f32")));
        }
        Results.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Passed;
        UE_LOG(LogTemp,Display,TEXT("M249_WRIST_NATIVE %s pass=%d started=%d ended=%d held=%.5f/%.5f return=%.5f body=%d"),*Name,Passed,Started,Ended,MaxHeldError,MaxHeldAngle,Boundary,Equipment);
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Results);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("asset_writes"),false);Report->SetBoolField(TEXT("network_transport"),false);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Output/TEXT("receipt.json")));
    Pawn->EndPlay(EEndPlayReason::Quit);GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
