#include "VillageHotOil.h"
#include "VillageDefenseCombat.h"
#include "VillageOilCarry.h"
#include "VillageOilMotion.h"
#include "VillageOilSurveySubsystem.h"
#include "TemperateHillsWorld.h"
#include "VillageSiegeUpgrades.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../Movement/HorseRiderComponent.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
double WorldClock(const UWorld* World)
{
    const auto* State=World->GetGameState();
    return State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();
}

bool Living(const APawn& Unit)
{
    if(Unit.IsA<AVillageDefenseSection>() || !Unit.CanBeDamaged())return false;
    if(const auto* Horse=Cast<AStableRidingHorse>(&Unit))return !Horse->IsRetreating();
    if(const auto* V=Unit.FindComponentByClass<UVillageArtisanVitalsComponent>())return !V->IsDowned();
    if(const auto* V=Unit.FindComponentByClass<UMonsterCombatComponent>())return !V->IsDead();
    if(const auto* V=Unit.FindComponentByClass<UFPSCombatHealthComponent>())return !V->IsDead();
    return false;
}
}
FSoftObjectPath VillageHotOil::Asset(const TCHAR* Name)
{
    return FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/%s.%s"),Name,Name));
}
UMaterialInterface* VillageHotOil::BodyMaterial()
{
    return LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilBody.M_OilBody"));
}

AVillageOilKettle::AVillageOilKettle()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.065f;
    Liquid=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BoilingSurface"));
    Liquid->SetupAttachment(Masonry);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Disc(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/SM_OilSurface"));
    Liquid->SetStaticMesh(Disc.Object);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> BodyOil(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilBody"));
    Liquid->SetMaterial(0,BodyOil.Object);
    Liquid->SetRelativeLocation(FVector(0,0,89));
    Liquid->SetRelativeScale3D(FVector(1.14,1.14,1));
    Liquid->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Liquid->SetCastShadow(false);
    Bubbles=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("RollingBubbles"));
    Bubbles->SetupAttachment(Masonry);
    Bubbles->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Bubbles->SetCanEverAffectNavigation(false);
    Bubbles->SetCastShadow(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> BubbleGold(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilBubble"));
    Bubbles->SetStaticMesh(Sphere.Object);Bubbles->SetMaterial(0,BubbleGold.Object);
    Vapour=CreateDefaultSubobject<UNiagaraComponent>(TEXT("OilFumes"));
    Vapour->SetupAttachment(Masonry);
    Vapour->SetRelativeLocation(FVector(0,0,93));
    Vapour->SetRelativeScale3D(FVector(.27));
    Vapour->SetAutoActivate(false);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> Smoke(TEXT("/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam"));
    Vapour->SetAsset(Smoke.Object);
    HearthGlow=CreateDefaultSubobject<UPointLightComponent>(TEXT("HearthGlow"));
    HearthGlow->SetupAttachment(Masonry);
    HearthGlow->SetRelativeLocation(FVector(0,0,56));
    HearthGlow->SetIntensityUnits(ELightUnits::Lumens);
    HearthGlow->SetIntensity(420.f);
    HearthGlow->SetLightColor(FLinearColor(1.f,.46f,.14f));
    HearthGlow->SetAttenuationRadius(280.f);
    HearthGlow->SetCastShadows(false);
    HearthGlow->SetVolumetricScatteringIntensity(0.15f);
    HearthGlow->bAffectTranslucentLighting=false;
    HearthGlow->SetMaxDrawDistance(2400.f);
    HearthGlow->SetMaxDistanceFadeRange(400.f);
}
void AVillageOilKettle::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer){SetActorTickEnabled(false);return;}
    BoilRandom.Initialize(GetTypeHash(GetActorLocation())^GetTypeHash(GetPlacedId()));
    SurfaceMID=Liquid->CreateDynamicMaterialInstance(0);
    Boil.SetNum(28);
    for(int32 I=0;I<Boil.Num();++I)Bubbles->AddInstance(FTransform(FQuat::Identity,FVector(0,0,83),FVector(.001)));
    Vapour->SetVariableFloat(TEXT("User.SteamCount"),2.f);
    Vapour->SetVariableVec3(TEXT("User.LocalUp"),FVector::UpVector);
    Vapour->SetVariableVec3(TEXT("User.Wind"),FVector(7,2,0));
    ApplyHealth();
}
void AVillageOilKettle::ApplyHealth()
{
    Super::ApplyHealth();
    const bool Active=GetHealth()>0.f && GetNetMode()!=NM_DedicatedServer;
    Liquid->SetVisibility(Active);Bubbles->SetVisibility(Active);
    if(HearthGlow)HearthGlow->SetVisibility(Active);
    if(IsActorBeginningPlay()||HasActorBegunPlay())
    {
        if(!Active)Vapour->DeactivateImmediate();
        SetActorTickEnabled(Active);
    }
}
void AVillageOilKettle::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!Masonry->WasRecentlyRendered(.5f) && !Liquid->WasRecentlyRendered(.5f))return;
    AdvanceBoil(GetWorld()->GetTimeSeconds());
}
void AVillageOilKettle::AdvanceBoil(double Now)
{
    Liquid->SetCustomPrimitiveDataFloat(0,float(Now));
    if(Now>=NextVent)
    {
        const double A=BoilRandom.FRandRange(0,UE_TWO_PI),R=49.*FMath::Sqrt(BoilRandom.FRand());
        VentXY=FVector2D(FMath::Cos(A),FMath::Sin(A))*R;
        NextVent=Now+BoilRandom.FRandRange(.45f,1.8f);
    }
    if(Now>=NextBubble)
    {
        int Count=BoilRandom.FRand()<.55f?BoilRandom.RandRange(2,5):1;
        for(auto& B:Boil)if(B.Born<0)
        {
            const double A=BoilRandom.FRandRange(0,UE_TWO_PI);
            const double R=BoilRandom.FRand()<.72f?BoilRandom.FRandRange(1,14):BoilRandom.FRandRange(15,44);
            B.XY=(VentXY+FVector2D(FMath::Cos(A),FMath::Sin(A))*R).GetClampedToMaxSize(51.);
            B.Life=BoilRandom.FRandRange(.27f,.76f);B.Radius=BoilRandom.FRandRange(1.0f,4.1f);
            B.Born=Now+BoilRandom.FRandRange(0,.13f);
            if(--Count==0)break;
        }
        NextBubble=Now+BoilRandom.FRandRange(.075f,.19f);
    }
    if(Now>=NextVapour)
    {
        Vapour->SetRelativeLocation(FVector(VentXY*.72,92.));Vapour->Activate(true);
        NextVapour=Now+BoilRandom.FRandRange(1.1f,2.2f);
    }
    static const FName Events[]={TEXT("Burst0"),TEXT("Burst1"),TEXT("Burst2"),TEXT("Burst3")};
    for(int I=0;I<Boil.Num();++I)
    {
        auto& B=Boil[I];if(B.Born<0 || Now<B.Born)continue;
        const double Age=(Now-B.Born)/B.Life;
        FVector Size(.001);double Z=84.;
        if(Age>=1.)
        {
            if(SurfaceMID && Age<1.6)SurfaceMID->SetVectorParameterValue(Events[BurstIndex++%4],
                FLinearColor(.5+B.XY.X/114.,.5+B.XY.Y/114.,Now,0));
            B.Born=-1.;
        }
        else
        {
            const double R=B.Radius*(.2+.8*FMath::SmoothStep(0.,.84,Age));
            Z=89.-R*(1.-.91*FMath::SmoothStep(0.,.86,Age));
            Size=FVector(.02*R,.02*R,.017*R*(1.-.85*FMath::SmoothStep(.86,1.,Age)));
        }
        Bubbles->UpdateInstanceTransform(I,FTransform(FQuat::Identity,FVector(B.XY,Z),Size),false,false,true);
    }
    Bubbles->MarkRenderStateDirty();
}

AVillageOilField::AVillageOilField()
{
    bReplicates=true;
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=.05f;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Impact")));
    Pool=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("OilOnFloor"));Pool->SetupAttachment(RootComponent);
    Pool->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    FireFront=CreateDefaultSubobject<UNiagaraComponent>(TEXT("TorchFireOnOil"));
    FireFront->SetupAttachment(RootComponent);
    FireFront->SetAutoActivate(false);
    FireFront->SetTranslucentSortPriority(1);
    FireFront->SetVisibleInRayTracing(false);
    Stream=CreateDefaultSubobject<USplineMeshComponent>(TEXT("OilRibbon"));Stream->SetupAttachment(RootComponent);
    for(UPrimitiveComponent* Part:{static_cast<UPrimitiveComponent*>(Pool),static_cast<UPrimitiveComponent*>(Stream),static_cast<UPrimitiveComponent*>(FireFront)})
    {
        Part->SetMobility(EComponentMobility::Movable);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);
        Part->SetCastShadow(false);Part->SetCanEverAffectNavigation(false);
    }
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Gold(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilFilm"));
    Pool->SetMaterial(0,Gold.Object);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Flow(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilStream"));
    Stream->SetStaticMesh(Cylinder.Object);Stream->SetMaterial(0,Flow.Object);
    Stream->SetForwardAxis(ESplineMeshAxis::Z,false);
    Splash=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("OilSplash"));
    Splash->SetupAttachment(RootComponent);Splash->SetMobility(EComponentMobility::Movable);
    Splash->SetCollisionEnabled(ECollisionEnabled::NoCollision);Splash->SetCastShadow(false);Splash->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> DropMesh(TEXT("/Engine/BasicShapes/Sphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> DropSkin(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/FlowR2/M_OilBubble"));
    Splash->SetStaticMesh(DropMesh.Object);Splash->SetMaterial(0,DropSkin.Object);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> Flames(TEXT("/Game/WorldGeneration/TemperateHills/HotOil/SeaOfFireV3/NS_OilSeaOfFire"));
    FireFront->SetAsset(Flames.Object);
    FireLight=CreateDefaultSubobject<UPointLightComponent>(TEXT("FireGlow"));
    FireLight->SetupAttachment(RootComponent);
    FireLight->SetRelativeLocation(FVector(0,0,48));
    FireLight->SetIntensityUnits(ELightUnits::Lumens);
    FireLight->SetIntensity(0.f);
    FireLight->SetLightColor(FLinearColor(1.f,.44f,.12f));
    FireLight->SetAttenuationRadius(520.f);
    FireLight->SetCastShadows(false);
    FireLight->bAffectTranslucentLighting=false;
    FireLight->SetVisibility(false);
    FireAudio=CreateDefaultSubobject<UAudioComponent>(TEXT("FireLoopAudio"));
    FireAudio->SetupAttachment(RootComponent);
    FireAudio->bAutoActivate=false;
    FireAudio->bAllowSpatialization=true;
}
void AVillageOilField::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(AVillageOilField,PourFrom,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageOilField,Started,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageOilField,FlowSeed,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageOilField,UpgradeRanks,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageOilField,bDirectSplash,COND_InitialOnly);
    DOREPLIFETIME_CONDITION(AVillageOilField,bIgnoreFriendlies,COND_InitialOnly);
    DOREPLIFETIME(AVillageOilField,SurfacePacket);
}
float AVillageOilField::FieldDamage() const
{
    return float(VillageSiegeUpgrades::Installed(UpgradeRanks,VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilDamage));
}
float AVillageOilField::FieldRadius() const
{
    return float(VillageSiegeUpgrades::Installed(UpgradeRanks,VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilRadius));
}
float AVillageOilField::FieldLife() const
{
    return float(VillageSiegeUpgrades::Installed(UpgradeRanks,VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilDuration));
}
int32 AVillageOilField::FieldBurnStacks() const
{
    return FMath::RoundToInt(VillageSiegeUpgrades::Installed(UpgradeRanks,VillageSiegeUpgrades::HotOil,VillageSiegeUpgrades::OilBurnStacks));
}
void AVillageOilField::BeginPlay()
{
    Super::BeginPlay();
    if(HasAuthority())
    {
        PourFrom=Lip;Started=WorldClock(GetWorld());FlowSeed=FMath::RandHelper(65536);
        if(bDirectSplash && InitialUpgradeRanks!=0)UpgradeRanks=InitialUpgradeRanks;
        else
        {
            bool bFoundVillage=false;
            for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){UpgradeRanks=It->GetSiegeRanks();bFoundVillage=true;break;}
            if(!bFoundVillage)UpgradeRanks=InitialUpgradeRanks;
        }
        if(const APawn* Inst=GetInstigator();Inst && Inst->IsPlayerControlled())
            if(const auto* Profile=ColdSteelAuthority::ForPawn(Inst))BurnMagicAttack=Profile->Derived(TEXT("matk"));
    }
    Spread.Seed=FlowSeed/1773.f;
    Spread.Radius=FieldRadius();
    DropSeconds=bDirectSplash?0.02:FMath::Clamp(.105+FMath::Sqrt(FMath::Max(0.,double(PourFrom.Z)-GetActorLocation().Z))*.009,.13,.42);
    if(HasAuthority())SetLifeSpan(FieldLife()+DropSeconds+.85);
    const FVector2D Delta2D(GetActorLocation()-FVector(PourFrom));
    Spread.Incoming=Delta2D.IsNearlyZero()?FVector2D(1.,0.):Delta2D.GetSafeNormal();
    if(HasAuthority())
    {
        if(auto* Scheduler=GetWorld()->GetSubsystem<UVillageOilSurveySubsystem>())Scheduler->Add(this);
    }
    else if(!SurfacePacket.Bytes.IsEmpty())OnRep_Surface();
    if(GetNetMode()!=NM_DedicatedServer)
    {
        FRandomStream R(GetTypeHash(FVector(PourFrom)-GetActorLocation()));
        const FVector Into=(GetActorLocation()-FVector(PourFrom)).GetSafeNormal2D(UE_SMALL_NUMBER,FVector::ForwardVector);
        for(int I=0;I<16;++I)
        {
            const FVector Dir=Into.RotateAngleAxis(R.FRandRange(-145.f,145.f),FVector::UpVector);
            SplashVelocity.Add(Dir*R.FRandRange(55.f,170.f)+FVector(0,0,R.FRandRange(52.f,136.f)));
            Splash->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.001)));
        }
        Splash->SetVisibility(false);
        Pool->SetCustomPrimitiveDataFloat(0,float(WorldClock(GetWorld())-Started-DropSeconds));
        Pool->SetCustomPrimitiveDataFloat(1,FieldLife());
        if(FireLight)FireLight->SetAttenuationRadius(FieldRadius()+40.f);
        if(bDirectSplash)
        {
            Stream->SetVisibility(false);
            SetActorTickInterval(.05f);
        }
        else
        {
            const FVector Start=FVector(PourFrom)-GetActorLocation();
            const FVector Forward=(-Start).GetSafeNormal2D();
            Stream->SetStartAndEnd(Start,Forward*Start.Size2D()*.9,FVector::ZeroVector,FVector(0,0,-FMath::Max(80.,Start.Z)),false);
            Stream->SetStartScale(FVector2D(.060,.035),false);Stream->SetEndScale(FVector2D(.115,.055),true);
            if(const APawn* Source=GetInstigator())
                if(auto* Hands=Source->FindComponentByClass<UVillageOilCarry>())AddTickPrerequisiteComponent(Hands);
            SetActorTickInterval(0.f);
            UpdateStream(WorldClock(GetWorld())-Started);
        }
    }
}
int32 AVillageOilField::SurveyStep(int32 Allowance)
{
    const double Now=WorldClock(GetWorld());
    const float Age=float(Now-Started-DropSeconds);
    if(Age>=FieldLife())return 0;
    if(Now>=NextSupportCheck)
    {
        NextSupportCheck=Now+.15;
        if(Spread.RemoveLostSupports(Age))
        {
            // Any uncommitted links were sampled against the previous geometry.
            SurveyWork.Reset();bSurfaceDirty=true;
        }
    }
    const int Want=FMath::Clamp(3+FMath::FloorToInt(FMath::Max(0.f,Age)*14.f),3,Spread.MaxExtent());
    if(Spread.Built>=Want)return 0;
    if(!SurveyWork)SurveyWork=MakeUnique<FVillageOilSpread>(Spread);
    int Remaining=Allowance;
    if(SurveyWork->AdvanceSurvey(*this,Age,Remaining))
    {
        SurveyWork->RemoveLostSupports(Age);
        Spread=MoveTemp(*SurveyWork);SurveyWork.Reset();
        bSurfaceDirty=true;
    }
    return Allowance-Remaining;
}

void AVillageOilField::PublishSurface()
{
    bSurfaceDirty=false;
    if(GetNetMode()!=NM_Standalone)
    {
        Spread.PackSurface(SurfacePacket.Bytes);
        ++SurfacePacket.Serial;
        ForceNetUpdate();
    }
    if(GetNetMode()!=NM_DedicatedServer)PresentSurface();
}

void AVillageOilField::OnRep_Surface()
{
    if(!HasActorBegunPlay() && !IsActorBeginningPlay())return;
    FVillageOilSpread Received;
    if(!Received.UnpackSurface(SurfacePacket.Bytes))return;
    Spread=MoveTemp(Received);
    PresentSurface();
}

void AVillageOilField::PresentSurface()
{
    if(DisplayedSupportRevision!=Spread.SupportRevision)
    {
        // Retire particles that were born on a platform before it disappeared.
        FireFront->DeactivateImmediate();
        DisplayedSupportRevision=Spread.SupportRevision;
        NextFireUpdate=0.f;
    }
    Spread.WriteMesh(*Pool);
    FireSurveyExtent=INDEX_NONE;
}

void AVillageOilField::Pulse(double Now)
{
    if(!Spread.WetBounds.IsValid){NextContact.Reset();return;}
    const FBox ContactBox(Spread.WetBounds.Min-FVector(24.,24.,24.),Spread.WetBounds.Max+FVector(24.,24.,32.));
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits,GetActorLocation()+ContactBox.GetCenter(),FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(ContactBox.GetExtent()));
    TSet<TWeakObjectPtr<APawn>> Present;
    bool bHit=false,bKilled=false;
    const double ElapsedWet=Now-Started-DropSeconds;
    const float Life=FieldLife();
    const float Damage=FieldDamage();
    const int32 BurnStacks=FieldBurnStacks();
    const FVector LocalOrigin=GetActorLocation();
    AActor* OwnerActor=GetOwner()?GetOwner():static_cast<AActor*>(this);
    const auto IsHostileOilTarget=[OwnerActor](const APawn* Unit) -> bool
    {
        if(!Unit || Unit->IsPlayerControlled() || Unit->IsA<AFPSGAMECharacter>() || Unit->IsA<AStableRidingHorse>() || Unit->IsA<AVillageDefenseSection>())
            return false;
        if(Unit->FindComponentByClass<UVillageArtisanVitalsComponent>())return false;
        if(Unit->ActorHasTag(TEXT("NPC")) || Unit->ActorHasTag(TEXT("Friendly")) || Unit->ActorHasTag(TEXT("Companion"))
            || Unit->ActorHasTag(TEXT("Player")) || Unit->ActorHasTag(TEXT("Wildlife")) || Unit->ActorHasTag(TEXT("WildlifeSpawned")))
            return false;
        return UFPSMeleeLightningComponent::IsEnemy(const_cast<APawn*>(Unit),OwnerActor);
    };
    for(const FOverlapResult& Hit:Hits)
    {
        APawn* Unit=Cast<APawn>(Hit.GetActor());
        if(!Unit || Present.Contains(Unit) || !Living(*Unit))continue;
        if(bIgnoreFriendlies && !IsHostileOilTarget(Unit))continue;
        if(const auto* Rider=Unit->FindComponentByClass<UHorseRiderComponent>();Rider && Rider->Active())continue;
        const auto* Capsule=Unit->FindComponentByClass<UCapsuleComponent>();
        const FVector Feet=Capsule?Capsule->GetComponentLocation()-FVector(0,0,Capsule->GetScaledCapsuleHalfHeight()):Unit->GetNavAgentLocation();
        // Floors and platforms can disappear during the oil field duration. Trace first so slopes and large feet match surface contact.
        FCollisionQueryParams Q(SCENE_QUERY_STAT(OilFootContact),false,Unit);
        FCollisionObjectQueryParams Terrain(ECC_WorldStatic);Terrain.AddObjectTypesToQuery(ECC_WorldDynamic);
        FHitResult Footing;
        if(!GetWorld()->LineTraceSingleByObjectType(Footing,Feet+FVector(0,0,24),Feet-FVector(0,0,42),Terrain,Q) ||
            !Footing.IsValidBlockingHit() || Footing.ImpactNormal.Z<.55)continue;
        if(!Spread.WetAt(Footing.ImpactPoint-LocalOrigin,ElapsedWet) && !Spread.WetAt(Feet-LocalOrigin,ElapsedWet))continue;
        Present.Add(Unit);
        double& Next=NextContact.FindOrAdd(Unit,Now+VillageHotOil::Exposure);
        while(Now+1.e-5>=Next && Next<=Started+DropSeconds+Life+1.e-5 && Living(*Unit))
        {
            Next+=VillageHotOil::Exposure;
            const float Applied=UGameplayStatics::ApplyDamage(Unit,Damage,GetInstigatorController(),this,UVillageOilDamage::StaticClass());
            if(Applied<=0.f)continue;
            bHit=true;
            const bool bUnitKilled=!Living(*Unit);
            if(IsHostileOilTarget(Unit))
                VillageDefenseCombat::BroadcastDamageNumber(GetWorld(),Unit,Unit->GetActorLocation(),Applied,Applied,false,bUnitKilled);
            if(!bUnitKilled)UCombatStatusFormula::GetOrAdd(Unit)->AddOilBurn(GetInstigator(),BurnMagicAttack,BurnStacks);
            else bKilled=true;
        }
    }
    for(auto It=NextContact.CreateIterator();It;++It)if(!Present.Contains(It.Key()))It.RemoveCurrent();
    if(bHit)if(auto* Shooter=Cast<AFPSGAMECharacter>(GetInstigator()))Shooter->ClientBallistaHit(bKilled);
}
void AVillageOilField::UpdateStream(double Age)
{
    if(bDirectSplash){Stream->SetVisibility(false);return;}
    constexpr double Duration=VillageOilMotion::Empty-VillageOilMotion::Release;
    FVector SourceLip=FVector::ZeroVector;
    const auto* Source=GetInstigator();
    const auto* Hands=Source?Source->FindComponentByClass<UVillageOilCarry>():nullptr;
    const bool Following=Hands && Hands->PourLip(SourceLip);
    if(Age>=Duration || (bFollowedHands && !Following))
    {
        Stream->SetVisibility(false);
        SetActorTickInterval(.05f);
        return;
    }
    if(Following)bFollowedHands=true;
    const FVector From=GetActorTransform().InverseTransformPosition(Following?SourceLip:FVector(PourFrom));
    const FVector Launch=(-From).GetSafeNormal2D()*From.Size2D()*.96;
    const FVector Fall=FVector(0,0,-FMath::Max(80.,From.Z)*1.5);
    const double Head=FMath::Clamp(Age/DropSeconds,.01,1.);
    const FVector End=FMath::CubicInterp(From,Launch,FVector::ZeroVector,Fall,Head);
    const FVector Tangent=FMath::CubicInterpDerivative(From,Launch,FVector::ZeroVector,Fall,Head);
    Stream->SetStartAndEnd(From,Head*Launch,End,Head*Tangent,false);
    const float Width=FMath::Sqrt(float(FMath::SmoothStep(-.018,.08,Age)*(1.-FMath::SmoothStep(Duration-.14,Duration,Age))));
    Stream->SetStartScale(FVector2D(.057,.032)*Width,false);
    Stream->SetEndScale(FVector2D(.077,.027)*Width,true);
}
void AVillageOilField::UpdateSplash(float WetAge)
{
    if(WetAge<0 || WetAge>.62f){if(Splash->IsVisible())Splash->SetVisibility(false);return;}
    Splash->SetVisibility(true);
    for(int I=0;I<SplashVelocity.Num();++I)
    {
        const double T=WetAge-(I%4)*.045;
        const FVector V=SplashVelocity[I];
        FVector P=V*T-FVector(0,0,340.*T*T);
        const double R=T>0 && P.Z>0?(.85+I%3*.42):.005;
        const FVector Axis=(V-FVector(0,0,680.*T)).GetSafeNormal();
        Splash->UpdateInstanceTransform(I,FTransform(FRotationMatrix::MakeFromZ(Axis).ToQuat(),P,
            FVector(R*.016,R*.016,R*.032)),false,I+1==SplashVelocity.Num(),true);
    }
}

void AVillageOilField::Tick(float Delta)
{
    Super::Tick(Delta);
    const double Now=WorldClock(GetWorld()),Age=Now-Started;
    const double WetAge=Age-DropSeconds;
    if(bSurfaceDirty)PublishSurface();
    const float Life=FieldLife();
    if(HasAuthority() && WetAge>=0.)
    {
        if(WetAge>=Life+.65){Destroy();return;}
        if(!bFinalPulseDone && (Now>=NextSample || WetAge>=Life))
        {
            NextSample=Now+.05;
            Pulse(FMath::Min(Now,Started+DropSeconds+Life));
            if(WetAge>=Life){bFinalPulseDone=true;NextContact.Reset();}
        }
    }
    if(GetNetMode()==NM_DedicatedServer)return;
    if(Stream->IsVisible())UpdateStream(Age);
    UpdateSplash(WetAge);
    UpdateFireFront(float(WetAge));
    Pool->SetCustomPrimitiveDataFloat(0,float(WetAge));
}
