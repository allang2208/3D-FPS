#if WITH_EDITOR
// Explicitly invoked transient-world regression; never loads or writes player saves.
#include "Components/BoxComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "Animation/AnimSequence.h"

struct FM24BipodValidation
{
    static void Run(const TArray<FString>& Args)
    {
        if(Args.IsEmpty())return;
        const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
            .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
        auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("M24BipodValidation"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
        auto* C=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
        PC->SetAsLocalPlayerController();PC->Possess(C);PC->bShowMouseCursor=false;PC->SetControlRotation(FRotator::ZeroRotator);
        C->ActiveInventoryWeaponDefinition=M24WeaponAssets::Definition;C->ActiveInventoryWeapon=TEXT("isolated_m24");
        C->bInventoryWeaponReady=true;C->bUseM4Infima=false;C->WeaponState=EAKMWeaponState::Idle;
        C->bIsAiming=C->bAimHeld=true;C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        C->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        const FVector Eye=C->GetMeleeAimTransform().GetLocation();C->FirstPersonCamera->SetWorldLocationAndRotation(Eye,FRotator::ZeroRotator);
        C->AKMViewmodel->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9")));
        PKMLowpolyWeaponAssets::ConfigureBipod(C,C->AKMViewmodel,true);
        auto* P=Cast<UPKMBipodComponent>(PKMLowpolyWeaponAssets::FindBipod(C));auto* D=C->BipodDeployment.Get();D->Character=C;
        const FQuat Q=FRotator(0,90,0).Quaternion();const FVector Hinge=Eye+FVector(60,0,-20);
        P->SetWorldTransform(FTransform(Q,Hinge-Q.RotateVector(M24Bipod::Hinge)));
        auto* GI=NewObject<UGameInstance>();C->NetShadowProfile=NewObject<UColdSteelStatusModel>(GI);
        FColdSteelProfile Shadow;FColdSteelItem Item;Item.InstanceId=C->ActiveInventoryWeapon;Item.Definition=M24WeaponAssets::Definition;Item.Place=1;Item.Cell=6;
        Shadow.Items.Add(Item);C->NetShadowProfile->AdoptNetMirror(Shadow);
        auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Cases;int32 Failed=0;
        const auto Check=[&](const TCHAR* Name,bool Pass)
        {auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);Row->SetBoolField(TEXT("pass"),Pass);Cases.Add(MakeShared<FJsonValueObject>(Row));if(!Pass)++Failed;};
        const auto Box=[&](const FVector& Center,const FVector& Extent,const FRotator& Rotation=FRotator::ZeroRotator)
        {
            auto* A=World->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(A);A->SetRootComponent(B);A->AddInstanceComponent(B);
            B->SetBoxExtent(Extent);B->SetCollisionEnabled(ECollisionEnabled::QueryOnly);B->SetCollisionResponseToAllChannels(ECR_Block);
            B->SetWorldLocationAndRotation(Center,Rotation);B->RegisterComponent();return B;
        };
        const FVector A=P->GetRestFootWorld(0),B=P->GetRestFootWorld(1);const double Top=(A.Z+B.Z)*.5;
        auto* Table=Box(FVector(70,0,Top-5),FVector(100,80,5));
        UWeaponBipodDeploymentComponent::FSupport Support;
        Check(TEXT("valid broad static surface"),D->FindSupport(*P,Support));
        const FTransform LevelRig=P->GetComponentTransform();
        for(const float Pitch:{-70.f,70.f})
        {
            const FRotator Aim(Pitch,0,0);const FQuat View=Aim.Quaternion();const FQuat Pose=View*Q;
            PC->SetControlRotation(Aim);C->FirstPersonCamera->SetWorldRotation(Aim);
            P->SetWorldTransform(FTransform(Pose,Eye+View.RotateVector(Hinge-Eye)-Pose.RotateVector(M24Bipod::Hinge)));
            Check(TEXT("entry pitch does not move the support search"),D->FindSupport(*P,Support)
                &&FMath::IsNearlyEqual(Support.Feet[0].Z,Top+.12,.01));
            FWeaponBipodNetState Pitched;Pitched.Anchor=Support.Anchor;Pitched.FeetA=Support.Feet[0];Pitched.FeetB=Support.Feet[1];
            Check(TEXT("authority accepts high and low entry pitch"),D->ResolveServerSupport(Pitched,Support));
        }
        PC->SetControlRotation(FRotator::ZeroRotator);C->FirstPersonCamera->SetWorldRotation(FRotator::ZeroRotator);P->SetWorldTransform(LevelRig);
        D->FindSupport(*P,Support);
        D->Support=Support;Check(TEXT("retained support"),D->SupportStillValid(true));
        Table->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("removed support is rejected"),!D->SupportStillValid(true)&&!D->FindSupport(*P,Support));
        Table->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        auto* Block=Box(Hinge+FVector(50,0,3.1),FVector(3,50,30));
        Check(TEXT("long barrel obstruction"),!D->ClearPlacement(Eye,FVector::ZeroVector,Hinge,FVector::ForwardVector));
        Check(TEXT("barrel clearance does not veto shared support acquisition"),D->FindSupport(*P,Support));
        Check(TEXT("hint uses the same support acquisition"),D->HasSupportHint(*P));
        FWeaponBipodNetState Obstructed;Obstructed.Anchor=Support.Anchor;Obstructed.FeetA=Support.Feet[0];Obstructed.FeetB=Support.Feet[1];
        Check(TEXT("authority also accepts support with blocked barrel correction"),D->ResolveServerSupport(Obstructed,Support));
        Block->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* Screen=Box((Eye+(A+B)*.5)*.5,FVector(2,100,200));
        Check(TEXT("occluded contacts cannot mount"),!D->FindSupport(*P,Support)&&!D->HasSupportHint(*P));
        Check(TEXT("authority rejects occluded contacts"),!D->ResolveServerSupport(Obstructed,Support));
        Screen->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("camera correction obstruction"),!D->ClearPlacement(Eye,FVector(0,0,Top-Eye.Z),Hinge,FVector::ForwardVector));
        Table->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* Sole=Box(A-FVector(0,0,1),FVector(1.5,1.5,1));
        Check(TEXT("single foot cannot mount"),!D->FindSupport(*P,Support));Sole->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* Slope=Box(FVector(65,0,Top-5),FVector(120,90,5),FRotator(35,0,0));
        Check(TEXT("steep support rejected"),!D->FindSupport(*P,Support));Slope->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* High=Box(FVector(70,0,Top+90),FVector(100,80,5));
        Check(TEXT("out of height reach"),!D->FindSupport(*P,Support));High->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("native contacts reachable"),P->CanReachContacts(A,B,FVector::ZeroVector));
        const FVector ReferenceLeg(0,0,-24);
        Check(TEXT("M24 accepts seven percent leg extension"),M24Bipod::CanReachLeg(ReferenceLeg,ReferenceLeg*1.07));
        Check(TEXT("M24 rejects excessive leg extension"),!M24Bipod::CanReachLeg(ReferenceLeg,ReferenceLeg*1.12));
        Check(TEXT("M24 accepts thirty degree leg adjustment"),M24Bipod::CanReachLeg(ReferenceLeg,FQuat(FVector::RightVector,FMath::DegreesToRadians(30.)).RotateVector(ReferenceLeg)));
        Check(TEXT("M24 rejects fifty degree leg adjustment"),!M24Bipod::CanReachLeg(ReferenceLeg,FQuat(FVector::RightVector,FMath::DegreesToRadians(50.)).RotateVector(ReferenceLeg)));
        Check(TEXT("unequal foot heights rejected"),!P->CanReachContacts(A+FVector(0,0,10),B-FVector(0,0,10),FVector::ZeroVector));
        Check(TEXT("sideways foot span rejected"),!P->CanReachContacts(A+FVector(20,0,0),B-FVector(20,0,0),FVector::ZeroVector));
        P->SetM24DeploymentTime(1.70f);P->SetDeploymentContacts(A,B,.1f);P->SetDeploymentContacts(A,B,0.f);
        Check(TEXT("contact release preserves unfolding clock"),P->Angles[0]>.999f&&P->Angles[1]>.999f);
        bool Sync=true;
        for(int32 I=FMath::RoundToInt(M24Bipod::Duration*240);I>=0;--I){const float T=I/240.f;P->SetM24DeploymentTime(T);Sync&=FMath::IsNearlyEqual(P->Angles[0],M24Bipod::LegWeight(0,T))&&FMath::IsNearlyEqual(P->Angles[1],M24Bipod::LegWeight(1,T));}
        Check(TEXT("reverse hinge sequence 240 Hz"),Sync);
        Table->SetCollisionEnabled(ECollisionEnabled::QueryOnly);D->FindSupport(*P,Support);D->Support=Support;
        FWeaponBipodNetState Proposed;Proposed.Anchor=Support.Anchor;Proposed.FeetA=Support.Feet[0];Proposed.FeetB=Support.Feet[1];
        Check(TEXT("authority accepts physical contacts"),D->ResolveServerSupport(Proposed,Support));
        Proposed.Anchor+=FVector(0,0,100);Check(TEXT("authority rejects unreachable anchor"),!D->ResolveServerSupport(Proposed,Support));
        D->FindSupport(*P,Support);D->Support=Support;Table->AddWorldOffset(FVector(2,0,0));
        Check(TEXT("moving support releases"),!D->SupportStillValid(false));Table->AddWorldOffset(FVector(-2,0,0));
        auto* Profile=LoadObject<UWeaponGripProfile>(nullptr,M24Bipod::Profile);C->WeaponGripProfiles.Add(TEXT("bipod"),Profile);
        Check(TEXT("both magazine clips saved"),Profile&&Profile->Clips.Num()==2&&Profile->Clips[0].Playback()&&Profile->Clips[1].Playback());
        D->bRequested=true;D->Blend=1.f;D->NetDeployment.bActive=false;D->NetDeployment.Sequence=D->LocalSequence;D->NetDeployment.StartedAt=-3.;
        Check(TEXT("unconfirmed support has no handling bonus"),FMath::IsNearlyEqual(D->RecoilMultiplier(),1.f)&&D->BlocksFire());
        D->NetDeployment.bActive=true;D->NetDeployment.WeaponInstance=C->ActiveInventoryWeapon;
        D->ConfirmedDeployment=D->NetDeployment;D->Blend=.5f;
        Check(TEXT("unfolding rifle still blocks fire"),FMath::IsNearlyEqual(D->RecoilMultiplier(),1.f)&&D->BlocksFire());
        D->Blend=1.f;
        Check(TEXT("confirmed seated rifle receives mounted bonus"),FMath::IsNearlyEqual(D->RecoilMultiplier(),.34f,1.e-5f)&&!D->BlocksFire());
        D->Bipod=P;D->PawnAnchor=C->GetActorLocation();D->InitialAim=FRotator::ZeroRotator;D->EntryAimPitch=0.f;
        const FTransform RestFrame=P->GetComponentTransform();
        for(const FRotator& Requested:{FRotator(70,120,0),FRotator(-70,-120,0),FRotator(12,30,0),FRotator(-12,-30,0)})
        {
            D->RestoreCameraOffset();C->FirstPersonCamera->SetWorldLocation(Eye);P->SetWorldTransform(RestFrame);
            PC->SetControlRotation(Requested);D->Advance(0.f);
            const FRotator Limited=PC->GetControlRotation();
            Check(TEXT("camera stays inside shared yaw and pitch limits"),
                FMath::Abs(FRotator::NormalizeAxis(Limited.Yaw))<=D->YawLimitDegrees+.001f
                &&FMath::Abs(FRotator::NormalizeAxis(Limited.Pitch))<=D->PitchLimitDegrees+.001f);
            const FQuat View=Limited.Quaternion();const FQuat Pose=View*Q;
            C->FirstPersonCamera->SetWorldRotation(Limited);
            P->SetWorldTransform(FTransform(Pose,Eye+View.RotateVector(Hinge-Eye)-Pose.RotateVector(M24Bipod::Hinge)));
            D->ApplyPresentation();D->ApplyPresentation(true);
            Check(TEXT("aim limits preserve deployed state and handling bonus"),D->IsDeployed()&&!D->BlocksFire()
                &&FMath::IsNearlyEqual(D->RecoilMultiplier(),.34f,1.e-5f));
            Check(TEXT("deployed legs use authored rest pose without contact IK"),FMath::IsNearlyZero(P->ContactWeight)
                &&P->Angles[0]>.999f&&P->Angles[1]>.999f);
        }
        D->RestoreCameraOffset();PC->SetControlRotation(FRotator::ZeroRotator);
        C->FirstPersonCamera->SetWorldLocationAndRotation(Eye,FRotator::ZeroRotator);P->SetWorldTransform(RestFrame);
        auto* CameraBlock=Box(Eye,FVector(6));D->ApplyPresentation();D->ApplyPresentation(true);
        Check(TEXT("blocked camera correction preserves mount and bonus"),D->IsDeployed()
            &&FMath::IsNearlyEqual(D->RecoilMultiplier(),.34f,1.e-5f)&&D->AppliedCameraOffset.IsNearlyZero());
        CameraBlock->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Report->SetNumberField(TEXT("mounted_recoil"),D->RecoilMultiplier());Report->SetNumberField(TEXT("mounted_weight"),D->HandlingBlend());
        Report->SetNumberField(TEXT("world_time"),World->GetTimeSeconds());Report->SetBoolField(TEXT("is_local"),C->IsLocallyControlled());
        D->bRequested=false;D->NetDeployment.bActive=false;
        auto* Anim=NewObject<UFPSGunplayAnimInstance>(C->AKMViewmodel);
        D->Blend=.5f;C->MagazineAttachmentId=TEXT("none");D->ApplyHandPose(*Anim);Check(TEXT("base magazine selects matching hands"),Anim->ActionClip==Profile->Clips[0].Playback());
        C->MagazineAttachmentId=M24Attachments::ExtendedMagazine;D->ApplyHandPose(*Anim);Check(TEXT("extended magazine selects matching hands"),Anim->ActionClip==Profile->Clips[1].Playback());
        Check(TEXT("half deployment samples authored midpoint"),FMath::IsNearlyEqual(Anim->ActionTime,.24f,1.e-5f));
        Check(TEXT("deployment retains current grip corrections"),Anim->ActionGripProfile==Anim->GripProfile);
        // Keep reload's inventory entry guard closed: this tests the actual queue
        // and transition without changing ammunition or starting profile writes.
        C->MagazineAmmo=C->MagazineCapacity=5;C->ReserveAmmo=0;
        for(const float Dt:{1.f/15,1.f/30,1.f/60,1.f/144,.4f})
        {
            D->Blend=.8f;D->Bipod=P;D->bRequested=false;D->PendingReloadWeapon=C->ActiveInventoryWeapon;
            float Elapsed=0;bool Premature=false;
            while(D->Blend>UE_SMALL_NUMBER&&Elapsed<4.f){D->Advance(Dt);Elapsed+=Dt;if(D->Blend>UE_SMALL_NUMBER&&D->PendingReloadWeapon.IsEmpty())Premature=true;}
            Check(*FString::Printf(TEXT("reload queue completes once, dt %.5f"),Dt),!Premature&&D->Blend==0&&D->PendingReloadWeapon.IsEmpty());
        }
        D->Blend=.5f;D->Bipod=P;D->bRequested=false;D->PendingReloadWeapon=C->ActiveInventoryWeapon;
        C->FireAnimation=NewObject<UAnimSequence>(C);C->ActiveActionAnimation=C->FireAnimation;C->LastShotWorldTime=World->GetTimeSeconds();C->ActionDuration=1.f;
        D->Advance(.4f);Check(TEXT("bolt holds folding and pending reload"),FMath::IsNearlyEqual(D->Blend,.5f)&&!D->PendingReloadWeapon.IsEmpty());
        C->ActiveActionAnimation=nullptr;D->Release(true);Check(TEXT("weapon change clears pending actions"),D->PendingReloadWeapon.IsEmpty()&&!D->bPendingReaim);
        D->Blend=.2f;D->Bipod=P;D->bRequested=false;C->bIsAiming=C->bAimHeld=true;D->bPendingReaim=false;
        D->Advance(1.f);Check(TEXT("support loss does not re-acquire while aim held"),!D->bRequested&&!D->bPendingReaim);
        // Exercise the real owner receipt/RepNotify paths without a socket or
        // player saves. Explicitly model independent RPC/property arrival order.
        FWeaponBipodNetState Accepted;Accepted.Sequence=10;Accepted.bActive=true;
        Accepted.WeaponInstance=C->ActiveInventoryWeapon;Accepted.StartedAt=-3.;
        Accepted.Anchor=Support.Anchor;Accepted.FeetA=Support.Feet[0];Accepted.FeetB=Support.Feet[1];
        D->LocalSequence=10;D->bRequested=true;D->Blend=1.f;D->Bipod=P;
        D->ClientDeploymentResult_Implementation(Accepted);
        Check(TEXT("owner RPC confirms exact weapon generation"),D->IsDeployed());
        D->NetDeployment=Accepted;D->NetDeployment.Sequence=9;D->NetDeployment.bActive=false;D->OnRep_Deployment();
        Check(TEXT("older replicated property preserves newer RPC bonus"),D->IsDeployed()&&D->ConfirmedDeployment.Sequence==10);
        auto Old=Accepted;Old.Sequence=9;Old.bActive=false;D->ClientDeploymentResult_Implementation(Old);
        Check(TEXT("older RPC cannot cancel a newer generation"),D->IsDeployed());
        D->NetDeployment=Accepted;D->NetDeployment.bActive=false;D->OnRep_Deployment();
        Check(TEXT("matching authority release clears mount and bonus"),!D->bRequested&&FMath::IsNearlyEqual(D->RecoilMultiplier(),1.f));
        D->ClientDeploymentResult_Implementation(Accepted);
        Check(TEXT("late acceptance cannot revive released generation"),!D->bRequested);
        D->LocalSequence=11;D->bRequested=true;D->Blend=1.f;D->ConfirmedDeployment=FWeaponBipodNetState();
        D->ClientDeploymentResult_Implementation(Accepted);
        Check(TEXT("previous acceptance cannot confirm a pending new mount"),D->BlocksFire()&&D->HandlingBlend()==0.f);
        Accepted.Sequence=11;Accepted.WeaponInstance=TEXT("previous_m24_instance");
        D->ClientDeploymentResult_Implementation(Accepted);
        Check(TEXT("receipt for a different M24 instance releases prediction"),!D->bRequested);
        D->NetDeployment=FWeaponBipodNetState();D->NetDeployment.Sequence=20;
        D->ServerDeploy_Implementation(21,TEXT("previous_m24_instance"),Support.Feet[0],Support.Feet[1],Support.Anchor,FRotator::ZeroRotator);
        Check(TEXT("authority rejects delayed request for previous M24 instance"),!D->NetDeployment.bActive&&D->NetDeployment.Sequence==21);
        D->ServerRelease_Implementation(20);Check(TEXT("stale cancellation does not rewind authority generation"),D->NetDeployment.Sequence==21);
        D->NetDeployment.Sequence=65535;D->ServerRelease_Implementation(0);
        Check(TEXT("authority cancellation handles sequence wrap"),D->NetDeployment.Sequence==0&&!D->NetDeployment.bActive);
        for(const FString& Definition:{FString(M24WeaponAssets::Definition),FString(PKMLowpolyWeaponAssets::Definition),FString(LMG201WeaponAssets::Definition)})
        {
            const FString Installed=Definition==M24WeaponAssets::Definition?M24Bipod::Id:Definition==PKMLowpolyWeaponAssets::Definition?TEXT("pkm_bipod"):TEXT("false");
            Check(TEXT("authority recognizes installed bipod"),BipodPartInstalled(Definition,Installed));
            Check(TEXT("authority rejects removed or missing bipod"),!BipodPartInstalled(Definition,TEXT("lmg201_no_bipod"))&&!BipodPartInstalled(Definition,TEXT("none"))&&!BipodPartInstalled(Definition,TEXT("")));
        }
        Report->SetNumberField(TEXT("failures"),Failed);Report->SetArrayField(TEXT("cases"),Cases);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Args[0]);
        D->Release(true);World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("M24_BIPOD_NATIVE_REVIEW: %d failures"),Failed);
    }
};
static FAutoConsoleCommand M24BipodValidationCommand(TEXT("fps.m24.ReviewBipod"),TEXT("Opt-in M24 bipod check: output JSON"),FConsoleCommandWithArgsDelegate::CreateStatic(&FM24BipodValidation::Run));
#endif
