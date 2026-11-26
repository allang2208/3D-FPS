#include "ChapelNun.h"
#include "../Characters/FPSOutfitRobeCloth.h"
#include "../Characters/FPSPlayerHeadAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillagePresentationView.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GroomAsset.h"
#include "GroomBindingAsset.h"
#include "GroomComponent.h"
#include "GroomInstance.h"
#include "RenderingThread.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace ChapelNunAssets
{
static const TCHAR* Paths[]={
    TEXT("/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Body.SK_Nun_Body"),
    TEXT("/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_OriginalMeshyFace_Final.SK_Nun_OriginalMeshyFace_Final"),
    TEXT("/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe.SK_Nun_BlackRobe"),
    TEXT("/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_PlainCollar_R7.SK_Nun_PlainCollar_R7"),
    TEXT("/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_Boots.SK_Nun_Boots"),
    TEXT("/Game/Characters/ChapelNun20261115/HairReferenceR5/Grooms/Nun_LowBun_Core_R5.Nun_LowBun_Core_R5"),
    TEXT("/Game/Characters/ChapelNun20261115/HairReferenceR5/Grooms/Nun_LowBun_Core_R5_Binding.Nun_LowBun_Core_R5_Binding"),
    TEXT("/Game/Characters/ChapelNun20261115/HairReferenceR5/Grooms/Nun_LowBun_Loose_R5.Nun_LowBun_Loose_R5"),
    TEXT("/Game/Characters/ChapelNun20261115/HairReferenceR5/Grooms/Nun_LowBun_Loose_R5_Binding.Nun_LowBun_Loose_R5_Binding"),
    TEXT("/Game/Characters/ChapelNun20261115/Animations/A_Nun_Idle_Crossed_R7.A_Nun_Idle_Crossed_R7"),
    TEXT("/Game/Characters/ChapelNun20261115/HairReferenceR5/Materials/MI_Nun_Hair.MI_Nun_Hair"),
    TEXT("/Game/Characters/ChapelNun20261115/NapeHairR10/SK_Nun_NapeHair_R10.SK_Nun_NapeHair_R10")
};
}

AChapelNun::AChapelNun()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickGroup=TG_LastDemotable;
    Collision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("ResidentCollision"));
    Collision->InitCapsuleSize(27.f,84.f);
    Collision->SetCollisionProfileName(TEXT("Pawn"));
    Collision->SetGenerateOverlapEvents(false);
    Collision->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    RootComponent=Collision;
    Body=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("KaitlinBody"));
    Body->SetupAttachment(Collision);
    Body->SetRelativeLocation(FVector(0,0,-84));
    Body->SetRelativeRotation(FRotator(0,FResidentConversationFacing::RestYaw,0));
    Head=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("NunHead"));
    NapeHair=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("NapeHair"));
    NapeHair->SetupAttachment(Head);
    Robe=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("BlackHabit"));
    Trim=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CollarAndCross"));
    Boots=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("RobeBoots"));
    for(auto* Part:{Head.Get(),Robe.Get(),Trim.Get(),Boots.Get()})Part->SetupAttachment(Body);
    for(auto* Part:{Body.Get(),Head.Get(),Robe.Get(),Trim.Get(),Boots.Get(),NapeHair.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetVisibility(false);
        Part->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    }
    HairCore=CreateDefaultSubobject<UGroomComponent>(TEXT("LowBun"));
    HairLoose=CreateDefaultSubobject<UGroomComponent>(TEXT("LooseStrands"));
    for(auto* Hair:{HairCore.Get(),HairLoose.Get()})
    {
        Hair->SetupAttachment(Head);
        Hair->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Hair->SetGenerateOverlapEvents(false);
        Hair->SetVisibility(false);
    }
    Tags.Add(TEXT("NPC"));
    Tags.Add(TEXT("ChapelNun"));
}

void AChapelNun::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
    TArray<FSoftObjectPath> Assets;
    for(const TCHAR* Path:ChapelNunAssets::Paths)Assets.Emplace(Path);
    AppearanceLoad=ATemperateHillsWorld::RequestResidentAppearance(GetWorld(),Assets,
        FStreamableDelegate::CreateUObject(this,&AChapelNun::AssembleAppearance));
}

void AChapelNun::CreateHairCollision()
{
    const auto* Mesh=Head->GetSkeletalMeshAsset();
    if(!Mesh)return;
    const auto& Ref=Mesh->GetRefSkeleton();
    TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)
        if(const int32 Parent=Ref.GetParentIndex(I);Parent>=0)Frames[I]*=Frames[Parent];
    HairCollision=NewObject<UPhysicsAsset>(this,TEXT("NunHairHeadCollision"),RF_Transient);
    auto Capsule=[&](FName Name,const FVector& Center,float Radius,float Length)
    {
        const int32 Index=Ref.FindBoneIndex(Name);if(!Frames.IsValidIndex(Index))return;
        auto* Setup=NewObject<USkeletalBodySetup>(HairCollision);
        Setup->BoneName=Name;Setup->PhysicsType=PhysType_Kinematic;
        FKSphylElem Shape;
        Shape.Center=Frames[Index].InverseTransformPosition(Center);
        Shape.Rotation=FRotationMatrix::MakeFromZ(Frames[Index].InverseTransformVectorNoScale(FVector::UpVector)).Rotator();
        Shape.Radius=Radius;Shape.Length=Length;
        Setup->AggGeom.SphylElems.Add(Shape);
        HairCollision->SkeletalBodySetups.Add(Setup);
    };
    // Authored in the fitted nun head's native centimetre frame.
    Capsule(TEXT("head"),FVector(0,.5,158.7),7.1f,3.6f);
    Capsule(TEXT("neck_02"),FVector(0,1.,146.1),3.6f,3.0f);
    HairCollision->UpdateBodySetupIndexMap();
    HairCollision->UpdateBoundsBodiesArray();
    Head->SetPhysicsAsset(HairCollision,true);
}

void AChapelNun::AssembleAppearance()
{
    if(IsActorBeingDestroyed()||!HasActorBegunPlay())return;
    auto Resolve=[](int32 I){return FSoftObjectPath(ChapelNunAssets::Paths[I]).ResolveObject();};
    USkeletalMeshComponent* Parts[]={Body,Head,Robe,Trim,Boots};
    for(int32 I=0;I<5;++I)
    {
        auto* Mesh=Cast<USkeletalMesh>(Resolve(I));
        if(!Mesh){UE_LOG(LogTemp,Error,TEXT("CHAPEL_NUN missing asset %s"),ChapelNunAssets::Paths[I]);return;}
        Parts[I]->SetSkeletalMeshAsset(Mesh);
    }
    auto* Idle=Cast<UAnimSequence>(Resolve(9));
    auto* Core=Cast<UGroomAsset>(Resolve(5));auto* CoreBinding=Cast<UGroomBindingAsset>(Resolve(6));
    auto* Loose=Cast<UGroomAsset>(Resolve(7));auto* LooseBinding=Cast<UGroomBindingAsset>(Resolve(8));
    if(!Idle||!Core||!CoreBinding||!Loose||!LooseBinding)
    {UE_LOG(LogTemp,Error,TEXT("CHAPEL_NUN animation or groom assets unavailable"));return;}
    ConversationFacing.StartIdle(*Body,*Idle);
    Head->SetAnimInstanceClass(UFPSPlayerHeadAnimInstance::StaticClass());
    Head->AddTickPrerequisiteComponent(Body);
    // Hair collision capsules must not replace the authored face visibility bounds.
    Head->bComponentUseFixedSkelBounds=true;
    if(auto* NapeMesh=Cast<USkeletalMesh>(Resolve(11)))
    {
        NapeHair->SetSkeletalMeshAsset(NapeMesh);
        NapeHair->SetLeaderPoseComponent(Head);
        NapeHair->bUseAttachParentBound=true;
        NapeHair->SetComponentTickEnabled(false);
        NapeHair->SetVisibility(true);
    }
    for(auto* Part:{Trim.Get(),Boots.Get()})
    {
        Part->SetLeaderPoseComponent(Body);
        Part->SetComponentTickEnabled(false);
        Part->bUseAttachParentBound=false;
    }
    // These are the retained native robe inner-layer sections, not missing legs.
    const TArray<int32> Covered={0,1,3,7,8,9,10,14};
    BodyInner.Initialize(Body,Covered);
    BodyInner.Apply(false);
    BootInner.Initialize(Boots,{});
    BootInner.Apply(false);
    // The complete boot mesh covers the native bare feet in every LOD.
    const auto& Mats=Body->GetSkeletalMeshAsset()->GetMaterials();
    for(int32 I=0;I<Mats.Num();++I)
    {
        const FString Slot=Mats[I].MaterialSlotName.ToString();
        if(Slot==TEXT("SkinBoots_12")||Slot==TEXT("SkinArmoredBoot_12")||
           Slot==TEXT("RobeStairHidden_12")||Slot==TEXT("RobeStairHidden_15")||Slot==TEXT("RobeStairHidden_16"))
            for(int32 Lod=0;Lod<Body->GetSkeletalMeshAsset()->GetLODNum();++Lod)Body->ShowMaterialSection(I,INDEX_NONE,false,Lod);
    }
    CuffMotion.Initialize(Body,Robe,true);
    // Initialize after cuff materials: a simulated skirt must retain its own pose tick.
    FPSOutfitRobeCloth::Initialize(Robe,Body);
    HemEnvelope.Initialize(Robe);
    PrimaryActorTick.AddPrerequisite(Body,Body->PrimaryComponentTick);
    PrimaryActorTick.AddPrerequisite(Robe,Robe->PrimaryComponentTick);
    PrimaryActorTick.AddPrerequisite(Robe,Robe->ClothTickFunction);
    PrimaryActorTick.AddPrerequisite(Robe,Robe->ClothEndTickFunction);
    CreateHairCollision();
    HairCore->SetGroomAsset(Core,CoreBinding,false);
    HairLoose->SetGroomAsset(Loose,LooseBinding,false);
    for(auto* Hair:{HairCore.Get(),HairLoose.Get()})
    {
        Hair->SimulationSettings.SimulationSetup.LocalBone=TEXT("head");
        Hair->SimulationSettings.SimulationSetup.bLocalSimulation=true;
        Hair->SimulationSettings.SimulationSetup.LinearVelocityScale=.35f;
        Hair->SimulationSettings.SimulationSetup.AngularVelocityScale=.35f;
        if(auto* Material=Cast<UMaterialInterface>(Resolve(10)))Hair->SetMaterial(0,Material);
        Hair->AddTickPrerequisiteComponent(Head);
    }
    HairLoose->AddCollisionComponent(Head);
    HairLoose->AddCollisionComponent(Body);
    for(auto* Part:Parts)Part->SetVisibility(true);
    HairCore->SetVisibility(true);HairLoose->SetVisibility(true);
    bAppearanceReady=true;SetActorTickEnabled(true);
}

void AChapelNun::UpdateCoreHairDetail(double EffectiveDistance)
{
    // This groom has one continuous strands group and no cards. Keep its authored bias at close range.
    FHairGroupInstance* Group=HairCore->GetGroupInstance(0);
    if(!Group)
    {
        BudgetedCoreGroup.SafeRelease();
        CoreHairTier=INDEX_NONE;
        return;
    }
    const double FarBoundary=CoreHairTier==2?1800.:2100.;
    const double MidBoundary=CoreHairTier>0?750.:900.;
    const int32 Tier=EffectiveDistance>=FarBoundary?2:EffectiveDistance>=MidBoundary?1:0;
    if(Tier==CoreHairTier && BudgetedCoreGroup.GetReference()==Group)return;

    CoreHairTier=Tier;
    BudgetedCoreGroup=Group;
    const float AuthoredBias=HairCore->GroomAsset->GetAutoLODBias(0);
    const float Bias=AuthoredBias-(Tier==2?.016f:Tier==1?.008f:0.f);
    // The component can recreate its group on re-registration. Hold this instance until the render command runs.
    ENQUEUE_RENDER_COMMAND(NunCoreStrandDetail)(
        [Instance=TRefCountPtr<FHairGroupInstance>(Group),Bias](FRHICommandListImmediate&)
        {
            if(FHairGroupPublicData* Data=Instance->HairGroupPublicData;Data && Data->bAutoLOD)
                Data->AutoLODBias=Bias;
        });
}

void AChapelNun::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!bAppearanceReady)return;
    bool HasView=false;
    const double Distance=VillagePresentationView::Distance(*GetWorld(),GetActorLocation(),0.,&HasView);
    UpdateCoreHairDetail(HasView?Distance:0.);
    const float DistanceSquared=HasView?float(FMath::Square(Distance)):MAX_flt;
    FPSOutfitRobeCloth::UpdateAtDistance(Robe,Delta,DistanceSquared);
    const float Radius=bLooseHairActive?2200.f:1800.f;
    const bool Active=DistanceSquared<Radius*Radius;
    if(Active!=bLooseHairActive)
    {
        bLooseHairActive=Active;
        HairLoose->SetVisibility(Active);
        HairLoose->SetComponentTickEnabled(Active);
        if(auto* Solver=HairLoose->GetNiagaraComponent(0))Solver->SetPaused(!Active);
        if(Active)HairLoose->ResetSimulation();
    }
    const bool Resting=DistanceSquared>FMath::Square(3600.f)&&Robe->IsClothingSimulationSuspended()
        &&!Body->WasRecentlyRendered(1.f)&&!Robe->WasRecentlyRendered(1.f);
    if(Resting!=(GetActorTickInterval()>0.f))
    {
        SetActorTickInterval(Resting?.25f:0.f);
        for(auto* Part:{Body.Get(),Head.Get(),Robe.Get()})
            Part->VisibilityBasedAnimTickOption=Resting?EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered:
                EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    }
    if(Resting)return;
    CuffMotion.Tick(Delta);
    HemEnvelope.Update(false,Delta);
    BodyInner.Conform(HemEnvelope);
    BootInner.Conform(HemEnvelope);
}

void AChapelNun::EndPlay(const EEndPlayReason::Type Reason)
{
    BudgetedCoreGroup.SafeRelease();
    if(AppearanceLoad){AppearanceLoad->CancelHandle();AppearanceLoad.Reset();}
    Super::EndPlay(Reason);
}

void AChapelNun::SetLocalConversation(APlayerController* Player)
{
    ConversationFacing.SetLocalPlayer(Player);
}
