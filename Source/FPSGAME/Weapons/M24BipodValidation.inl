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
        D->Support=Support;Check(TEXT("retained support"),D->SupportStillValid(true));
        Table->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("removed support is rejected"),!D->SupportStillValid(true)&&!D->FindSupport(*P,Support));
        Table->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        auto* Block=Box(Hinge+FVector(50,0,3.1),FVector(3,50,30));
        Check(TEXT("long barrel obstruction"),!D->ClearPlacement(Eye,FVector::ZeroVector,Hinge,FVector::ForwardVector));
        Check(TEXT("blocked mount cannot be acquired"),!D->FindSupport(*P,Support));
        Block->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("camera correction obstruction"),!D->ClearPlacement(Eye,FVector(0,0,Top-Eye.Z),Hinge,FVector::ForwardVector));
        Table->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* Sole=Box(A-FVector(0,0,1),FVector(1.5,1.5,1));
        Check(TEXT("single foot cannot mount"),!D->FindSupport(*P,Support));Sole->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* Slope=Box(FVector(65,0,Top-5),FVector(120,90,5),FRotator(35,0,0));
        Check(TEXT("steep support rejected"),!D->FindSupport(*P,Support));Slope->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        auto* High=Box(FVector(70,0,Top+90),FVector(100,80,5));
        Check(TEXT("out of height reach"),!D->FindSupport(*P,Support));High->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Check(TEXT("native contacts reachable"),P->CanReachContacts(A,B,FVector::ZeroVector));
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
        Proposed.Anchor+=FVector(0,0,25);Check(TEXT("authority rejects unreachable anchor"),!D->ResolveServerSupport(Proposed,Support));
        D->FindSupport(*P,Support);D->Support=Support;Table->AddWorldOffset(FVector(2,0,0));
        Check(TEXT("moving support releases"),!D->SupportStillValid(false));Table->AddWorldOffset(FVector(-2,0,0));
        auto* Profile=LoadObject<UWeaponGripProfile>(nullptr,M24Bipod::Profile);C->WeaponGripProfiles.Add(TEXT("bipod"),Profile);
        Check(TEXT("both magazine clips saved"),Profile&&Profile->Clips.Num()==2&&Profile->Clips[0].Playback()&&Profile->Clips[1].Playback());
        D->bRequested=true;D->Blend=1.f;D->NetDeployment.bActive=true;D->NetDeployment.Sequence=D->LocalSequence;D->NetDeployment.StartedAt=-3.;
        D->bM24PlacementReady=false;Check(TEXT("unseated rifle has no handling bonus"),FMath::IsNearlyEqual(D->RecoilMultiplier(),1.f)&&D->BlocksFire());
        D->bM24PlacementReady=true;Check(TEXT("confirmed seated rifle receives mounted bonus"),FMath::IsNearlyEqual(D->RecoilMultiplier(),.34f,1.e-5f)&&!D->BlocksFire());
        Report->SetNumberField(TEXT("mounted_recoil"),D->RecoilMultiplier());Report->SetNumberField(TEXT("mounted_weight"),D->HandlingBlend());
        Report->SetNumberField(TEXT("world_time"),World->GetTimeSeconds());Report->SetBoolField(TEXT("is_local"),C->IsLocallyControlled());
        D->bRequested=false;D->NetDeployment.bActive=false;
        auto* Anim=NewObject<UFPSGunplayAnimInstance>(C->AKMViewmodel);
        D->Blend=.5f;C->MagazineAttachmentId=TEXT("none");D->ApplyHandPose(*Anim);Check(TEXT("base magazine selects matching hands"),Anim->ActionClip==Profile->Clips[0].Playback());
        C->MagazineAttachmentId=M24Attachments::ExtendedMagazine;D->ApplyHandPose(*Anim);Check(TEXT("extended magazine selects matching hands"),Anim->ActionClip==Profile->Clips[1].Playback());
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
        Report->SetNumberField(TEXT("failures"),Failed);Report->SetArrayField(TEXT("cases"),Cases);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Args[0]);
        D->Release(true);World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("M24_BIPOD_NATIVE_REVIEW: %d failures"),Failed);
    }
};
static FAutoConsoleCommand M24BipodValidationCommand(TEXT("fps.m24.ReviewBipod"),TEXT("Opt-in M24 bipod check: output JSON"),FConsoleCommandWithArgsDelegate::CreateStatic(&FM24BipodValidation::Run));
#endif
