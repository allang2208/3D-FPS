#include "HillsNightPortal.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "NavigationSystem.h"
#include "Net/UnrealNetwork.h"

namespace
{
const TCHAR* FramePath=TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Frame.SM_GamedevPortal_Frame");
const TCHAR* CurtainPath=TEXT("/Game/Props/GamedevPortal20260922/SM_GamedevPortal_Energy.SM_GamedevPortal_Energy");
const TCHAR* MaterialPath=TEXT("/Game/WorldGeneration/HillsNightRaid/M_NightPortalVeil.M_NightPortalVeil");
const TCHAR* BeamMeshPath=TEXT("/Game/WorldGeneration/HillsNightRaid/SM_NightPortalSkyBeam.SM_NightPortalSkyBeam");
const TCHAR* BeamMaterialPath=TEXT("/Game/WorldGeneration/HillsNightRaid/M_NightPortalSkyBeam.M_NightPortalSkyBeam");
}
AHillsNightPortal::AHillsNightPortal()
{
    bReplicates=true;bAlwaysRelevant=true;SetReplicateMovement(true);
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.1f;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    Frame=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Arch"));Frame->SetupAttachment(RootComponent);
    Frame->SetCollisionProfileName(TEXT("BlockAll"));Frame->SetGenerateOverlapEvents(false);
    Curtain=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FlowingVeil"));Curtain->SetupAttachment(RootComponent);
    Curtain->SetCollisionEnabled(ECollisionEnabled::NoCollision);Curtain->SetCastShadow(false);
    Curtain->SetCanEverAffectNavigation(false);
    SkyBeam=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PurpleSkyBeam"));SkyBeam->SetupAttachment(RootComponent);
    SkyBeam->SetRelativeLocation(FVector(0,0,180));
    SkyBeam->SetCollisionEnabled(ECollisionEnabled::NoCollision);SkyBeam->SetGenerateOverlapEvents(false);
    SkyBeam->SetCastShadow(false);SkyBeam->SetCanEverAffectNavigation(false);
    SkyBeam->bAffectDistanceFieldLighting=false;SkyBeam->bVisibleInRayTracing=false;
    SkyBeam->SetReceivesDecals(false);SkyBeam->SetVisibility(false);
    // Map-wide beacon; its authored bounds cover the per-view cylindrical billboard.
    SkyBeam->bAllowCullDistanceVolume=false;SkyBeam->SetCullDistance(0);
    Glow=CreateDefaultSubobject<UPointLightComponent>(TEXT("PurpleSpill"));Glow->SetupAttachment(RootComponent);
    Glow->SetRelativeLocation(FVector(70,0,180));Glow->SetLightColor(FLinearColor(.34f,.035f,1.f));
    Glow->SetIntensity(0);Glow->SetAttenuationRadius(650);Glow->SetCastShadows(false);
    Glow->MaxDrawDistance=4500;Glow->MaxDistanceFadeRange=1000;
}
void AHillsNightPortal::AddAssetPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const auto* Path:{FramePath,CurtainPath,MaterialPath,BeamMeshPath,BeamMaterialPath})Paths.AddUnique(FSoftObjectPath(Path));
}
double AHillsNightPortal::ServerTime() const
{
    const auto* GS=GetWorld()->GetGameState();return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
void AHillsNightPortal::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHillsNightPortal,OpenedAt);DOREPLIFETIME(AHillsNightPortal,ClosedAt);
}
void AHillsNightPortal::BeginPlay()
{
    Super::BeginPlay();
    if(HasAuthority())UNavigationSystemV1::RegisterNavigationInvoker(*this,15000,17000);
    TArray<FSoftObjectPath> Paths;AddAssetPaths(Paths);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateUObject(this,&AHillsNightPortal::AssetsReady));
}
void AHillsNightPortal::AssetsReady()
{
    Frame->SetStaticMesh(Cast<UStaticMesh>(FSoftObjectPath(FramePath).ResolveObject()));
    Curtain->SetStaticMesh(Cast<UStaticMesh>(FSoftObjectPath(CurtainPath).ResolveObject()));
    if(const UStaticMesh* Mesh=Frame->GetStaticMesh())
    {
        const FVector FloorOffset(0,0,-Mesh->GetBoundingBox().Min.Z);
        Frame->SetRelativeLocation(FloorOffset);Curtain->SetRelativeLocation(FloorOffset);
    }
    if(auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(MaterialPath).ResolveObject()))
    {
        Energy=UMaterialInstanceDynamic::Create(Material,this);Curtain->SetMaterial(0,Energy);
        Energy->SetScalarParameterValue(TEXT("FlowTimeOffset"),ServerTime()-GetWorld()->GetTimeSeconds());
    }
    SkyBeam->SetStaticMesh(Cast<UStaticMesh>(FSoftObjectPath(BeamMeshPath).ResolveObject()));
    if(auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(BeamMaterialPath).ResolveObject()))
    {
        BeamEnergy=UMaterialInstanceDynamic::Create(Material,this);SkyBeam->SetMaterial(0,BeamEnergy);
        BeamEnergy->SetScalarParameterValue(TEXT("FlowTimeOffset"),ServerTime()-GetWorld()->GetTimeSeconds());
    }
    OnRep_Presentation();
}
void AHillsNightPortal::OnRep_Presentation(){if(HasActorBegunPlay())Tick(0.f);}
void AHillsNightPortal::Tick(float Delta)
{
    Super::Tick(Delta);
    const double Now=ServerTime();
    const float Amount=ClosedAt>=0.?float(1.-FMath::Clamp((Now-ClosedAt)/4.,0.,1.)):float(FMath::Clamp((Now-OpenedAt)/8.,0.,1.));
    if(Energy)Energy->SetScalarParameterValue(TEXT("OpenAmount"),Amount);
    if(BeamEnergy)BeamEnergy->SetScalarParameterValue(TEXT("OpenAmount"),Amount);
    SkyBeam->SetVisibility(BeamEnergy!=nullptr&&Amount>.001f);
    Glow->SetIntensity(75.f*Amount);
}
void AHillsNightPortal::ClosePortal()
{
    if(!HasAuthority()||ClosedAt>=0.)return;
    ClosedAt=ServerTime();ForceNetUpdate();SetLifeSpan(4.2f);
}
void AHillsNightPortal::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority())UNavigationSystemV1::UnregisterNavigationInvoker(*this);
    if(AssetLoad){AssetLoad->CancelHandle();AssetLoad.Reset();}
    Super::EndPlay(Reason);
}
