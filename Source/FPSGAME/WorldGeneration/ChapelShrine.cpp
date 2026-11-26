#include "ChapelShrine.h"
#include "ChapelNavigationGeometry.h"
#include "HillsNightRaidSubsystem.h"
#include "../Dungeons/RandomShrine.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

namespace
{
    const FSoftObjectPath PedestalPath(TEXT("/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal.SM_ChapelShrineRockPedestal"));
    constexpr double StatueScale=2.;
    constexpr double PedestalAuthoredRadius=220.;
    constexpr double RootHeight=100.;
    constexpr double PedestalBedDepth=4.;
    // Diana's saved geometry starts 0.885 cm above its doubled mesh bounds.
    // A shallow seat removes the gap for every shrine without altering assets.
    constexpr double StatueSeatDepth=1.;
}

void AChapelShrine::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    Paths.AddUnique(PedestalPath);
}

AChapelShrine::AChapelShrine()
{
    bReplicates=true;bAlwaysRelevant=true;SetReplicateMovement(true);
    AutoPossessAI=EAutoPossessAI::Disabled;
    Body=CreateDefaultSubobject<UCapsuleComponent>(TEXT("WardBody"));
    SetRootComponent(Body);Body->InitCapsuleSize(52.f,100.f);
    Body->SetCollisionProfileName(TEXT("Pawn"));
    Body->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    Body->SetCanEverAffectNavigation(false);
    Statue=CreateDefaultSubobject<UChapelStatueNavMesh>(TEXT("Statue"));
    Statue->SetupAttachment(Body);Statue->SetRelativeLocation(FVector(0,0,-100));
    Statue->SetMobility(EComponentMobility::Movable);
    Statue->SetCollisionProfileName(TEXT("BlockAll"));
    Statue->SetGenerateOverlapEvents(false);
    PrimaryActorTick.bCanEverTick=false;
}

void AChapelShrine::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(AChapelShrine,WorldSeed,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AChapelShrine,WorldId,COND_InitialOnly);
    DOREPLIFETIME(AChapelShrine,Durability);
    DOREPLIFETIME(AChapelShrine,MaxDurability);
    DOREPLIFETIME(AChapelShrine,bRaidNight);
}

void AChapelShrine::BeginPlay()
{
    Super::BeginPlay();OnRep_Identity();
    if(HasAuthority())UNavigationSystemV1::RegisterNavigationInvoker(*this,14000.f,16000.f);
}

FVector AChapelShrine::GetNavAgentLocation() const { return GetActorLocation()-FVector(0,0,100); }

FVector AChapelShrine::GetRaidTargetPoint(const FVector& From) const
{
    if(RaidPedestal&&RaidPedestal->IsRegistered())
    {
        const FBox Bounds=RaidPedestal->Bounds.GetBox();
        FVector End=Bounds.GetCenter();
        End.Z=FMath::Clamp(From.Z,Bounds.Min.Z+1.,Bounds.Max.Z-1.);
        FVector Start=From;Start.Z=End.Z;
        FHitResult Hit;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(RaidShrineSurface),true);
        // A horizontal component-only trace finds the real near stone surface.
        // A chest-to-center diagonal instead hits the top near the middle and
        // recreates the old center-distance error on a broad, low pedestal.
        if(RaidPedestal->LineTraceComponent(Hit,Start,End,Query))return Hit.ImpactPoint;
    }
    return GetActorLocation();
}

void AChapelShrine::SetRaidNight(bool Night,float Maximum)
{
    if(!HasAuthority())return;
    MaxDurability=FMath::Max(1.f,Maximum);
    const bool Restore=!Night&&(bRaidNight||IsDormant()||Durability!=MaxDurability);
    bRaidNight=Night;
    if(Restore){Durability=MaxDurability;OnRep_Ward();}
    ForceNetUpdate();
}

void AChapelShrine::RestoreWard(float Health,float Maximum,bool Night)
{
    if(!HasAuthority())return;
    MaxDurability=FMath::Max(1.f,Maximum);Durability=FMath::Clamp(Health,0.f,MaxDurability);
    bRaidNight=Night;OnRep_Ward();ForceNetUpdate();
}

float AChapelShrine::TakeDamage(float Damage,const FDamageEvent&,AController*,AActor* Causer)
{
    if(!HasAuthority()||!CanBeSieged()||Damage<=0.f||!IsValid(Causer)
        ||!Causer->ActorHasTag(TEXT("HillsNightRaider")))return 0.f;
    const auto* Combat=Causer->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat||Combat->IsDead())return 0.f;
    const float Applied=FMath::Min(Durability,Damage);
    Durability-=Applied;ForceNetUpdate();
    if(IsDormant())
    {OnRep_Ward();if(auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>())Raid->Checkpoint();}
    return Applied;
}

void AChapelShrine::OnRep_Ward()
{
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get())if(APawn* Pawn=PC->GetPawn())UStatusEffectsComponent::Notify(Pawn);
}

void AChapelShrine::OnRep_Identity()
{
    if(!HasActorBegunPlay()||!WorldId.IsValid()||bBound||MeshLoad)return;
    FRandomStream Random(int32(uint32(WorldSeed)^DungeonRunDomains::ShrineSelection));
    const auto Choice=RandomShrine::Choose(Random);
    if(!Choice)return;
    TArray<FSoftObjectPath> Paths{FSoftObjectPath(Choice->GetStringField(TEXT("mesh")))};
    AddAssetPaths(Paths);
    if(Paths[0].ResolveObject()&&PedestalPath.ResolveObject()){BindShrine();return;}
    MeshLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateUObject(this,&AChapelShrine::BindShrine));
}

void AChapelShrine::BindShrine()
{
    if(bBound)return;
    FRandomStream Random(int32(uint32(WorldSeed)^DungeonRunDomains::ShrineSelection));
    if(auto* Run=UDungeonRunSubsystem::Get(GetWorld()))
        bBound=Run->BindHillsShrine(this,WorldId,RandomShrine::Choose(Random));
    if(bBound)ArrangePresentation();
}

void AChapelShrine::ArrangePresentation()
{
    const UStaticMesh* Mesh=Statue->GetStaticMesh();
    if(!Mesh)return;
    auto* Stone=Cast<UStaticMesh>(PedestalPath.ResolveObject());
    if(!Stone){UE_LOG(LogTemp,Error,TEXT("HILLS_SHRINE rock pedestal unavailable"));return;}
    const FBox Bounds=Mesh->GetBoundingBox();
    const FVector Base(Bounds.GetCenter().X,Bounds.GetCenter().Y,Bounds.Min.Z);
    const FBox StoneBounds=Stone->GetBoundingBox();
    const double PedestalZ=-RootHeight-PedestalBedDepth-StoneBounds.Min.Z;
    const double SupportZ=PedestalZ+StoneBounds.Max.Z;
    Statue->SetRelativeScale3D(FVector(StatueScale));
    Statue->SetRelativeLocation(FVector(0,0,SupportZ-StatueSeatDepth)-Base*StatueScale);
    Statue->SetReceivesDecals(false);
    Statue->SetCanEverAffectNavigation(HasAuthority());
    const double Footprint=FVector2D(Bounds.GetExtent().X,Bounds.GetExtent().Y).Size()*StatueScale;
    const double Radius=FMath::Max(180.,(Footprint+25.)/.82);
    auto* Pedestal=FindObject<UStaticMeshComponent>(this,TEXT("RockPedestal"));
    if(!Pedestal)
    {
        Pedestal=NewObject<UStaticMeshComponent>(this,TEXT("RockPedestal"));
        Pedestal->SetupAttachment(Body);AddInstanceComponent(Pedestal);
    }
    Pedestal->SetMobility(EComponentMobility::Movable);
    Pedestal->SetStaticMesh(Stone);
    Pedestal->SetRelativeLocation(FVector(0,0,PedestalZ));
    Pedestal->SetRelativeScale3D(FVector(Radius/PedestalAuthoredRadius,Radius/PedestalAuthoredRadius,1.));
    Pedestal->SetReceivesDecals(false);
    Pedestal->SetCollisionProfileName(TEXT("BlockAll"));Pedestal->SetGenerateOverlapEvents(false);
    Pedestal->SetCanEverAffectNavigation(HasAuthority());
    if(!Pedestal->IsRegistered())Pedestal->RegisterComponent();
    RaidPedestal=Pedestal;
}

void AChapelShrine::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority())UNavigationSystemV1::UnregisterNavigationInvoker(*this);
    if(auto* Run=UDungeonRunSubsystem::Get(GetWorld()))Run->UnbindHillsShrine(this);
    if(MeshLoad){MeshLoad->CancelHandle();MeshLoad.Reset();}
    Super::EndPlay(Reason);
}
