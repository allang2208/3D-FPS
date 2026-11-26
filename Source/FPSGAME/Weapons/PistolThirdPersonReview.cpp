#include "ShotgunAttachmentAuditCommandlet.h"
#include "PistolDualWieldComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "PistolReloadSkinProbe.h"
#include "PistolReviewGeometry.h"
#include "Kukri/OffhandKukriAuthoredStrike.h"
#include "Kukri/OffhandKukriAuthoredUppercut.h"
#include "Kukri/KukriRhythm.h"
#include "DanWesson715WeaponAssets.h"
#include "DualPistolReloadTiming.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "FPSBallisticsComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodySinglePistolSource.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

// Explicit user-requested, isolated third-person pose review. Native animation
// graphs and the normal equipment/motion consumers run; no player save or combat.
int32 UShotgunAttachmentAuditCommandlet::RunPistolBodyReview(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=PistolBody_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("PistolBodyReview"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Results,Observations;int32 Failures=0;
    const auto Check=[&](const FString& Name,bool Pass,double Value=0.)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);
        Row->SetBoolField(TEXT("passed"),Pass);Row->SetNumberField(TEXT("value"),Value);
        Results.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("PISTOL_BODY %s %s %.6f"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Value);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    Model->Current=Seed;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Pawn);
    // This standalone commandlet has no GameMode to create PlayerState. The
    // production third-person option requires IsPlayerControlled(), which in
    // UE uses PlayerState rather than merely possessing a player controller.
    Pawn->SetPlayerState(World->SpawnActor<APlayerState>());
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->DispatchBeginPlay();Model->CurrentPawn=Pawn;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->BodyAnimation||!Body->GetBodyMesh())return 2;
    Pawn->SetActorTickEnabled(false);Body->SetComponentTickEnabled(false);
    const bool ReloadClearance=FParse::Param(*Params,TEXT("ReloadClearance"));
    const bool QuickClearance=FParse::Param(*Params,TEXT("QuickClearance"));
    FString CaseFilter;FParse::Value(*Params,TEXT("PistolCase="),CaseFilter);
    const bool DualStandards=FParse::Param(*Params,TEXT("DualStandards"));
    const bool Completion=FParse::Param(*Params,TEXT("Completion"));
    FString GeometryRoot;const bool GeometryReview=FParse::Value(*Params,TEXT("Geometry="),GeometryRoot);
    FPistolReloadSkinProbe SkinProbe;
    if(ReloadClearance||DualStandards||Completion||GeometryReview)SkinProbe.Initialize(Body->GetBodyMesh());
    const auto TickPose=[](USkeletalMeshComponent* Mesh,float Delta=0.f)
    {
        ++GFrameCounter;Mesh->TickAnimation(Delta,false);Mesh->RefreshBoneTransforms();Mesh->UpdateChildTransforms();
    };
    const auto Rigid=[](FTransform T){T.SetScale3D(FVector::OneVector);return T;};
    struct FVariant {const TCHAR* Definition;const TCHAR* Slot;const TCHAR* Part;};
    const FVariant Variants[]={
        {TEXT("ue_m1911"),TEXT(""),TEXT("")},{TEXT("ue_g18"),TEXT(""),TEXT("")},
        {TEXT("ue_pit_viper2011"),TEXT(""),TEXT("")},{TEXT("ue_dan_wesson715"),TEXT(""),TEXT("")},
        {TEXT("ue_rsh12"),TEXT(""),TEXT("")},{TEXT("ue_g18"),TEXT("magazine"),TEXT("g18_drum_50")},
        {TEXT("ue_m1911"),TEXT("magazine"),TEXT("ext_mag")},
        {TEXT("ue_g18"),TEXT("magazine"),TEXT("ext_mag")},
        {TEXT("ue_pit_viper2011"),TEXT("magazine"),TEXT("ext_mag")},
        {TEXT("ue_rsh12"),TEXT("underbarrel"),TEXT("vertical_foregrip")},
        {TEXT("ue_rsh12"),TEXT("underbarrel"),TEXT("canted_foregrip")},
        {TEXT("ue_rsh12"),TEXT("underbarrel"),TEXT("prism_handstop")},
        {TEXT("ue_rsh12"),TEXT("underbarrel"),TEXT("angled_foregrip")}
    };
    if(FParse::Param(*Params,TEXT("OffhandKnife")))
    {
#include "PistolOffhandKnifeReview.inl"
    }
    else if(FParse::Param(*Params,TEXT("NetworkIdentity")))
    {
#include "PistolNetworkIdentityReview.inl"
    }
    else if(Completion)
    {
#include "PistolCompletionReview.inl"
    }
    else if(DualStandards)
    {
#include "DualPistolStandardsReview.inl"
    }
    else for(const auto& Variant:Variants)for(int32 Side=0;Side<2;++Side)
    {
        const FString VariantKey=FString::Printf(TEXT("%s/%s/%s"),Variant.Definition,*Variant.Part?Variant.Part:TEXT("base"),Side?TEXT("left"):TEXT("right"));
        if(!CaseFilter.IsEmpty()&&!VariantKey.StartsWith(CaseFilter))continue;
        if(ReloadClearance&&QuickClearance&&*Variant.Part)continue;
        auto Item=Model->CreateItem(Variant.Definition);Item.Place=1;Item.Cell=Side?8:6;Item.Magazine=5;
        if(*Variant.Slot)
        {
            TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(Variant.Slot,Variant.Part);
            Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
            Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        }
        Model->Current=Seed;Model->Current.Items={Item};Pawn->ApplyColdSteelProfile(Model);
        Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;
        Pawn->DualPistols->InterruptActions();Pawn->bIsAiming=false;Pawn->WeaponADSFactor=0.f;
        auto* Source=Side?Pawn->DualPistols->Hands[1].Mesh.Get():Pawn->AKMViewmodel.Get();
        if(Side)Pawn->DualPistols->Pose(1,0.f);else Pawn->UpdateActionPose(0.f);
        FlushAsyncLoading();TickPose(Source);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
        const FString Prefix=FString::Printf(TEXT("%s/%s/%s/"),Variant.Definition,*Variant.Part?Variant.Part:TEXT("base"),Side?TEXT("left"):TEXT("right"));
        Check(Prefix+TEXT("one world gun on owning hand"),Body->MotionBindings.Num()==1&&
            Body->MotionBindings[0].Definition.AttachHand==Side);
        if(Body->MotionBindings.Num()!=1)continue;
        auto& Binding=Body->MotionBindings[0];auto* Weapon=Binding.Mesh.Get();
        const FName Dominant=Side?TEXT("hand_l"):TEXT("hand_r"),Support=Side?TEXT("hand_r"):TEXT("hand_l");
        Check(Prefix+TEXT("attachment socket"),Weapon&&Weapon->GetAttachSocketName()==Dominant);
        Check(Prefix+TEXT("ready support belongs to opposite hand"),
            Side?(Body->BodyAnimation->bHasRightGrip&&!Body->BodyAnimation->bHasLeftGrip):
                (Body->BodyAnimation->bHasLeftGrip&&!Body->BodyAnimation->bHasRightGrip));
        auto* ExpectedProfile=Side?Pawn->DualPistols->Hands[1].Anim->GripProfile.Get():Pawn->GunplayAnimation->GripProfile.Get();
        Check(Prefix+TEXT("captured grip profile"),Binding.Definition.GripProfile.Get()==ExpectedProfile);
        const auto ClipFor=[&](const FString& Kind)->UAnimSequence*
        {
            if(Side)return Pawn->DualPistols->Hands[1].Clips.FindRef(Kind);
            if(Kind==TEXT("idle"))return Pawn->IdleAnimation;
            if(Kind==TEXT("fire"))return Pawn->FireAnimation;
            if(Kind==TEXT("equip"))return Pawn->EquipAnimation;
            if(Kind==TEXT("reload"))return Pawn->ReloadAnimation;
            return Pawn->ReloadEmptyAnimation;
        };
        if(ReloadClearance)
        {
#include "PistolReloadClearanceReview.inl"
            continue;
        }
        struct FPoseCase{FString Name;const TCHAR* Clip;float Fraction;bool Aim;bool Crouch;float Pitch=0;float Yaw=0;float Speed=0,Direction=0;bool Run=false;};
        TArray<FPoseCase> Cases={
            {TEXT("idle"),TEXT("idle"),0,false,false},{TEXT("aim"),TEXT("idle"),0,true,false},
            {TEXT("crouch"),TEXT("idle"),0,false,true},{TEXT("fire"),TEXT("fire"),.2f,false,false},
            {TEXT("aim_up"),TEXT("idle"),0,true,false,35,20},
            {TEXT("crouch_aim_down"),TEXT("idle"),0,true,true,-30,-20},
            {TEXT("equip"),TEXT("equip"),.6f,false,false},{TEXT("reload_start"),TEXT("reload"),.15f,false,false},
            {TEXT("reload_insert"),TEXT("reload"),.6f,false,false},{TEXT("reload_return"),TEXT("reload"),.95f,false,false},
            {TEXT("empty_insert"),TEXT("reload_empty"),.6f,false,false},{TEXT("idle_return"),TEXT("idle"),0,false,false}
        };
        if(GeometryReview)for(int32 Direction=0;Direction<8;++Direction)for(int32 Pace=0;Pace<3;++Pace)
            Cases.Add({FString::Printf(TEXT("move_%d_%d"),Direction,Pace),TEXT("idle"),0,false,Pace==2,0,0,
                Pace==0?300.f:Pace==1?600.f:180.f,Direction*45.f,Pace==1&&(Direction==0||Direction==1||Direction==7)});
        bool First=true;
        for(const auto& C:Cases)
        {
            FString Role=C.Clip;
            if(Side&&Pawn->DualPistols->Hands[1].Revolver&&Role.StartsWith(TEXT("reload")))Role=TEXT("speed_0");
            auto* Clip=ClipFor(Role);if(!Clip){Check(Prefix+C.Name+TEXT(" source"),false);continue;}
            const float Time=Clip->GetPlayLength()*C.Fraction;
            const bool Action=FCString::Strcmp(C.Clip,TEXT("idle"))!=0,Reload=FString(C.Clip).StartsWith(TEXT("reload"));
            Pawn->bIsAiming=C.Aim;Pawn->WeaponADSFactor=C.Aim?1.f:0.f;
            Pawn->bIsSprinting=C.Run;Pawn->SprintPoseFactor=Pawn->PistolLocomotionAlpha=C.Run?1.f:0.f;
            Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            Pawn->GetCharacterMovement()->Velocity=FRotator(0,C.Direction,0).Vector()*C.Speed;
            Pawn->WeaponState=Action?(Reload?EAKMWeaponState::Reloading:FCString::Strcmp(C.Clip,TEXT("equip"))==0?EAKMWeaponState::Equipping:EAKMWeaponState::Idle):EAKMWeaponState::Idle;
            Pawn->WeaponStateElapsed=Time;Pawn->WeaponStateDuration=Clip->GetPlayLength();
            if(Side)
            {
                if(Action)Pawn->DualPistols->StartAction(1,Role,1.f);
                else Pawn->DualPistols->StopAction(1);
                auto& Hand=Pawn->DualPistols->Hands[1];Hand.Action=Action?Clip:nullptr;Hand.ActionTime=Time;Hand.ActionRate=1.f;
                Hand.SprintBlend=C.Run?1.f:0.f;
                Hand.Reloading=Reload;Hand.ActionBlendStarted=World->GetTimeSeconds()-1.;
                Pawn->DualPistols->Pose(1,0.f);
            }
            else
            {
                Pawn->ActiveActionAnimation=Action?Clip:nullptr;Pawn->ActionElapsed=Time;Pawn->ActionDuration=Clip->GetPlayLength();
                Pawn->ActionStartPosition=0;Pawn->ActionPlayRate=1;Pawn->UpdateActionPose(0.f);
                Pawn->GunplayAnimation->ActionTime=Time;Pawn->GunplayAnimation->ActionAlpha=Action?1.f:0.f;
            }
            TickPose(Source);
            auto State=Body->SampleLocalState();State.bCrouched=C.Crouch;State.bSprinting=C.Run;State.LastShotAt=-100.f;State.RightHand.LastShotAt=State.LeftHand.LastShotAt=-100.f;
            if(Role==TEXT("fire"))
            {
                const float ShotAt=World->GetTimeSeconds()-Time;
                if(Side)State.LeftHand.LastShotAt=ShotAt;
                else State.LastShotAt=State.RightHand.LastShotAt=ShotAt;
            }
            State.AimPitch=C.Pitch;State.AimYaw=C.Yaw;
            Body->CaptureMotion(State);Body->DisplayState=State;
            Body->ApplyMotion(First?1.f:1.f/60.f);First=false;
            auto* Anim=Body->BodyAnimation.Get();Anim->BodyState=Anim->UpperState=Anim->MotionState=State;
            Anim->Clock=World->GetTimeSeconds();Anim->CrouchAlpha=C.Crouch?1.f:0.f;Anim->AimAlpha=C.Aim?1.f:0.f;
            Anim->UpperAlpha=Action?1.f:0.f;Anim->MotionAlpha=Anim->AirAlpha=0.f;Anim->SprintAlpha=C.Run?1.f:0.f;
            Anim->Speed=C.Speed;Anim->Direction=C.Direction;
            if(GeometryReview)for(int32 Settle=0;Settle<12;++Settle){Body->ApplyMotion(1.f/60.f);TickPose(Body->GetBodyMesh(),1.f/60.f);}
            else TickPose(Body->GetBodyMesh(),.2f);
            Weapon->UpdateComponentToWorld();Weapon->UpdateChildTransforms();
            const auto* Map=Body->MotionMap(Source,Dominant,Side);if(!Map||!Map->IsValid())return 2;
            const FTransform Hand=Rigid(Source->GetSocketTransform(Dominant,RTS_Component));
            const FTransform Expected=Source->GetSocketTransform(TEXT("WPN_root"),RTS_Component).GetRelativeTransform(Hand)*
                Map->Mount*Body->GetBodyMesh()->GetSocketTransform(Dominant);
            const FTransform Actual=Weapon->GetSocketTransform(TEXT("WPN_root"));
            const double GripError=FVector::Dist(Expected.GetLocation(),Actual.GetLocation());
            const double RotationError=FMath::RadiansToDegrees(Expected.GetRotation().AngularDistance(Actual.GetRotation()));
            const FString Case=Prefix+C.Name;
            Check(Case+TEXT(" gun contact cm"),GripError<.5,GripError);
            Check(Case+TEXT(" gun contact angle deg"),RotationError<2.,RotationError);
            Check(Case+TEXT(" finite positive scale"),!Actual.ContainsNaN()&&Actual.GetScale3D().GetMin()>0.);
            if(GeometryReview)
            {
                SkinProbe.Update(Body->GetBodyMesh());
                const double ArmDepth=FMath::Max(SkinProbe.Arm(0).Depth,SkinProbe.Arm(1).Depth);
                const double GunDepth=SkinProbe.Weapon(Weapon,Body->GetBodyMesh()->GetComponentTransform()).Depth;
                Check(Case+TEXT(" arms outside torso cm"),ArmDepth<=.2,ArmDepth);
                Check(Case+TEXT(" gun outside torso cm"),GunDepth<=.2,GunDepth);
            }
            FString GeometryDir;
            if(FParse::Value(*Params,TEXT("Geometry="),GeometryDir)&&(*Variant.Part==0||!CaseFilter.IsEmpty())&&
                (FString(C.Name)==TEXT("idle")||FString(C.Name)==TEXT("reload_start")||FString(C.Name)==TEXT("aim_up")||FString(C.Name)==TEXT("reload_insert")||
                 C.Name==TEXT("move_0_1")||C.Name==TEXT("move_6_1")))
            {
                TArray<USkeletalMeshComponent*> Meshes={Body->GetBodyMesh(),Weapon};
                TArray<UStaticMeshComponent*> Parts;for(const auto& Part:Binding.Parts)if(Part.IsValid())Parts.Add(Part.Get());
                FPSPistolReviewGeometry::Save(GeometryDir/(Case.Replace(TEXT("/"),TEXT("_"))+TEXT(".obj")),Meshes,Parts,Body->GetBodyMesh()->GetComponentTransform());
            }
            double PartPosition=0.,PartAngle=0.;bool PartsValid=Binding.Parts.Num()==Binding.Definition.SourceParts.Num();
            for(int32 P=0;P<Binding.Parts.Num()&&PartsValid;++P)
            {
                auto* Native=Binding.Definition.SourceParts[P].Get();auto* Copy=Binding.Parts[P].Get();
                if(!Native||!Copy){PartsValid=false;break;}
                FTransform PartExpected=Native->GetComponentTransform().GetRelativeTransform(Rigid(Hand*Source->GetComponentTransform()))*
                    Map->Mount*Body->GetBodyMesh()->GetSocketTransform(Dominant);
                if(Binding.bMagazineOverride&&P==Binding.MagazinePart)
                    PartExpected=Binding.MagazinePartPose*Weapon->GetComponentTransform();
                PartPosition=FMath::Max(PartPosition,FVector::Dist(PartExpected.GetLocation(),Copy->GetComponentLocation()));
                PartAngle=FMath::Max(PartAngle,FMath::RadiansToDegrees(PartExpected.GetRotation().AngularDistance(Copy->GetComponentQuat())));
            }
            Check(Case+TEXT(" attachments contact cm"),PartsValid&&PartPosition<.5,PartPosition);
            Check(Case+TEXT(" attachments contact angle deg"),PartsValid&&PartAngle<2.,PartAngle);
            const FTransform RelativeSupport=Anim->UsesNativeSinglePistolSource()&&C.Run?
                Anim->SinglePistolContact.Ready:(Side?Anim->RightGripFromLeft:Anim->LeftGripFromRight);
            const FTransform SupportTarget=RelativeSupport*Body->GetBodyMesh()->GetSocketTransform(Dominant);
            const double SupportError=FVector::Dist(SupportTarget.GetLocation(),Body->GetBodyMesh()->GetSocketLocation(Support));
            auto Observation=MakeShared<FJsonObject>();Observation->SetStringField(TEXT("case"),Case);
            Observation->SetNumberField(TEXT("support_contact_cm"),SupportError);
            if(GeometryReview)
                for(int32 SideIndex=0;SideIndex<2;++SideIndex)
                {
                    const auto Probe=SkinProbe.Arm(SideIndex);
                    Observation->SetNumberField(SideIndex?TEXT("left_skin_depth_cm"):TEXT("right_skin_depth_cm"),Probe.Depth);
                    Observation->SetStringField(SideIndex?TEXT("left_skin_point"):TEXT("right_skin_point"),Probe.Point.ToString());
                }
            if(GeometryReview&&FString(C.Name)==TEXT("reload_insert"))
            {
                const auto* Mesh=Body->GetBodyMesh();const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
                for(int32 Arm=0;Arm<2;++Arm)
                {
                    const FName HandName=Arm?TEXT("hand_l"):TEXT("hand_r");
                    const int32 W=Ref.FindBoneIndex(HandName),E=Ref.GetParentIndex(W),S=Ref.GetParentIndex(E);
                    const auto H=Mesh->GetSocketTransform(HandName,RTS_Component);
                    const auto Elbow=Mesh->GetSocketTransform(Ref.GetBoneName(E),RTS_Component);
                    const auto Upper=Mesh->GetSocketTransform(Ref.GetBoneName(S),RTS_Component);
                    const auto& Bind=Ref.GetRefBonePose()[W];
                    const FVector WristAxis=(H.GetRotation()*Bind.GetRotation().Inverse()).RotateVector(Bind.GetLocation().GetSafeNormal());
                    const double Bend=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(WristAxis,(H.GetLocation()-Elbow.GetLocation()).GetSafeNormal()),-1.,1.)));
                    Observation->SetNumberField(Arm?TEXT("left_wrist_bend_deg"):TEXT("right_wrist_bend_deg"),Bend);
                    const auto& SourceRef=Source->GetSkeletalMeshAsset()->GetRefSkeleton();
                    const int32 SW=SourceRef.FindBoneIndex(HandName),SE=SourceRef.GetParentIndex(SW);
                    const auto SH=Source->GetSocketTransform(HandName,RTS_Component);
                    const auto SL=Source->GetSocketTransform(SourceRef.GetBoneName(SE),RTS_Component);
                    const auto& SB=SourceRef.GetRefBonePose()[SW];
                    const FVector SA=(SH.GetRotation()*SB.GetRotation().Inverse()).RotateVector(SB.GetLocation().GetSafeNormal());
                    const double SourceBend=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(SA,(SH.GetLocation()-SL.GetLocation()).GetSafeNormal()),-1.,1.)));
                    Observation->SetNumberField(Arm?TEXT("source_left_wrist_bend_deg"):TEXT("source_right_wrist_bend_deg"),SourceBend);
                    Observation->SetNumberField(Arm?TEXT("left_elbow_above_shoulder_cm"):TEXT("right_elbow_above_shoulder_cm"),Elbow.GetLocation().Z-Upper.GetLocation().Z);
                }
            }
            Observations.Add(MakeShared<FJsonValueObject>(Observation));
            // During a held pose both hands must actually reach the same grip.
            if(!Action)Check(Case+TEXT(" support contact cm"),SupportError<1.,SupportError);
            if(!Action)
            {
                const FVector Bore=(Weapon->GetSocketLocation(TEXT("WPN_FrontSight"))-Weapon->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
                const FVector AimDirection=FRotator(State.AimPitch,Pawn->GetActorRotation().Yaw+State.AimYaw,0.f).Vector();
                const double Forward=FVector::DotProduct(Bore,AimDirection);
                Check(Case+TEXT(" barrel forward"),Forward>.65,Forward);
            }
            if(Action)
            {
                const FTransform SavedFrame=Source->GetRelativeTransform();
                Source->AddLocalOffset(FVector(80,-40,30));
                auto Shifted=State;Body->CaptureMotion(Shifted);Source->SetRelativeTransform(SavedFrame);
                Check(Case+TEXT(" action independent of viewmodel position"),
                    Shifted.Contacts.Hands[Side].Wrist.Equals(State.Contacts.Hands[Side].Wrist,.001));
            }
        }
        // An old loadout packet must not move either hand of the newly fitted
        // single pistol. Use the saved equipment grip until a matching packet.
        auto Stale=Body->DisplayState;Stale.Contacts.Rigs[0].Schema^=0x80;
        Stale.Contacts.HasSupportGrip=true;Stale.Contacts.SupportGrip.SetLocation(FVector(900,900,900));
        Body->DisplayState=Stale;Body->ApplyMotion(1.f/60.f);
        auto* Anim=Body->BodyAnimation.Get();
        const FTransform Fallback=Side?Anim->RightGripFromLeft:Anim->LeftGripFromRight;
        const FTransform Saved=Side?Body->BaseRightSupportGrip:Body->BaseSupportGrip;
        Check(Prefix+TEXT(" stale packet preserves equipment grip"),Fallback.Equals(Saved,.001));
        Check(Prefix+TEXT(" stale packet rejects both hand samples"),Anim->ActionFingerMask==0&&Anim->ActionWristMask==0);
        Check(Prefix+TEXT(" stale packet restores gun mount"),Weapon->GetRelativeTransform().Equals(Binding.Mount,.001));
    }
    auto Output=MakeShared<FJsonObject>();Output->SetNumberField(TEXT("failures"),Failures);Output->SetArrayField(TEXT("checks"),Results);
    Output->SetArrayField(TEXT("observations"),Observations);
    Output->SetStringField(TEXT("body_mesh"),Body->GetBodyMesh()->GetSkeletalMeshAsset()->GetPathName());
    if(ReloadClearance||DualStandards)
    {
        Output->SetNumberField(TEXT("torso_triangles"),SkinProbe.TorsoIndices.Num()/3);
        Output->SetNumberField(TEXT("reference_front_from_spine_cm"),SkinProbe.ReferenceFrontFromSpine);
    }
    Output->SetStringField(TEXT("scope"),TEXT("native isolated local pose/equipment checks; no visual or network acceptance"));
    FString Path;if(!FParse::Value(*Params,TEXT("Output="),Path))Path=FPaths::ProjectSavedDir()/TEXT("PistolThirdPerson/review.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    FString Text;FJsonSerializer::Serialize(Output,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);
    UE_LOG(LogTemp,Display,TEXT("PISTOL_BODY_COMPLETE checks=%d failures=%d"),Results.Num(),Failures);
    Model->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {
        It->RouteEndPlay(EEndPlayReason::Quit);
        TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
