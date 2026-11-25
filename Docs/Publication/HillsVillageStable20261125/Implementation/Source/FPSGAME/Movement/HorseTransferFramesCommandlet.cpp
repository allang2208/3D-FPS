#include "HorseTransferFramesCommandlet.h"
#include "HorseRiderComponent.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "UObject/SavePackage.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#endif

#if WITH_EDITOR
namespace
{
    bool SaveTransferClip(const FString& Package,USkeletalMesh& Mesh,const TArray<TArray<FTransform>>& Frames)
    {
        auto* Outer=FPackageName::DoesPackageExist(Package)?LoadPackage(nullptr,*Package,LOAD_None):CreatePackage(*Package);
        if(!Outer)return false;
        Outer->FullyLoad();
        const FName Name(*FPackageName::GetLongPackageAssetName(Package));
        auto* Clip=FindObject<UAnimSequence>(Outer,*Name.ToString());
        const bool NewClip=!Clip;
        if(NewClip)Clip=NewObject<UAnimSequence>(Outer,Name,RF_Public|RF_Standalone);
        Clip->SetSkeleton(Mesh.GetSkeleton());
        // These keys are already in this body's proportions, including its pelvis height.
        Clip->SetRetargetSourceAsset(&Mesh);
        Clip->UpdateRetargetSourceAssetData();
        Clip->bEnableRootMotion=false;
        auto& C=Clip->GetController();
        C.OpenBracket(FText::FromString(TEXT("Bake fixed saddle transfer")),false);
        C.InitializeModel();
        C.RemoveAllBoneTracks(false);
        C.SetFrameRate(FFrameRate(60,1),false);
        C.SetNumberOfFrames(FFrameNumber(Frames.Num()-1),false);
        const auto& Ref=Mesh.GetRefSkeleton();
        bool Valid=true;
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            const FTransform& Bind=Ref.GetRefBonePose()[I];
            TArray<FVector> Positions,Scales;
            TArray<FQuat> Rotations;
            bool Varies=false;
            for(const auto& Frame:Frames)
            {
                const FTransform& Local=Frame[I];
                Varies|=!Local.Equals(Bind,.0001f);
                Positions.Add(Local.GetLocation());Scales.Add(Local.GetScale3D());
                FQuat Rot=Local.GetRotation().GetNormalized();
                if(!Rotations.IsEmpty())Rot.EnforceShortestArcWith(Rotations.Last());
                Rotations.Add(Rot);
            }
            if(Varies)
            {
                const FName Bone=Ref.GetBoneName(I);
                Valid&=C.AddBoneCurve(Bone,false);
                Valid&=C.SetBoneTrackKeys(Bone,Positions,Rotations,Scales,false);
            }
        }
        C.NotifyPopulated();
        C.CloseBracket(false);
        if(!Valid)return false;
        Clip->MarkPackageDirty();
        if(NewClip)FAssetRegistryModule::AssetCreated(Clip);
        FAssetCompilingManager::Get().FinishAllCompilation();
        const FString File=FPackageName::LongPackageNameToFilename(Package,FPackageName::GetAssetPackageExtension());
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
        FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;
        return UPackage::SavePackage(Outer,Clip,*File,Args);
    }
    // Optional mesh samples use precisely the rider pose being measured, including the skin weights.
    template<typename T>
    bool SaveTransferBuffer(const FString& File,const TArray<T>& Values)
    {
        return FFileHelper::SaveArrayToFile(MakeArrayView(reinterpret_cast<const uint8*>(Values.GetData()),
            Values.Num()*int32(sizeof(T))),*File);
    }
    bool SaveRiderSurface(const FString& Prefix,USkeletalMeshComponent& Body,const TArray<FTransform>& Pose,bool First)
    {
        const auto* Mesh=Body.GetSkeletalMeshAsset();
        const auto* Skin=Body.GetSkinWeightBuffer(0);
        if(!Mesh || !Skin || !Skin->GetNeedsCPUAccess())return false;
        const auto& LOD=Mesh->GetResourceForRendering()->LODRenderData[0];
        if(First)
        {
            TArray<uint32> Indices;
            LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);
            if(!SaveTransferBuffer(Prefix+TEXT(".indices"),Indices))return false;
        }
        const auto& Inverse=Mesh->GetRefBasesInvMatrix();
        TArray<FMatrix44f> Matrices;
        for(int32 I=0;I<Pose.Num();++I)
            Matrices.Add(Inverse[I]*FMatrix44f((Pose[I]*Body.GetComponentTransform()).ToMatrixWithScale()));
        TArray<FVector3f> Points;
        USkinnedMeshComponent::ComputeSkinnedPositions(&Body,Points,Matrices,LOD,*Skin);
        return SaveTransferBuffer(Prefix+TEXT(".vertices"),Points);
    }
}
#endif

int32 UHorseTransferFramesCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    const bool bRight=FParse::Param(*Params,TEXT("RightSide"));
    const bool Bake=FParse::Param(*Params,TEXT("BakeTransfers"));
    const bool UsePlayerGraph=!Bake && FParse::Param(*Params,TEXT("PlayerGraph"));
    FString Stage;
    if(Bake && (!FParse::Value(*Params,TEXT("StageProject="),Stage) ||
        !FPaths::IsSamePath(FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath()),Stage)))return 9;
    FString Output,Json,Surface;
    FParse::Value(*Params,TEXT("Surface="),Surface);
    FString ClipKey=TEXT("Rifle.Idle");
    FParse::Value(*Params,TEXT("Clip="),ClipKey);
    float GroundYaw=0.f;
    const bool bExplicitYaw=FParse::Value(*Params,TEXT("GroundYaw="),GroundYaw);
    TSharedPtr<FJsonObject> Config;
    if(!FParse::Value(*Params,TEXT("Output="),Output) ||
       !FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))) ||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Config))return 1;
    const FString Folder=TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/");
    const auto LoadHorse=[&](const FString& Name){return Folder+Name+TEXT(".")+FPaths::GetCleanFilename(Name);};
    auto* HorseMesh=LoadObject<USkeletalMesh>(nullptr,*LoadHorse(TEXT("SK_StableWarhorse")));
    auto* Idle=LoadObject<UAnimSequence>(nullptr,*LoadHorse(TEXT("Animations/A_Warhorse_Idle")));
    if(!HorseMesh||!Idle)return 2;
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false);
    if(!World)return 3;
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Horse=World->SpawnActor<AStableRidingHorse>(FVector(0,0,94),FRotator::ZeroRotator,Spawn);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,-150,96),FRotator::ZeroRotator,Spawn);
    if(!Horse||!Pawn)return 4;
    auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>();
    Ride->Player=Pawn;
    auto* Skin=Horse->GetMesh();
    Skin->SetSkeletalMeshAsset(HorseMesh);
    FAssetCompilingManager::Get().FinishAllCompilation();
    Skin->SetRelativeLocationAndRotation(FVector(0,0,-94),FRotator::ZeroRotator);
    const FVector Heading=Skin->GetSocketLocation(TEXT("mouth_socket"))-Skin->GetSocketLocation(TEXT("pelvis"));
    Skin->SetRelativeRotation(FRotator(0,-Heading.Rotation().Yaw,0));
    Skin->PlayAnimation(Idle,true);
    // The production mesh offset is shared by authoring, raw clip and body graph capture.
    auto* Body=NewObject<USkeletalMeshComponent>(Pawn);
    Body->SetupAttachment(Pawn->GetRootComponent());Body->RegisterComponent();
    const float H=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Body->SetRelativeLocationAndRotation(FVector(0,0,-H),FRotator(0,-90,0));
    const TArray<FName> Names={TEXT("pelvis"),TEXT("spine_03"),TEXT("head"),TEXT("thigh_l"),TEXT("calf_l"),TEXT("foot_l"),TEXT("ball_l"),
        TEXT("thigh_r"),TEXT("calf_r"),TEXT("foot_r"),TEXT("ball_r"),TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r")};
    const bool InspectSeat=FParse::Param(*Params,TEXT("SeatedWeapons"));
    FString Csv=InspectSeat?TEXT("body,motion,yaw,frame,upper_degrees,wrist_span_cm,left_tread_cm,right_tread_cm\n"):
        TEXT("body,action,frame,p,bone,x,y,z,qx,qy,qz,qw\n");
    for(FString Id:{FString(TEXT("jason")),FString(TEXT("kaitlin"))})
    {
        const auto Data=Id==TEXT("jason")?Config:Config->GetObjectField(TEXT("body_variants"))->GetObjectField(Id);
        auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Data->GetStringField(TEXT("body_mesh")));
        auto* Equip=LoadObject<UAnimSequence>(nullptr,*Data->GetObjectField(TEXT("clips"))->GetStringField(ClipKey));
        if(!Asset||!Equip)return 5;
        FAssetCompilingManager::Get().FinishAllCompilation();
        Body->SetSkeletalMeshAsset(Asset);Body->PlayAnimation(Equip,true);
        if(InspectSeat)
        {
            Ride->State.Horse=Horse;Ride->State.Phase=ERiderPhase::Seated;
            for(FString Motion:{FString(TEXT("Rifle.Idle")),FString(TEXT("Rifle.Reload")),FString(TEXT("Melee.FullBody.Slash1"))})
            {
                auto* Source=LoadObject<UAnimSequence>(nullptr,*Data->GetObjectField(TEXT("clips"))->GetStringField(Motion));
                if(!Source)return 13;
                UFPSPlayerBodyAnimInstance* Graph=nullptr;
                if(Motion==TEXT("Rifle.Idle"))
                {
                    Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
                    Graph=Cast<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());
                    if(!Graph)return 12;
                    Graph->Clips.Add(TEXT("Rifle.Idle"),Source);Graph->BodyState.Family=TEXT("Rifle");
                    Graph->BodyState.bAiming=true;
                }
                else Body->PlayAnimation(Source,false);
                const auto Bone=[Asset](const TCHAR* Name){return Asset->GetRefSkeleton().FindBoneIndex(FName(Name));};
                const int32 L=Bone(TEXT("hand_l")),R=Bone(TEXT("hand_r")),BL=Bone(TEXT("ball_l")),BR=Bone(TEXT("ball_r"));
                if(FMath::Min(FMath::Min(L,R),FMath::Min(BL,BR))<0)return 6;
                for(float Yaw:{-150.f,-90.f,0.f,90.f,150.f})
                    for(int32 I=0;I<=30;++I)
                    {
                        const float Part=I/30.f;
                        Pawn->SetActorLocationAndRotation(Ride->RiderRoot(1.f),FRotator(0,Yaw,0));
                        if(Graph){Graph->Clock=1.f+Part;Graph->BodyState.AimPitch=(Part-.5f)*80.f;Graph->BodyState.LastShotAt=1.f+FMath::FloorToFloat(Part*4.f)*.25f;}
                        else Body->SetPosition(Part*Source->GetPlayLength(),false);
                        Body->TickAnimation(Graph?1.f/30.f:0.f,false);Body->RefreshBoneTransforms();
                        const auto& Input=Body->GetComponentSpaceTransforms();
                        TArray<FTransform> SeatPose=Input;Ride->ApplyPose(*Body,SeatPose);
                        double Angle=0.;
                        for(const TCHAR* Name:{TEXT("spine_03"),TEXT("upperarm_l"),TEXT("upperarm_r"),TEXT("lowerarm_l"),TEXT("lowerarm_r"),TEXT("hand_l"),TEXT("hand_r"),TEXT("ik_hand_gun")})
                        {
                            const int32 Index=Bone(Name);
                            if(Index!=INDEX_NONE)Angle=FMath::Max(Angle,FMath::RadiansToDegrees(Input[Index].GetRotation().AngularDistance(SeatPose[Index].GetRotation())));
                        }
                        const auto Tread=[&](int32 Index,bool Left){return FVector::Distance(Body->GetComponentTransform().TransformPosition(SeatPose[Index].GetLocation()),Horse->Stirrup(Left)+FVector(0,0,3.5));};
                        const double Span=((Input[L].GetLocation()-Input[R].GetLocation())-(SeatPose[L].GetLocation()-SeatPose[R].GetLocation())).Size();
                        Csv+=FString::Printf(TEXT("%s,%s,%.0f,%d,%.8f,%.8f,%.5f,%.5f\n"),*Id,*Motion,Yaw,I,Angle,Span,Tread(BL,true),Tread(BR,false));
                    }
            }
            continue;
        }
        for(bool Mount:{true,false})
        {
            const FString Package=Ride->TransferPackage(Id==TEXT("kaitlin"),bRight,Mount);
            auto* Fixed=Bake?nullptr:LoadObject<UAnimSequence>(nullptr,*(Package+TEXT(".")+FPaths::GetCleanFilename(Package)));
            if(!Bake && !Fixed)return 10;
            Body->SetDisablePostProcessBlueprint(Bake);
            UFPSPlayerBodyAnimInstance* Graph=nullptr;
            if(UsePlayerGraph)
            {
                Body->SetAnimInstanceClass(nullptr);
                Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
                Graph=Cast<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());
                if(!Graph)return 12;
                Graph->Clips.Add(*ClipKey,Equip);
                FString Family,Action;
                ClipKey.Split(TEXT("."),&Family,&Action);
                Graph->BodyState.Family=*Family;
                if(auto* Neutral=LoadObject<UAnimSequence>(nullptr,*Data->GetObjectField(TEXT("clips"))->GetStringField(TEXT("Unarmed.Idle"))))
                    Graph->Clips.Add(TEXT("Unarmed.Idle"),Neutral);
            }
            else Body->PlayAnimation(Bake?Equip:Fixed,false);
            TArray<TArray<FTransform>> Frames;
            const float Duration=Mount?1.7f:1.4f;
            const int32 Last=FMath::RoundToInt(Duration*60.f);
            for(int32 Frame=0;Frame<=Last;++Frame)
            {
                const float T=Frame/60.f;
                const float P=Mount?T/Duration:1-T/Duration;
                Skin->SetPosition(FMath::Fmod(T,Idle->GetPlayLength()),false);
                Skin->TickAnimation(0,false);Skin->RefreshBoneTransforms();
                if(Frame==0)
                {
                    Ride->State.Horse=Horse;Ride->State.Phase=Mount?ERiderPhase::Mounting:ERiderPhase::Dismounting;
                    Ride->State.bFromRight=bRight;
                    const FVector Side=Horse->Saddle()+Horse->GetActorRightVector()*(bRight?1.f:-1.f)*(51.f+Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius());
                    Ride->State.Ground=FVector(Side.X,Side.Y,H+2.5f);
                    const float StartYaw=bExplicitYaw?GroundYaw:68.f*(bRight?-1.f:1.f);
                    Ride->State.Start=FTransform(FRotator(0,StartYaw,0),Ride->State.Ground);
                }
                Ride->State.Since=Ride->Clock()-T;
                Pawn->SetActorLocationAndRotation(Ride->RiderRoot(P),Ride->RiderFacing(P));
                if(Graph)Graph->Clock=T;
                else Body->SetPosition(Bake?0.f:T,false);
                Body->TickAnimation(Graph?1.f/60.f:0.f,false);
                Body->RefreshBoneTransforms();
                TArray<FTransform> Pose=Body->GetComponentSpaceTransforms();
                if(Bake)
                {
                    Ride->BuildContactPose(*Body,Pose);
                    auto& Local=Frames.Add_GetRef(Pose);
                    const auto& Rig=Asset->GetRefSkeleton();
                    for(int32 I=Local.Num()-1;I>0;--I)
                        Local[I]=Pose[I].GetRelativeTransform(Pose[Rig.GetParentIndex(I)]);
                }
                if(!Surface.IsEmpty() && (Frame%6==0 || Frame==Last))
                {
                    const FString Prefix=Surface/FString::Printf(TEXT("%s-%s-%03d"),*Id,Mount?TEXT("up"):TEXT("down"),Frame);
                    if(!SaveRiderSurface(Prefix,*Body,Pose,Frame==0))return 8;
                }
                const auto Row=[&](FName Name,const FTransform& Transform)
                {
                    const FVector V=Transform.GetLocation();const FQuat Q=Transform.GetRotation();
                    Csv+=FString::Printf(TEXT("%s,%s,%d,%.6f,%s,%.5f,%.5f,%.5f,%.7f,%.7f,%.7f,%.7f\n"),*Id,
                        Mount?TEXT("mount"):TEXT("dismount"),Frame,P,*Name.ToString(),V.X,V.Y,V.Z,Q.X,Q.Y,Q.Z,Q.W);
                };
                for(FName Name:Names)
                {
                    const int32 I=Asset->GetRefSkeleton().FindBoneIndex(Name);
                    if(!Pose.IsValidIndex(I))return 6;
                    Row(Name,Pose[I]*Body->GetComponentTransform());
                }
                for(FName Name:{FName(TEXT("saddle_socket")),FName(TEXT("stirrup_L")),FName(TEXT("stirrup_R"))})
                    Row(Name,Skin->GetSocketTransform(Name));
                Row(TEXT("tread_l"),FTransform(Horse->Stirrup(true)));
                Row(TEXT("tread_r"),FTransform(Horse->Stirrup(false)));
            }
            if(Bake && !SaveTransferClip(Package,*Asset,Frames))return 11;
        }
    }
    Ride->State.Phase=ERiderPhase::OnFoot;
    Body->DestroyComponent();
    World->DestroyWorld(false);
    return FFileHelper::SaveStringToFile(Csv,*Output,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)?0:7;
#else
    return 1;
#endif
}
