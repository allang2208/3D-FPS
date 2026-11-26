#include "BowSkillTrainingAuditCommandlet.h"
#include "FPSQuickCombatComponent.h"
#include "ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowQuickCombatMotion.h"
#include "../Weapons/Bow/BowScopeOptics.h"
#include "../Weapons/Bow/BowArmsMeshComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Bow/CadenceString.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

namespace FPSBodyNetwork { bool IsTransition(const FFPSBodyState& A,const FFPSBodyState& B); }
namespace BowPresentationReview
{
int32 Forwarded=0;
bool Forward(AActor*,const FHitResult&,float,const FVector&,const FColdSteelSkillShot&)
{++Forwarded;return true;}
}

int32 UBowSkillTrainingAuditCommandlet::RunBowPresentationReview(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("BowSkillAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("BowSkillTrainingAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("BowPresentationReview"));
    auto* W=GI->GetWorld();auto* M=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!W||!M||!M->IsAudit()||M->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    const auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Row->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(Row));Failed+=!OK;
        UE_LOG(LogTemp,Display,TEXT("BOW_PRESENTATION_REVIEW %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=M->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    auto Item=M->CreateItem(TEXT("bow_woodsteel"));Item.Place=1;Item.Cell=6;Seed.Items.Add(Item);
    M->Current=Seed;
    auto CadenceItem=Item;TSharedPtr<FJsonObject> CadenceData;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CadenceItem.Data),CadenceData);
    if(!CadenceData)CadenceData=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("string"),CadenceString::Option);CadenceData->SetObjectField(TEXT("gunsmith_parts"),Parts);
    FJsonSerializer::Serialize(CadenceData.ToSharedRef(),TJsonWriterFactory<>::Create(&CadenceItem.Data));
    const auto BaseStats=ColdSteelBow::Evaluate(Item,M),CadenceStats=ColdSteelBow::Evaluate(CadenceItem,M);
    Check(FMath::IsNearlyEqual(CadenceStats.RhythmWindow,BaseStats.RhythmWindow*2.,.00001)
        &&FMath::IsNearlyEqual(CadenceStats.Draw,BaseStats.Draw,.00001),TEXT("cadence passive doubles rhythm window without old passive draw speed"),
        FString::Printf(TEXT("window %.3f -> %.3f, draw %.3f -> %.3f"),BaseStats.RhythmWindow,CadenceStats.RhythmWindow,BaseStats.Draw,CadenceStats.Draw));
    Check(CadenceString::StackSeconds==6.f&&CadenceString::MaximumStacks==5
        &&FMath::IsNearlyEqual(CadenceString::MaximumStacks*CadenceString::SpeedPerStack,1.f),TEXT("cadence current tuning is six seconds and five stacks totaling 100 percent speed"));
    auto* PC=W->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    auto* Pawn=W->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Pawn);M->CurrentPawn=Pawn;
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Bow=Pawn->FindComponentByClass<UBowWeaponComponent>();auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    Bow->Character=Pawn;Bow->Camera=Pawn->FirstPersonCamera;Bow->InstanceId=Item.InstanceId;Bow->EquippedDefinition=Item.Definition;
    auto* Clip=LoadObject<UAnimSequence>(nullptr,BowQuickCombatMotion::Asset);
    Check(Clip&&FMath::IsNearlyEqual(Clip->GetPlayLength(),BowQuickCombatMotion::Length,.01f),TEXT("saved shared quick-melee clip resolves with authored duration"));
    const float Length=Clip?Clip->GetPlayLength():BowQuickCombatMotion::Length;
    const auto ResetQuick=[&]()
    {
        Quick->Cancel();Quick->ConfigureForBow(Length);Quick->ActionRate=1.f;
        Quick->Phase=EQuickCombatBashPhase::Smash;Quick->ActionAge=Quick->ContactTime;
        Quick->bContactDone=true;Quick->ImpactAge=1.f;Quick->ImpactStrength=0.f;
    };
    bool RoundTrip=true;
    for(float Scale:{.5f,1.f,2.f})for(int32 I=0;I<=100;++I)
    {
        const float L=Length*Scale,T=L*I/100.f;
        RoundTrip&=FMath::IsNearlyEqual(T,BowQuickCombatMotion::SourceSeconds(BowQuickCombatMotion::PlaybackSeconds(T,L),L),.00001f);
    }
    Check(RoundTrip,TEXT("source and playback clocks round-trip across all segments and clip scales"));

    // Exercise the actual owner contact path with the production forward hook:
    // a client submits damage and receives zero locally, without changing health.
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    auto* Target=W->SpawnActor<ANurseZombie>(Aim.TransformPosition(FVector(70,0,0)),FRotator::ZeroRotator);
    Target->Knockdown=nullptr;Target->Health=Target->MaxHealth=10000.f;
    Target->GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Target->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Target->GetCapsuleComponent()->SetCollisionResponseToAllChannels(ECR_Block);
    const auto PreviousForward=ColdSteelSkills::NetHitForward();
    ColdSteelSkills::NetHitForward()=&BowPresentationReview::Forward;BowPresentationReview::Forwarded=0;
    Pawn->SetRole(ROLE_AutonomousProxy);ResetQuick();Quick->ContactHit();
    Check(BowPresentationReview::Forwarded==1&&Target->Health==10000.f,TEXT("client contact forwards once without local damage"));
    Check(Quick->IsImpactPaused()&&Quick->GetBowSourcePlaybackRate()==0.f,TEXT("client contact starts hit stop while authority result is pending"));
    Quick->AdvanceAction(.02f);
    Check(FMath::IsNearlyEqual(Quick->ActionAge,Quick->ContactTime)&&Quick->IsImpactPaused(),TEXT("contact frame stays frozen inside 45 ms stop"));
    Quick->AdvanceAction(.04f);
    Check(Quick->ActionAge>Quick->ContactTime&&Quick->GetBowSourcePlaybackRate()>0.f&&Quick->GetBowRecoilCM()<0.f,
        TEXT("client resumes authored follow-through with recoil"));
    Check(BowPresentationReview::Forwarded==1,TEXT("recovery does not repeat hit submission"));
    Quick->Cancel();Check(!Quick->IsOccupyingLeftHand()&&Quick->GetBowRecoilCM()==0.f&&!Quick->IsImpactPaused(),TEXT("cancellation clears predicted feedback"));
    ColdSteelSkills::NetHitForward()=PreviousForward;Pawn->SetRole(ROLE_Authority);
    Target->SetActorLocation(FVector(5000,0,500));
    ResetQuick();Quick->ContactHit();Check(!Quick->IsImpactPaused()&&Quick->ImpactStrength==0.f,TEXT("miss has no hit stop or recoil"));
    auto* Wall=W->SpawnActor<AActor>(Aim.TransformPosition(FVector(70,0,0)),FRotator::ZeroRotator);
    auto* Box=NewObject<UBoxComponent>(Wall);Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(10,100,100));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();
    Wall->SetActorLocation(Aim.TransformPosition(FVector(70,0,0)));
    ResetQuick();Quick->ContactHit();Check(Quick->IsImpactPaused()&&Quick->ImpactStrength==.8f,TEXT("solid obstruction uses reduced resistance without damage submission"));
    Wall->Destroy();
    ResetQuick();Quick->ImpactAge=.02f;Quick->ImpactStrength=1.f;Quick->AdvanceAction(.5f);
    Check(!Quick->IsOccupyingLeftHand(),TEXT("hitch consumes remaining hit stop and finishes recovery"));
    ResetQuick();Quick->ImpactStrength=1.f;Quick->ImpactAge=.08f;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();Body->Character=Pawn;FFPSBodyState State;Bow->Stage=EBowStage::QuickCombat;
    Body->SampleBowState(*Bow,State);
    Check(State.BowClipRate==Quick->GetBowSourcePlaybackRate(),TEXT("body samples executor playback speed instead of fixed one-times rate"));
    Quick->Cancel();Bow->Stage=EBowStage::Ready;

    FFPSBodyState Moving;Moving.Family=TEXT("Bow");Moving.BowClip=TEXT("QuickCombat");Moving.BowClipTime=Quick->ContactTime;
    Moving.BowClipLength=Length;Moving.BowClipRate=2.f;Moving.PresentationSampledAt=10.f;
    auto Stopped=Moving;Stopped.BowClipRate=0.f;
    Check(FPSBodyNetwork::IsTransition(Stopped,Moving),TEXT("hit stop begins with reliable body transition"));
    Check(FPSBodyNetwork::IsTransition(Moving,Stopped),TEXT("hit stop resume uses reliable body transition"));
    auto ChangedRate=Moving;ChangedRate.BowClipRate=1.5f;
    Check(!FPSBodyNetwork::IsTransition(ChangedRate,Moving),TEXT("ordinary positive rate changes do not flood reliable channel"));
    UFPSPlayerBodyComponent::AdvanceBodyPresentation(Stopped,10.1f);
    Check(Stopped.BowClipTime==Moving.BowClipTime,TEXT("remote paused clip does not extrapolate through contact"));
    UFPSPlayerBodyComponent::AdvanceBodyPresentation(Moving,10.1f);
    Check(FMath::IsNearlyEqual(Moving.BowClipTime,Quick->ContactTime+.2f,.00001f),TEXT("remote moving clip uses transmitted source rate"));

    // Viewport-independent owner camera ownership and lifecycle checks. The
    // actual physical lens, HUD composition and art need a rendered client.
    if(!PC->PlayerCameraManager)
    {PC->PlayerCameraManager=W->SpawnActor<APlayerCameraManager>();PC->PlayerCameraManager->InitializeFor(PC);}
    PC->SetViewTarget(Pawn);PC->bShowMouseCursor=false;
    Bow->Pivot=NewObject<USceneComponent>(Pawn);Bow->Pivot->SetupAttachment(Pawn->FirstPersonCamera);Bow->Pivot->RegisterComponent();
    auto* Part=NewObject<UBoxComponent>(Pawn);Part->SetupAttachment(Bow->Pivot);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->RegisterComponent();
    Bow->bPresentationReady=true;Bow->bHasAimSight=Bow->bPeakwatchScope=true;Bow->AimProgress=1.f;
    Bow->OpticalMinimum=3.f;Bow->OpticalMaximum=6.f;
    auto* Optics=NewObject<UBowScopeOptics>(Bow);
    auto* Camera=Pawn->FirstPersonCamera.Get();
    Camera->SetEnableFirstPersonFieldOfView(false);Camera->SetFirstPersonFieldOfView(87.f);
    Bow->DisplayedOpticalMagnification=3.f;Optics->UpdateCamera(*Bow);
    Check(Camera->bEnableFirstPersonFieldOfView&&Optics->OwnsPrimitive(Part),TEXT("scope acquires only owner bow primitives"),
        FString::Printf(TEXT("local=%d target=%d present=%d scope=%d third=%d alpha=%.3f"),Pawn->IsLocallyControlled(),PC->GetViewTarget()==Pawn,
            Bow->CanPresent(true),Bow->IsScopeOpticalPresentationEnabled(),Body->IsThirdPersonViewEnabled(),Bow->AimAlpha()));
    const float Framing=Camera->FirstPersonFieldOfView,FOV3=Bow->AimVerticalFOV(90.f),LensFOV3=Bow->OpticalAimVerticalFOV(90.f);
    Bow->DisplayedOpticalMagnification=6.f;Optics->UpdateCamera(*Bow);
    Check(Framing==Camera->FirstPersonFieldOfView&&Bow->AimVerticalFOV(90.f)==FOV3&&Bow->OpticalAimVerticalFOV(90.f)<LensFOV3,
        TEXT("zoom changes only lens magnification while peripheral and viewmodel framing stay fixed"));

    // A custom, unbound glass finish is part of world equipment. The scope
    // scene tracks its temporary capture overlay separately while ADS is active.
    Bow->Viewmodel=NewObject<UBowArmsMeshComponent>(Pawn);
    Bow->Viewmodel->SetSkeletalMeshAsset(LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7.SK_Bow_BareArmsV7")));
    auto* Sight=NewObject<UBowPartComponent>(Pawn);Sight->InitializeAsPart(Pawn,TEXT("sight"),Bow->Pivot);
    Sight->SetMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V12/SM_Highland_Peakwatch3to6.SM_Highland_Peakwatch3to6")));
    Bow->Parts.Add(TEXT("sight"),Sight);Bow->SlotOrder.AddUnique(TEXT("sight"));
    auto* Lens=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens.M_PhysicalScopeLens"));
    const int32 Glass=Sight->FindMaterialSlot(TEXT("M_Peakwatch_Glass"));
    if(Lens&&Glass!=INDEX_NONE)Sight->GetVisual()->SetMaterial(Glass,UMaterialInstanceDynamic::Create(Lens,Pawn));
    FFPSBodyWeapon Captured;Body->CaptureBow(*Bow,Captured);
    const auto* CapturedSight=Captured.Parts.FindByPredicate([](const auto& P){return P.Slot==TEXT("sight");});
    Check(Lens&&Sight->GetMesh()&&Glass!=INDEX_NONE&&CapturedSight&&CapturedSight->Materials.IsValidIndex(Glass)
        &&CapturedSight->Materials[Glass].Get()==Lens,
        TEXT("world equipment preserves the parent of an unbound custom glass finish"));
    if(Glass!=INDEX_NONE)Sight->GetVisual()->SetMaterial(Glass,nullptr);
    FFPSBodyWeapon Factory;Body->CaptureBow(*Bow,Factory);
    const auto* FactorySight=Factory.Parts.FindByPredicate([](const auto& P){return P.Slot==TEXT("sight");});
    Check(Sight->GetMesh()&&Glass!=INDEX_NONE&&FactorySight&&FactorySight->Materials.IsValidIndex(Glass)
        &&FactorySight->Materials[Glass].Get()==Sight->GetMesh()->GetMaterial(Glass),
        TEXT("world equipment publishes authored glass when the custom finish is removed"));
    auto* Ring=NewObject<UBowPartComponent>(Pawn);Ring->InitializeAsPart(Pawn,TEXT("sight_zoom"),Bow->Pivot);
    Bow->Parts.Add(TEXT("sight_zoom"),Ring);Bow->SlotOrder.AddUnique(TEXT("sight_zoom"));
    Bow->ScopeRingRotation=FRotator(0,0,12);Bow->ScopeRingDegreesPerPower=30;
    Ring->SetRelativeRotation(FRotator(0,0,102));
    FFPSBodyState ZoomState;Body->SampleBowState(*Bow,ZoomState);FFPSBodyWeapon StableEquipment;Body->CaptureBow(*Bow,StableEquipment);
    const auto* RingDescription=StableEquipment.Parts.FindByPredicate([](const auto& P){return P.Slot==TEXT("sight_zoom");});
    Check(FMath::IsNearlyEqual(ZoomState.BowScopeRingRoll,102.f)&&RingDescription&&
        FMath::IsNearlyEqual(float(RingDescription->RelativeTransform.Rotator().Roll),12.f),
        TEXT("zoom ring carries actual roll in pose while equipment mount remains stable"));
    PC->bShowMouseCursor=true;Optics->UpdateCamera(*Bow);
    Check(!Camera->bEnableFirstPersonFieldOfView&&Camera->FirstPersonFieldOfView==87.f&&!Optics->OwnsPrimitive(Part),TEXT("opening menu restores camera and releases primitive ownership"));
    PC->bShowMouseCursor=false;Part->SetOwnerNoSee(true);const bool VisibleBefore=Part->IsVisible();
    Optics->UpdateCamera(*Bow);Optics->Release(*Bow);
    Check(Part->bOwnerNoSee&&Part->IsVisible()==VisibleBefore,TEXT("scope release preserves pre-existing owner hide without hiding world pose source"),
        FString::Printf(TEXT("owner hide %d, visible %d -> %d"),Part->bOwnerNoSee,VisibleBefore,Part->IsVisible()));
    Part->SetOwnerNoSee(false);Optics->UpdateCamera(*Bow);Bow->InstanceId.Reset();Optics->UpdateCamera(*Bow);
    Check(!Camera->bEnableFirstPersonFieldOfView&&!Optics->OwnsPrimitive(Part),TEXT("unequip releases scope camera state"));
    Bow->InstanceId=Item.InstanceId;
    auto* RPC=W->SpawnActor<ABowSkillAuditRemoteController>();PC->UnPossess();RPC->Possess(Pawn);Optics->UpdateCamera(*Bow);
    Check(!Camera->bEnableFirstPersonFieldOfView&&!Optics->OwnsPrimitive(Part),TEXT("remote pawn cannot acquire local scope camera"));

    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failed"),Failed);
    Root->SetBoolField(TEXT("actual_socket_transport"),false);Root->SetBoolField(TEXT("gameplay_map_started"),false);
    Root->SetBoolField(TEXT("visual_or_audio_acceptance"),false);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));FString Dir;
    FParse::Value(*Params,TEXT("ReportDir="),Dir);if(Dir.IsEmpty())Dir=FPaths::ProjectSavedDir()/TEXT("BowPresentationReview20261028");
    IFileManager::Get().MakeDirectory(*Dir,true);FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("presentation-checks.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("BOW_PRESENTATION_REVIEW_DONE checks=%d failed=%d"),Rows.Num(),Failed);
    M->CurrentPawn.Reset();TArray<AActor*> Actors;for(TActorIterator<AActor> It(W);It;++It)Actors.Add(*It);
    for(auto* A:Actors)if(IsValid(A))A->Destroy();
    GI->Shutdown();GEngine->DestroyWorldContext(W);W->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failed?1:0;
}
