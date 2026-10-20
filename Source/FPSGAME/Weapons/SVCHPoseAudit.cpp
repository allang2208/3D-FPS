// Opt-in SVCH check: isolated save, real input/animation, measured physical sights.
#include "../FPSGAMECharacter.h"
#include "FPSGunplayAnimInstance.h"
#include "SVCHWeaponAssets.h"
#include "WeaponGripProfile.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "SkeletalRenderPublic.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace SVCHPoseAudit
{
struct FRun
{
    int32 Phase=0,Frame=0,SteadyADS=0,InspectionTwistSamples=0;
    double PhaseStart=0,NextCapture=0,MaxRoll=0,MaxSightPixels=0,MaxRightWristCorrective=0,MaxInspectionTwistMismatch=0;
    bool Done=false,ProfileObserved=false,NormalReload=false,EmptyReload=false;
    int32 NativeNormalSamples=0,NativeEmptySamples=0;
    FString Directory;
} Run;
TArray<TSharedPtr<FJsonValue>> V(const FVector& P)
{
    return {MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};
}
void Write(const TSharedRef<FJsonObject>& Row,const FString& File,bool Append=false)
{
    FString Text;FJsonSerializer::Serialize(Row,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text+TEXT("\n"),*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),Append?FILEWRITE_Append:0);
}
void End(bool Success,const FString& Reason)
{
    Run.Done=true;auto Row=MakeShared<FJsonObject>();Row->SetBoolField(TEXT("completed"),Success);Row->SetStringField(TEXT("reason"),Reason);
    Row->SetNumberField(TEXT("requested_frames"),Run.Frame);Row->SetNumberField(TEXT("steady_ads_samples"),Run.SteadyADS);
    Row->SetNumberField(TEXT("max_ads_roll_deg"),Run.MaxRoll);Row->SetNumberField(TEXT("max_sight_error_px"),Run.MaxSightPixels);
    Row->SetBoolField(TEXT("profile_observed"),Run.ProfileObserved);Row->SetBoolField(TEXT("normal_reload_completed"),Run.NormalReload);
    Row->SetBoolField(TEXT("empty_reload_completed"),Run.EmptyReload);
    Row->SetNumberField(TEXT("native_v9_normal_samples"),Run.NativeNormalSamples);
    Row->SetNumberField(TEXT("native_v9_empty_samples"),Run.NativeEmptySamples);
    Row->SetNumberField(TEXT("max_right_wrist_corrective"),Run.MaxRightWristCorrective);
    Row->SetNumberField(TEXT("inspection_twist_samples"),Run.InspectionTwistSamples);
    Row->SetNumberField(TEXT("max_inspection_twist_mismatch_deg"),Run.MaxInspectionTwistMismatch);
    Write(Row,Run.Directory/TEXT("completion.json"));
    UE_LOG(LogTemp,Display,TEXT("SVCH_POSE_AUDIT_COMPLETE success=%d frames=%d reason=%s"),Success,Run.Frame,*Reason);
    FPlatformMisc::RequestExitWithStatus(false,Success?0:1);
}
bool Fixture(UColdSteelStatusModel* Profile,int32 Magazine)
{
    auto State=Profile->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);State.ActiveWeaponSlot=6;
    auto Gun=Profile->CreateItem(SVCHWeaponAssets::Definition);Gun.Place=1;Gun.Cell=6;Gun.Magazine=Magazine;State.Items.Add(Gun);
    Profile->AddAmmoToState(State,SVCHWeaponAssets::ItemAmmoId,40);
    return Profile->CommitState(State);
}
bool NativeV9Ready(AFPSGAMECharacter* Character)
{
    TArray<USkeletalMeshComponent*> Parts;Character->GetComponents(Parts);
    for(auto* Part:Parts)
        if(Part->IsVisible()&&GetPathNameSafe(Part->GetSkeletalMeshAsset())==TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7.SK_SVD_BareArmsV7"))return true;
    return false;
}
void Tick(UWorld* World,ELevelTick,float)
{
    if(Run.Done||!World)return;
    auto* PC=World->GetFirstPlayerController();auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    static int32 DiagnosticTicks=0;
    if(DiagnosticTicks++<3)UE_LOG(LogTemp,Display,TEXT("SVCH_POSE_WORLD type=%d world=%s pawn=%s time=%.3f"),int32(World->WorldType),*GetNameSafe(World),*GetNameSafe(PC?PC->GetPawn():nullptr),World->GetTimeSeconds());
    if(World->WorldType!=EWorldType::Game)return;
    if(!C||World->GetTimeSeconds()<3.f)return;
    auto* Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    static bool ProfileReported=false;
    if(!ProfileReported){ProfileReported=true;UE_LOG(LogTemp,Display,TEXT("SVCH_POSE_PROFILE object=%s audit=%d slot=%s"),*GetNameSafe(Profile),Profile&&Profile->IsAudit(),Profile?*Profile->ProfileSlot():TEXT("none"));}
    if(!Profile||!Profile->IsAudit()||!Profile->ProfileSlot().Contains(TEXT("SVCHPoseAudit")))return;
    const double Now=World->GetTimeSeconds();
    if(Run.Directory.IsEmpty())
    {
        FString Label;FParse::Value(FCommandLine::Get(),TEXT("GunplayLabel="),Label);
        Run.Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("SVCHPoseAudit")/FPaths::MakeValidFileName(Label));
        IFileManager::Get().MakeDirectory(*(Run.Directory/TEXT("Frames")),true);
        // Only the isolated capture world receives this neutral inspection rig.
        if(FParse::Param(FCommandLine::Get(),TEXT("SVCHPoseAuditStudio")))
        {
            auto* Fill=World->SpawnActor<ADirectionalLight>();
            Fill->GetLightComponent()->SetMobility(EComponentMobility::Movable);
            Fill->SetActorRotation(FRotator(-25,0,0));
            Fill->GetLightComponent()->SetIntensity(3.f);
            Fill->GetLightComponent()->SetCastShadows(false);
            auto* Neutral=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
            if(Neutral)for(TActorIterator<AStaticMeshActor> It(World);It;++It)
                for(int32 Slot=0;Slot<It->GetStaticMeshComponent()->GetNumMaterials();++Slot)It->GetStaticMeshComponent()->SetMaterial(Slot,Neutral);
        }
    }
    if(Now>100){End(false,TEXT("Stage timeout"));return;}
    const auto Key=[&](const FKey& K,EInputEvent Event){PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Event,Event==IE_Released?0.f:1.f));};
    const auto Next=[&](int32 Phase){Run.Phase=Phase;Run.PhaseStart=Now;Run.NextCapture=Now;};
    const double T=Now-Run.PhaseStart;
    switch(Run.Phase)
    {
    case 0:if(!Fixture(Profile,5)){End(false,TEXT("Initial fixture rejected"));return;}Next(1);break;
    case 1:if(T>5&&NativeV9Ready(C))Next(2);break;
    case 2:if(T>1.5){Key(EKeys::RightMouseButton,IE_Pressed);Next(3);}break;
    case 3:if(T>(FParse::Param(FCommandLine::Get(),TEXT("SVCHSightsOnly"))?3.:2.)){Key(EKeys::RightMouseButton,IE_Released);Next(4);}break;
    case 4:if(T>1)
        {
            if(FParse::Param(FCommandLine::Get(),TEXT("SVCHBoltFitReview")))
            {
                if(!Fixture(Profile,0)){End(false,TEXT("Empty fixture rejected"));return;}Next(6);break;
            }
            if(FParse::Param(FCommandLine::Get(),TEXT("SVCHSightsOnly")))
            {
                End(Run.SteadyADS>=4&&Run.ProfileObserved&&Run.MaxRoll<1.0&&Run.MaxSightPixels<5.0,
                    TEXT("Scoped hip/ADS sight capture; reload and inspection were not run"));return;
            }
            Key(EKeys::R,IE_Pressed);Key(EKeys::R,IE_Released);Next(5);
        }break;
    case 5:if(T>6&&!C->IsReloading())
        {Run.NormalReload=C->GetMagazineAmmo()==10;if(!Fixture(Profile,0)){End(false,TEXT("Empty fixture rejected"));return;}Next(6);}break;
    case 6:if(T>5&&NativeV9Ready(C)){Key(EKeys::R,IE_Pressed);Key(EKeys::R,IE_Released);Next(7);}break;
    case 7:if(T>8&&!C->IsReloading())
        {
            Run.EmptyReload=C->GetMagazineAmmo()==10;
            if(FParse::Param(FCommandLine::Get(),TEXT("SVCHBoltFitReview"))){Next(12);break;}
            if(FParse::Param(FCommandLine::Get(),TEXT("SVCHReloadOnly")))
            {
                End(Run.ProfileObserved&&Run.NormalReload&&Run.EmptyReload&&Run.NativeNormalSamples>=10&&Run.NativeEmptySamples>=10,
                    TEXT("Both reloads captured after native V9 readiness; visual/contact review is separate"));return;
            }
            Key(EKeys::RightMouseButton,IE_Pressed);Next(8);
        }break;
    case 8:if(T>2){Key(EKeys::RightMouseButton,IE_Released);Next(9);}break;
    case 9:if(T>1){Key(EKeys::L,IE_Pressed);Key(EKeys::L,IE_Released);Next(10);}break;
    case 10:if(T>7)Next(11);break;
    case 11:if(T>1)
        {End(Run.SteadyADS>=6&&Run.ProfileObserved&&Run.NormalReload&&Run.EmptyReload&&Run.MaxRoll<1.0&&Run.MaxSightPixels<5.0&&Run.InspectionTwistSamples>=3&&Run.MaxInspectionTwistMismatch<1.0,
            TEXT("Captured hip, ADS, both reloads, ADS return and inspection; visual review is separate"));return;}break;
    case 12:if(T>1.5)
        {End(Run.SteadyADS>=4&&Run.ProfileObserved&&Run.EmptyReload&&Run.NativeEmptySamples>=10&&Run.MaxRoll<1.0&&Run.MaxSightPixels<5.0,
            TEXT("Scoped sights, corrected bolt contact and empty-reload return; source clips and V9 unchanged"));return;}break;
    }
    if(Run.Phase!=2&&Run.Phase!=3&&Run.Phase!=5&&Run.Phase!=7&&Run.Phase!=8&&Run.Phase!=10&&Run.Phase!=11&&Run.Phase!=12)return;
    TArray<USkeletalMeshComponent*> Components;C->GetComponents(Components);USkeletalMeshComponent* Mesh=nullptr;
    for(auto* Part:Components)if(Part->GetFName()==TEXT("AKMViewmodel"))Mesh=Part;
    if(!Mesh||GetPathNameSafe(Mesh->GetSkeletalMeshAsset())!=SVCHWeaponAssets::MeshPath){End(false,TEXT("Current SVCH mesh not active"));return;}
    auto* Camera=C->FindComponentByClass<UCameraComponent>();auto* Anim=Cast<UFPSGunplayAnimInstance>(Mesh->GetAnimInstance());
    if(!Camera||!Anim||!PC->PlayerCameraManager){End(false,TEXT("Camera or native animation missing"));return;}
    if((Run.Phase==5||Run.Phase==7)&&FParse::Param(FCommandLine::Get(),TEXT("SVCHHandoffReview")))
    {
        const FTransform View(PC->PlayerCameraManager->GetCameraRotation(),PC->PlayerCameraManager->GetCameraLocation());
        const FTransform Component=Mesh->GetComponentTransform().GetRelativeTransform(View);
        const FTransform Root=Mesh->GetSocketTransform(TEXT("WPN_root")).GetRelativeTransform(View);
        auto Sample=MakeShared<FJsonObject>();Sample->SetNumberField(TEXT("time"),Now);
        Sample->SetStringField(TEXT("stage"),Run.Phase==5?TEXT("normal"):TEXT("empty"));
        Sample->SetNumberField(TEXT("source_time"),Anim->ActionTime);Sample->SetNumberField(TEXT("action_alpha"),Anim->ActionAlpha);
        Sample->SetBoolField(TEXT("reloading"),C->IsReloading());
        Sample->SetArrayField(TEXT("component_location"),V(Component.GetLocation()));
        Sample->SetArrayField(TEXT("component_rotation"),V(Component.Rotator().Euler()));
        Sample->SetArrayField(TEXT("root_location"),V(Root.GetLocation()));
        Sample->SetArrayField(TEXT("root_rotation"),V(Root.Rotator().Euler()));
        const auto Bone=[&](const TCHAR* Name){const auto T=Mesh->GetSocketTransform(Name);auto B=MakeShared<FJsonObject>();
            B->SetArrayField(TEXT("p"),V(T.GetLocation()));const FQuat Q=T.GetRotation();
            B->SetArrayField(TEXT("q"),{MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z),MakeShared<FJsonValueNumber>(Q.W)});return B;};
        Sample->SetObjectField(TEXT("hand_r"),Bone(TEXT("hand_r")));Sample->SetObjectField(TEXT("bolt"),Bone(TEXT("WPN_bolt")));
        Write(Sample,Run.Directory/TEXT("handoff.jsonl"),true);
    }
    if(Now<Run.NextCapture||FScreenshotRequest::IsScreenshotRequested())return;
    Run.NextCapture=Now+(FParse::Param(FCommandLine::Get(),TEXT("SVCHSightsOnly"))&&(Run.Phase==2||Run.Phase==3)?.33:.125);
    if(Run.Frame==0&&FParse::Param(FCommandLine::Get(),TEXT("SVCHSightsOnly")))
    {
        auto Assembly=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Entries;
        TArray<UMeshComponent*> Parts;C->GetComponents(Parts);
        for(auto* Part:Parts)
        {
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Part->GetName());
            Row->SetBoolField(TEXT("visible"),Part->IsVisible());Row->SetBoolField(TEXT("hidden_in_game"),Part->bHiddenInGame);
            Row->SetStringField(TEXT("parent"),GetNameSafe(Part->GetAttachParent()));Row->SetStringField(TEXT("socket"),Part->GetAttachSocketName().ToString());
            if(auto* Static=Cast<UStaticMeshComponent>(Part))Row->SetStringField(TEXT("asset"),GetPathNameSafe(Static->GetStaticMesh()));
            if(auto* Skinned=Cast<USkeletalMeshComponent>(Part))Row->SetStringField(TEXT("asset"),GetPathNameSafe(Skinned->GetSkeletalMeshAsset()));
            Row->SetStringField(TEXT("relative_transform"),Part->GetRelativeTransform().ToString());Entries.Add(MakeShared<FJsonValueObject>(Row));
        }
        Assembly->SetArrayField(TEXT("components"),Entries);Write(Assembly,Run.Directory/TEXT("assembly.json"));
        // Compare posed gun vertices in its bind frame to locate the raised rail fragment.
        TArray<FFinalSkinVertex> Skinned;Mesh->GetCPUSkinnedVertices(Skinned,0);
        const auto* Asset=Mesh->GetSkeletalMeshAsset();const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];
        const auto& Ref=Asset->GetRefSkeleton();FTransform Bind=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bind=Bind*Ref.GetRefBonePose()[I];
        const FTransform Pose=Mesh->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
        auto Geometry=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Moved;
        const auto* Weights=Mesh->GetSkinWeightBuffer(0);
        for(const auto& Section:LOD.RenderSections)
        {
            const FString Material=Asset->GetMaterials()[Section.MaterialIndex].MaterialSlotName.ToString();
            if(Material.StartsWith(TEXT("MI_Manny_")))continue;
            for(uint32 I=Section.BaseVertexIndex;I<Section.BaseVertexIndex+Section.NumVertices&&I<uint32(Skinned.Num());++I)
            {
                const FVector Rest(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(I));
                const FVector Posed=Bind.TransformPosition(Pose.InverseTransformPosition(FVector(Skinned[I].Position)));
                if(FVector::Dist(Rest,Posed)<.05)continue;
                auto Vertex=MakeShared<FJsonObject>();Vertex->SetArrayField(TEXT("rest"),V(Rest));Vertex->SetArrayField(TEXT("posed_bind"),V(Posed));
                Vertex->SetStringField(TEXT("material"),Material);
                if(Weights)Vertex->SetStringField(TEXT("bone"),Ref.GetBoneName(Section.BoneMap[Weights->GetBoneIndex(I,0)]).ToString());
                Moved.Add(MakeShared<FJsonValueObject>(Vertex));
            }
        }
        Geometry->SetArrayField(TEXT("moved_gun_vertices"),Moved);Write(Geometry,Run.Directory/TEXT("posed_geometry.json"));
    }
    const FString Stage=Run.Phase==2?TEXT("hip"):Run.Phase==3?TEXT("ads"):Run.Phase==5?TEXT("reload_normal"):Run.Phase==7?TEXT("reload_empty"):Run.Phase==10?TEXT("inspect"):(Run.Phase==11||Run.Phase==12)?TEXT("hip_return"):TEXT("ads_return");
    const FString Image=FString::Printf(TEXT("%s_%05d.png"),*Stage,Run.Frame++);
    FScreenshotRequest::RequestScreenshot(Run.Directory/TEXT("Frames")/Image,false,false);
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),Image);Row->SetStringField(TEXT("stage"),Stage);
    Row->SetNumberField(TEXT("time"),Now);Row->SetNumberField(TEXT("stage_time"),Now-Run.PhaseStart);Row->SetNumberField(TEXT("ammo"),C->GetMagazineAmmo());
    Row->SetNumberField(TEXT("weapon_state"),int32(C->GetWeaponState()));Row->SetNumberField(TEXT("aim_alpha"),Anim->AimAlpha);
    Row->SetNumberField(TEXT("action_alpha"),Anim->ActionAlpha);Row->SetNumberField(TEXT("action_time"),Anim->ActionTime);
    Row->SetStringField(TEXT("action"),GetPathNameSafe(Anim->ActionClip));Row->SetStringField(TEXT("idle"),GetPathNameSafe(Anim->IdleClip));
    Row->SetStringField(TEXT("mesh"),GetPathNameSafe(Mesh->GetSkeletalMeshAsset()));Row->SetStringField(TEXT("grip_profile"),GetPathNameSafe(Anim->GripProfile));
    Row->SetStringField(TEXT("action_grip_profile"),GetPathNameSafe(Anim->ActionGripProfile));
    const bool bNativeReady=NativeV9Ready(C);Row->SetBoolField(TEXT("native_v9_ready"),bNativeReady);
    if(bNativeReady&&Anim->ActionAlpha>.99f)
    {
        if(Run.Phase==5)++Run.NativeNormalSamples;
        if(Run.Phase==7)++Run.NativeEmptySamples;
    }
    Run.ProfileObserved|=GetPathNameSafe(Anim->GripProfile)==SVCHWeaponAssets::ProfilePath;
    const FTransform View(PC->PlayerCameraManager->GetCameraRotation(),PC->PlayerCameraManager->GetCameraLocation());
    const FTransform Root=Mesh->GetSocketTransform(TEXT("WPN_root"));
    const FVector Rear=Root.TransformPosition(SVCHWeaponAssets::RearSight),Front=Root.TransformPosition(SVCHWeaponAssets::FrontSight);
    const FVector Up=View.InverseTransformVectorNoScale(Root.TransformVectorNoScale(SVCHWeaponAssets::SightUp)).GetSafeNormal();
    const double Roll=FMath::RadiansToDegrees(FMath::Atan2(Up.Y,Up.Z));
    int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);double Error=0;
    for(const FVector Point:{Rear,Front}){FVector2D Pixel;if(PC->ProjectWorldLocationToScreen(Point,Pixel))Error=FMath::Max(Error,(Pixel-FVector2D(Width*.5,Height*.5)).Size());else Error=1e9;}
    Row->SetArrayField(TEXT("rear_camera_cm"),V(View.InverseTransformPosition(Rear)));Row->SetArrayField(TEXT("front_camera_cm"),V(View.InverseTransformPosition(Front)));
    Row->SetNumberField(TEXT("roll_deg"),Roll);Row->SetNumberField(TEXT("sight_error_px"),Error);
    Row->SetArrayField(TEXT("camera"),V(View.GetLocation()));Row->SetNumberField(TEXT("fov"),PC->PlayerCameraManager->GetFOVAngle());
    if((Run.Phase==3||Run.Phase==8)&&T>1&&Anim->AimAlpha>.99)
        {++Run.SteadyADS;Run.MaxRoll=FMath::Max(Run.MaxRoll,FMath::Abs(Roll));Run.MaxSightPixels=FMath::Max(Run.MaxSightPixels,Error);}
    auto Bones=MakeShared<FJsonObject>();
    for(const FName Name:{FName("upperarm_l"),FName("lowerarm_l"),FName("hand_l"),FName("hand_r"),FName("index_03_r"),FName("middle_03_r"),FName("ring_03_r"),FName("pinky_03_r"),FName("WPN_SOCKET_Magazine"),FName("WPN_bolt")})
        Bones->SetArrayField(Name.ToString(),V(Root.InverseTransformPosition(Mesh->GetSocketLocation(Name))*100.));
    Row->SetObjectField(TEXT("root_space_bones_cm"),Bones);
    TArray<TSharedPtr<FJsonValue>> Parts;
    for(auto* Part:Components)if(Part->IsVisible()&&Part->GetSkeletalMeshAsset())
    {auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("name"),Part->GetName());Item->SetStringField(TEXT("asset"),Part->GetSkeletalMeshAsset()->GetPathName());Parts.Add(MakeShared<FJsonValueObject>(Item));}
    Row->SetArrayField(TEXT("visible_components"),Parts);
    // These donor morphs are part of the arm surface, not optional attachments.
    auto Correctives=MakeShared<FJsonObject>();
    for(const FName Name:{FName("JC_WristFlexA_R"),FName("JC_WristFlexB_R"),FName("JC_WristRadial_R"),FName("JC_WristUlnar_R")})
    {
        const float Weight=Mesh->GetMorphTarget(Name);Correctives->SetNumberField(Name.ToString(),Weight);
        Run.MaxRightWristCorrective=FMath::Max(Run.MaxRightWristCorrective,double(Weight));
    }
    Row->SetObjectField(TEXT("right_wrist_correctives"),Correctives);
    if(Run.Phase==10)
    {
        const FReferenceSkeleton& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
        TArray<FTransform> Reference=Ref.GetRefBonePose();
        for(int32 I=0;I<Reference.Num();++I)if(const int32 Parent=Ref.GetParentIndex(I);Parent!=INDEX_NONE)Reference[I]=Reference[I]*Reference[Parent];
        const int32 Lower=Ref.FindBoneIndex(TEXT("lowerarm_r")),Hand=Ref.FindBoneIndex(TEXT("hand_r")),Twist=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_r"));
        const FVector Axis=Reference[Lower].GetRotation().UnrotateVector(Reference[Hand].GetLocation()-Reference[Lower].GetLocation()).GetSafeNormal();
        const FQuat LowerPose=Mesh->GetSocketTransform(TEXT("lowerarm_r")).GetRotation();
        const auto RelativeRoll=[&](int32 Index,const FName Name)
        {
            const FQuat Rest=Reference[Lower].GetRotation().Inverse()*Reference[Index].GetRotation();
            FQuat Q=LowerPose.Inverse()*Mesh->GetSocketTransform(Name).GetRotation()*Rest.Inverse();
            if(Q.W<0)Q=FQuat(-Q.X,-Q.Y,-Q.Z,-Q.W);
            return FMath::RadiansToDegrees(2.0*FMath::Atan2(FVector(Q.X,Q.Y,Q.Z)|Axis,Q.W));
        };
        const double HandRoll=RelativeRoll(Hand,TEXT("hand_r")),TwistRoll=RelativeRoll(Twist,TEXT("lowerarm_twist_01_r"));
        const double Mismatch=FMath::Abs(FMath::UnwindDegrees(HandRoll-TwistRoll));
        Row->SetNumberField(TEXT("right_hand_roll_deg"),HandRoll);Row->SetNumberField(TEXT("right_twist01_roll_deg"),TwistRoll);
        Row->SetNumberField(TEXT("right_twist_mismatch_deg"),Mismatch);
        if(Anim->ActionTime>2.75f&&Anim->ActionTime<4.25f&&Anim->ActionAlpha>.99f)
        {++Run.InspectionTwistSamples;Run.MaxInspectionTwistMismatch=FMath::Max(Run.MaxInspectionTwistMismatch,Mismatch);}
    }
    Write(Row,Run.Directory/TEXT("frames.jsonl"),true);
}
struct FRegister
{
    FRegister(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){if(FParse::Param(FCommandLine::Get(),TEXT("SVCHPoseAudit")))
        {UE_LOG(LogTemp,Display,TEXT("SVCH_POSE_AUDIT_REGISTERED"));FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);}});}
} Register;
}
