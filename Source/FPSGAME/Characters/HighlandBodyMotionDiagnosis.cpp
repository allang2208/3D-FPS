#if WITH_EDITOR
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyGrip.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSBodySwordMotion.h"
#include "../Weapons/WeaponGripProfile.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Serialization/JsonSerializer.h"

// Opt-in inspection of the installed native graph and mesh post-process.
// This fixture supplies executor-equivalent presentation clocks; it does not
// claim to exercise input, damage, a network transport, or player movement.
namespace HighlandBodyMotionDiagnosis
{
template<class T> static void Binary(const TArray<T>& Values,const FString& Path)
{
    check(FFileHelper::SaveArrayToFile(TArrayView<const uint8>(reinterpret_cast<const uint8*>(Values.GetData()),Values.Num()*sizeof(T)),*Path));
}
static TSharedPtr<FJsonValue> Pack(const FTransform& T)
{
    TArray<TSharedPtr<FJsonValue>> A;const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})A.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(A);
}
static void Append(TArray<float>& Out,const FTransform& T)
{
    const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})Out.Add(float(V));
}
static void Save(const TSharedRef<FJsonObject>& O,const FString& Path)
{
    FString S;FJsonSerializer::Serialize(O,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));
    check(FFileHelper::SaveStringToFile(S,*Path));
}
static FTransform Rigid(FTransform T){T.SetScale3D(FVector::OneVector);return T;}
static void Run(const TArray<FString>& Args)
{
    if(Args.IsEmpty())return;
    const FString Out=Args[0];IFileManager::Get().MakeDirectory(*Out,true);
    FString Text;TSharedPtr<FJsonObject> Root;
    check(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))));
    check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root));
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("HighlandBodyReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Floor=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);
    Floor->AddInstanceComponent(Box);Floor->SetRootComponent(Box);Box->SetBoxExtent(FVector(10000,10000,5));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponentWithWorld(World);Floor->SetActorLocation(FVector(0,0,-5));
    auto* Donor=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms"));check(Donor);
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;
    for(const FString Kind:{FString(TEXT("Jason")),FString(TEXT("Kaitlin"))})
    {
        const auto Cfg=Kind==TEXT("Jason")?Root:Root->GetObjectField(TEXT("body_variants"))->GetObjectField(TEXT("kaitlin"));
        auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Cfg->GetStringField(TEXT("body_mesh")));check(Asset);
        TMap<FName,TObjectPtr<UAnimSequence>> Clips;
        for(const auto& Pair:Cfg->GetObjectField(TEXT("clips"))->Values)
            if(Pair.Key.ToView().StartsWith(TEXT("Melee."))||Pair.Key.ToView().StartsWith(TEXT("Unarmed.")))
                if(auto* A=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,A);
        FAssetCompilingManager::Get().FinishAllCompilation();
        const FString BodyDir=Out/Kind;IFileManager::Get().MakeDirectory(*BodyDir,true);
        auto* Actor=World->SpawnActor<ACharacter>();Actor->SetActorLocation(FVector(0,0,96));
        Actor->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        auto* Body=Actor->GetMesh();Body->SetRelativeLocation(FVector(0,0,-96));Body->SetSkeletalMeshAsset(Asset);
        Body->SetDisablePostProcessBlueprint(false);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        const auto& Ref=Asset->GetRefSkeleton();const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];
        const auto* Weights=Body->GetSkinWeightBuffer(0);check(Weights&&Weights->GetNeedsCPUAccess());
        const int32 Count=LOD.GetNumVertices(),Influences=Weights->GetMaxBoneInfluences();
        TArray<FVector3f> Bind;Bind.SetNum(Count);TArray<uint16> Bones;Bones.SetNumZeroed(Count*Influences);
        TArray<float> Weight;Weight.SetNumZeroed(Count*Influences);TArray<uint32> Indices;
        LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);
        for(const auto& Section:LOD.RenderSections)for(uint32 I=Section.BaseVertexIndex;I<Section.BaseVertexIndex+Section.NumVertices;++I)
        {
            Bind[I]=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(I);
            for(int32 K=0;K<Influences;++K)
            {Bones[I*Influences+K]=Section.BoneMap[Weights->GetBoneIndex(I,K)];Weight[I*Influences+K]=float(Weights->GetBoneWeight(I,K))/65535.f;}
        }
        Binary(Bind,BodyDir/TEXT("skin.bind"));Binary(Bones,BodyDir/TEXT("skin.bones"));Binary(Weight,BodyDir/TEXT("skin.weights"));Binary(Indices,BodyDir/TEXT("skin.indices"));
        auto Meta=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Names,Parents,Rest;TArray<FTransform> RefPose=Ref.GetRefBonePose();
        for(int32 B=0;B<Ref.GetNum();++B)
        {const int32 P=Ref.GetParentIndex(B);if(P>=0)RefPose[B]*=RefPose[P];Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(B).ToString()));Parents.Add(MakeShared<FJsonValueNumber>(P));Rest.Add(Pack(RefPose[B]));}
        Meta->SetArrayField(TEXT("names"),Names);Meta->SetArrayField(TEXT("parents"),Parents);Meta->SetArrayField(TEXT("rest"),Rest);
        Meta->SetStringField(TEXT("mesh"),Asset->GetPathName());Meta->SetNumberField(TEXT("influences"),Influences);
        Meta->SetNumberField(TEXT("vertex_count"),Count);Meta->SetNumberField(TEXT("morph_count"),Asset->GetMorphTargets().Num());
        auto ClipMeta=MakeShared<FJsonObject>();
        for(const TCHAR* Key:{TEXT("Melee.FullBody.Thrust"),TEXT("Melee.FullBody.HighlandBreakSweep")})
        {auto* Clip=Clips.FindRef(Key).Get();check(Clip&&Clip->GetSkeleton()==Asset->GetSkeleton());auto M=MakeShared<FJsonObject>();M->SetStringField(TEXT("path"),Clip->GetPathName());M->SetNumberField(TEXT("length"),Clip->GetPlayLength());auto Markers=MakeShared<FJsonObject>();for(const auto& Mk:Clip->AuthoredSyncMarkers)Markers->SetNumberField(Mk.MarkerName.ToString(),Mk.Time);M->SetObjectField(TEXT("markers"),Markers);ClipMeta->SetObjectField(Key,M);}
        Meta->SetObjectField(TEXT("clips"),ClipMeta);Save(Meta,BodyDir/TEXT("mesh.json"));
        for(const FString Grip:{FString(TEXT("Standard")),FString(TEXT("LongGrip"))})
        {
            auto* Source=NewObject<UFPSBodyWeaponMeshComponent>(Actor);Actor->AddInstanceComponent(Source);Source->SetSkeletalMeshAsset(Donor);
            Source->SetDisablePostProcessBlueprint(true);Source->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
            if(Grip==TEXT("LongGrip"))Source->GripProfile=LoadObject<UWeaponGripProfile>(nullptr,TEXT("/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip"));
            auto* Idle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle"));
            if(Source->GripProfile)if(const auto* Layer=Source->GripProfile->FindAction(TEXT("Idle")))Idle=Layer->Playback();
            Source->RegisterComponentWithWorld(World);Source->PlayAnimation(Idle,false);Source->SetPosition(0,false);Source->TickAnimation(0,false);Source->RefreshBoneTransforms();
            FFPSBodyGripRig Rigs[2];for(int32 H=0;H<2;++H){const FName N=H==0?TEXT("hand_r"):TEXT("hand_l");Rigs[H].Initialize(Donor->GetRefSkeleton(),Ref,N,N);check(Rigs[H].IsValid());}
            const auto R=Rigid(Source->GetSocketTransform(TEXT("hand_r"),RTS_Component)),L=Rigid(Source->GetSocketTransform(TEXT("hand_l"),RTS_Component));
            const auto Weapon=Rigid(Source->GetSocketTransform(TEXT("WPN_root"),RTS_Component));
            const FTransform Mount=Weapon*R.Inverse()*Rigs[0].Mount;
            auto* SweepExecutor=LoadObject<UAnimSequence>(nullptr,*(FString(TEXT("/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104/A_Highland_BreakSweep_"))+Grip));
            check(SweepExecutor);
            for(const FString Role:{FString(TEXT("sweep")),FString(TEXT("charged_thrust")),FString(TEXT("finisher")),FString(TEXT("dash")),FString(TEXT("cancel")),FString(TEXT("moving_thrust"))})
            {
                const FString CaseDir=BodyDir/(Grip+TEXT("_")+Role);IFileManager::Get().MakeDirectory(*CaseDir,true);
                Body->SetAnimInstanceClass(nullptr);Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
                auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
                FPSBodyHighlandMotion::SelectGrip(Anim->Clips,Grip==TEXT("LongGrip"));
                const auto& Scale=Cfg->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
                Anim->LeftGripFromRight=Rigs[1].Mount.Inverse()*L.GetRelativeTransform(R)*Rigs[0].Mount;Anim->bHasLeftGrip=true;
                for(const auto& Rig:Rigs)Rig.Transfer(Source->GetComponentSpaceTransforms(),Anim->EquipmentFingers);
                Anim->EquipmentGripHands=3;Anim->BodyState.Family=TEXT("Melee");Anim->BodyState.Weapon=TEXT("ue_highland_claymore");
                // Match CaptureMotion's idle hand frame; omitting these inputs
                // would audit the graph's fallback carry, not the player carry.
                const FQuat CarryFrame=FRotator(0,180,0).Quaternion();
                Anim->ActionHands[0]=FTransform(CarryFrame*(Rigs[0].Mount.Inverse()*R).GetRotation(),FPSBodyPoses::SwordReady(0)*Anim->PoseScale);
                Anim->ActionHands[1]=Anim->LeftGripFromRight*Anim->ActionHands[0];
                Anim->ActionFingers=Anim->EquipmentFingers;Anim->ActionFingerMask=3;
                Anim->ActionWristMask=3;Anim->bCoupledActionWrists=true;
                Anim->Speed=Role==TEXT("moving_thrust")?150.f:0.f;
                constexpr float Dt=1.f/60.f;
                const auto Tick=[&](){Anim->Clock+=Dt;Body->TickAnimation(Dt,false);Body->RefreshBoneTransforms();};
                for(int32 I=0;I<30;++I)Tick();
                const bool Sweep=Role==TEXT("sweep"),Charged=Role==TEXT("charged_thrust")||Role==TEXT("moving_thrust"),Cancel=Role==TEXT("cancel");
                const FName Variant=Sweep?HighlandBreakSweep::Clip:Role==TEXT("finisher")?HighlandRidgeThrust::Finisher:Role==TEXT("dash")?HighlandRidgeThrust::Dash:HighlandRidgeThrust::Release;
                const float Lead=HighlandRidgeThrust::LeadFor(Variant),Rate=Role==TEXT("finisher")?HighlandRidgeThrust::FinisherPlaybackRate:1.f;
                // The executor clock comes from the installed first-person take,
                // even if the separately authored full-body take has another duration.
                const float Attack=Sweep?SweepExecutor->GetPlayLength()/HighlandBreakSweep::PlaybackRate:HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ReleaseSeconds,Lead,Rate);
                const float Pre=Sweep?.30f:(Charged||Cancel)?1.f:0.f;
                const float Total=Pre+(Cancel?.20f:Attack)+.4f;
                auto Case=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Frames;TArray<float> Poses;
                Case->SetStringField(TEXT("body"),Kind);Case->SetStringField(TEXT("grip"),Grip);Case->SetStringField(TEXT("role"),Role);Case->SetField(TEXT("mount"),Pack(Mount));
                Case->SetField(TEXT("left_grip"),Pack(Anim->LeftGripFromRight));Case->SetNumberField(TEXT("attack_seconds"),Attack);Case->SetNumberField(TEXT("lead_seconds"),Pre);
                for(int32 F=0;F<=FMath::CeilToInt(Total/Dt);++F)
                {
                    const float T=F*Dt;auto& S=Anim->BodyState;S.ActionWeight=1.f;S.bHasActionProgress=true;S.ActionProgressRate=0.f;
                    if(T<Pre)
                    {
                        S.Action=Sweep?EFPSBodyAction::HeavyStrike:EFPSBodyAction::Charge;
                        S.ActionVariant=Sweep?FName(TEXT("HeavyRelease")):HighlandRidgeThrust::Charge;
                        S.ActionDuration=Pre;S.ActionProgress=Sweep?.55f:T/Pre;S.ContactFraction=.25f;S.ReleaseFraction=.55f;
                    }
                    else if(Cancel&&T<Pre+.20f)
                    {S.Action=EFPSBodyAction::Charge;S.ActionVariant=HighlandRidgeThrust::Charge;S.ActionProgress=1.f;S.ActionWeight=1.f-FMath::SmoothStep(0.f,.20f,T-Pre);}
                    else if(!Cancel&&T<Pre+Attack)
                    {
                        S.Action=Sweep?EFPSBodyAction::Strike:EFPSBodyAction::Thrust;S.ActionVariant=Variant;S.ActionDuration=Attack;S.ActionProgress=(T-Pre)/Attack;
                        S.ContactFraction=Sweep?HighlandBreakSweep::Contact/(Attack*2.f):HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ContactStart,Lead,Rate)/Attack;
                        S.ReleaseFraction=Sweep?HighlandBreakSweep::Release/(Attack*2.f):HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ContactEnd,Lead,Rate)/Attack;
                        S.ActionEntryFraction=Sweep?0.f:HighlandRidgeThrust::ToWall(Lead,Lead,Rate)/Attack;
                    }
                    else {S.Action=EFPSBodyAction::None;S.ActionVariant=NAME_None;S.bHasActionProgress=false;}
                    Anim->ActionWristMask=FPSBodySwordMotion::Clip(S).IsNone()?3:0;
                    Anim->bCoupledActionWrists=Anim->ActionWristMask!=0;
                    Tick();
                    if(F%2)continue;
                    auto Frame=MakeShared<FJsonObject>();Frame->SetNumberField(TEXT("time"),T);Frame->SetStringField(TEXT("variant"),S.ActionVariant.ToString());Frame->SetNumberField(TEXT("progress"),S.ActionProgress);
                    Frame->SetStringField(TEXT("selected"),FPSBodySwordMotion::Clip(S).ToString());
                    Frame->SetNumberField(TEXT("roll"),Anim->GetCurveValue(TEXT("SwordGripRoll")));Frame->SetNumberField(TEXT("slide"),Anim->GetCurveValue(TEXT("SwordGripSlide")));
                    Frame->SetBoolField(TEXT("post_process_instance"),Body->GetPostProcessInstance()!=nullptr);
                    const auto& Pose=Body->GetComponentSpaceTransforms();check(Pose.Num()==Ref.GetNum());
                    for(const auto& Bone:Pose)Append(Poses,Bone);
                    Frames.Add(MakeShared<FJsonValueObject>(Frame));
                }
                Case->SetArrayField(TEXT("frames"),Frames);Save(Case,CaseDir/TEXT("motion.json"));Binary(Poses,CaseDir/TEXT("poses.bin"));
                Cases.Add(MakeShared<FJsonValueString>(Kind/(Grip+TEXT("_")+Role)));
            }
            Source->DestroyComponent();
        }
        Actor->Destroy();
    }
    Report->SetArrayField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("pose_sample_hz"),30);Report->SetNumberField(TEXT("graph_tick_hz"),60);
    Report->SetStringField(TEXT("scope"),TEXT("Current native graph and post-process; manually supplied presentation states, actual render buffers. No player executor or network transport."));
    Save(Report,Out/TEXT("report.json"));World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("HIGHLAND_BODY_REVIEW %s"),*Out);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseHighlandMotion"),TEXT("Explicit Highland third-person inspection: output-directory"),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
