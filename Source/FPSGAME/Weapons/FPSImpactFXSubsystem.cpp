#include "FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstance.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "HAL/IConsoleManager.h"
#include "UObject/ConstructorHelpers.h"
#include "../Building/VoxelBuildWorld.h"

namespace FPSImpact
{
    static TAutoConsoleVariable<float> MaxDistance(TEXT("fps.Impact.MaxDistance"), 12000.f, TEXT("Impact FX cull distance in cm, adjusted for optics."));
    static TAutoConsoleVariable<float> DetailDistance(TEXT("fps.Impact.DetailDistance"), 2500.f, TEXT("Full impact detail distance in cm."));
    static TAutoConsoleVariable<float> BurstsPerSecond(TEXT("fps.Impact.BurstsPerSecond"), 40.f, TEXT("World-wide cosmetic impact rate; no effect on damage."));
    constexpr int32 Starts[] = {0,48,72,104,128};
    constexpr int32 Counts[] = {48,24,32,24,96};
    constexpr const TCHAR* Names[] = {TEXT("Metal"),TEXT("Wood"),TEXT("Stone"),TEXT("Dirt"),TEXT("Glass"),TEXT("Flesh")};
    EFPSImpactSurface FromName(const FString& Name)
    {
        const FString S = Name.ToLower();
        if (S.Contains(TEXT("metal")) || S.Contains(TEXT("steel")) || S.Contains(TEXT("iron"))) return EFPSImpactSurface::Metal;
        if (S.Contains(TEXT("wood")) || S.Contains(TEXT("timber")) || S.Contains(TEXT("plank")) || S.Contains(TEXT("bark"))) return EFPSImpactSurface::Wood;
        if (S.Contains(TEXT("glass"))) return EFPSImpactSurface::Glass;
        if (S.Contains(TEXT("flesh")) || S.Contains(TEXT("skin"))) return EFPSImpactSurface::Flesh;
        if (S.Contains(TEXT("dirt")) || S.Contains(TEXT("soil")) || S.Contains(TEXT("mud")) || S.Contains(TEXT("grass")) || S.Contains(TEXT("sand"))) return EFPSImpactSurface::Dirt;
        if (S.Contains(TEXT("stone")) || S.Contains(TEXT("concrete")) || S.Contains(TEXT("rock")) || S.Contains(TEXT("brick")) || S.Contains(TEXT("gravel")) || S.Contains(TEXT("marble"))) return EFPSImpactSurface::Stone;
        return EFPSImpactSurface::Unknown;
    }
    const FLinearColor DustColors[] = {
        {.29f,.28f,.26f,1.f}, {.34f,.22f,.105f,1.f}, {.54f,.51f,.45f,1.f},
        {.25f,.17f,.085f,1.f}, {.58f,.69f,.72f,1.f}, {.12f,.016f,.012f,1.f}};
}

UFPSImpactFXSubsystem::UFPSImpactFXSubsystem()
{
    ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    PlaneMesh = Plane.Object; ChipMesh = Cube.Object;
    for (const TCHAR* Name : {TEXT("M_ImpactSparkV1"), TEXT("M_ImpactDustV1"), TEXT("M_ImpactChipV1")})
    {
        const FString Path = FString::Printf(TEXT("/Game/Weapons/GunplayFX/Impacts/%s.%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UMaterialInterface> Asset(*Path);
        ParticleMaterials.Add(Asset.Object);
    }
    for (const TCHAR* Name : {TEXT("M_FleshMistV1"), TEXT("M_FleshDropletV1")})
    {
        const FString Path = FString::Printf(TEXT("/Game/Weapons/GunplayFX/Impacts/Blood/%s.%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UMaterialInterface> Asset(*Path);
        ParticleMaterials.Add(Asset.Object);
    }
    ConstructorHelpers::FObjectFinder<UMaterialInterface> BloodMark(TEXT("/Game/Weapons/GunplayFX/Impacts/Blood/M_FleshStainV2.M_FleshStainV2"));
    BloodStainMaterial = BloodMark.Object;
    for (const TCHAR* Name : FPSImpact::Names)
    {
        const FString DecalPath = FString::Printf(TEXT("/Game/Weapons/GunplayFX/Impacts/MI_ImpactMark_%s.MI_ImpactMark_%s"), Name, Name);
        ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(*DecalPath);
        DecalMaterials.Add(Material.Object);
        for (int32 I=0; I<3; ++I)
        {
            const FString Path = FString::Printf(TEXT("/Game/Weapons/GunplayFX/Impacts/S_Impact_%s_%d.S_Impact_%s_%d"), Name,I,Name,I);
            ConstructorHelpers::FObjectFinder<USoundBase> Sound(*Path);
            Sounds.Add(Sound.Object);
        }
    }
}

bool UFPSImpactFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type == EWorldType::Game || Type == EWorldType::PIE; }

void UFPSImpactFXSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if (InWorld.GetNetMode() == NM_DedicatedServer || !PlaneMesh || !ChipMesh) return;
    for (const auto& Material : ParticleMaterials)
        if (!Material) return;
    for (auto& Surface : SurfaceTypes) Surface = EFPSImpactSurface::Unknown;
    for (const FPhysicalSurfaceName& Surface : UPhysicsSettings::Get()->PhysicalSurfaces)
        if (Surface.Type > SurfaceType_Default && Surface.Type < SurfaceType_Max)
            SurfaceTypes[Surface.Type] = FPSImpact::FromName(Surface.Name.ToString());
    SurfaceCache.Reserve(256);
    // Allocate at world start, never on the shot path. Five shared materials,
    // no per-particle components, MIDs, physics bodies, lights or shadow passes.
    for (int32 Group=0; Group<ParticleGroups; ++Group)
    {
        auto* Renderer = NewObject<UInstancedStaticMeshComponent>(this);
        Renderer->SetMobility(EComponentMobility::Movable);
        Renderer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Renderer->SetGenerateOverlapEvents(false);
        Renderer->SetCanEverAffectNavigation(false);
        Renderer->SetCastShadow(false);
        Renderer->bReceivesDecals = false;
        Renderer->bAffectDistanceFieldLighting = false;
        Renderer->SetStaticMesh(Group == 2 ? ChipMesh : PlaneMesh);
        Renderer->SetMaterial(0, ParticleMaterials[Group]);
        Renderer->SetNumCustomDataFloats(Group>=3 ? 6 : 4);
        Renderer->PreAllocateInstancesMemory(FPSImpact::Counts[Group]);
        Transforms[Group].Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),FPSImpact::Counts[Group]);
        Renderer->AddInstances(Transforms[Group],false,false,false);
        Renderer->RegisterComponentWithWorld(&InWorld);
        Renderers.Add(Renderer);
    }
    for (int32 I=0; I<DecalSlots; ++I)
    {
        auto* Decal = NewObject<UDecalComponent>(this);
        Decal->SetMobility(EComponentMobility::Movable);
        Decal->SetVisibility(false);
        Decal->SetFadeScreenSize(.002f);
        Decal->RegisterComponentWithWorld(&InWorld);
        Decals.Add(Decal);
    }
    // Blood has a small independent pool so wall hits cannot overwrite it.
    for (int32 I=0; I<BloodDecalSlots; ++I)
    {
        auto* Decal = NewObject<UDecalComponent>(this);
        Decal->SetMobility(EComponentMobility::Movable);
        Decal->SetVisibility(false);
        Decal->SetFadeScreenSize(.00025f);
        Decal->SetDecalMaterial(BloodStainMaterial);
        Decal->RegisterComponentWithWorld(&InWorld);
        BloodDecals.Add(Decal);
    }
    FSoundAttenuationSettings Attenuation;
    Attenuation.bAttenuate = true; Attenuation.bSpatialize = true;
    Attenuation.AttenuationShapeExtents = FVector(120.f);
    Attenuation.FalloffDistance = 5800.f;
    Attenuation.bEnableOcclusion = false; // No secondary visibility traces for tiny transients.
    for (int32 I=0; I<VoiceSlots; ++I)
    {
        auto* Voice = NewObject<UAudioComponent>(this);
        Voice->bAutoDestroy = false; Voice->SetAutoActivate(false);
        Voice->bOverrideAttenuation = true;
        Voice->SetAttenuationOverrides(Attenuation);
        Voice->RegisterComponentWithWorld(&InWorld);
        Voices.Add(Voice);
    }
    LastBudgetTime = InWorld.GetTimeSeconds();
    bReady = true;
}

EFPSImpactSurface UFPSImpactFXSubsystem::SurfaceForObject(const UObject* Object)
{
    if (!Object) return EFPSImpactSurface::Unknown;
    if (const auto* Physical=Cast<UPhysicalMaterial>(Object))
    {
        const auto Type=Physical->SurfaceType.GetValue();
        if(Type>SurfaceType_Default && Type<SurfaceType_Max && SurfaceTypes[Type]!=EFPSImpactSurface::Unknown)
            return SurfaceTypes[Type];
    }
    const TWeakObjectPtr<const UObject> Key(Object);
    if (const auto* Found = SurfaceCache.Find(Key)) return *Found;
    EFPSImpactSurface Result = FPSImpact::FromName(Object->GetName());
    // Material instance names can be opaque; walk only their material ancestry,
    // not texture dependencies or every mesh material slot.
    const UMaterialInstance* Instance = Cast<UMaterialInstance>(Object);
    for (int32 Depth=0; Result==EFPSImpactSurface::Unknown && Instance && Instance->Parent && Depth<8; ++Depth)
    {
        Result = FPSImpact::FromName(Instance->Parent->GetName());
        Instance = Cast<UMaterialInstance>(Instance->Parent);
    }
    if (SurfaceCache.Num() >= 256) SurfaceCache.Reset();
    SurfaceCache.Add(Key,Result);
    return Result;
}

EFPSImpactSurface UFPSImpactFXSubsystem::ResolveSurface(const FHitResult& Hit)
{
    const UPrimitiveComponent* Component = Hit.GetComponent();
    const AActor* Actor = Hit.GetActor();
    // Explicit tags allow armor/props to override a pawn or a generic physmat.
    static const FName Tags[] = {TEXT("Impact.Metal"),TEXT("Impact.Wood"),TEXT("Impact.Stone"),TEXT("Impact.Dirt"),TEXT("Impact.Glass"),TEXT("Impact.Flesh")};
    for (int32 I=0; I<6; ++I)
        if ((Component && (Component->ComponentHasTag(Tags[I]) || Component->ComponentHasTag(FName(FPSImpact::Names[I]))))
            || (Actor && Actor->ActorHasTag(Tags[I]))) return static_cast<EFPSImpactSurface>(I);
    if (Hit.PhysMaterial.IsValid())
    {
        const auto Type = Hit.PhysMaterial->SurfaceType.GetValue();
        if (Type > SurfaceType_Default && Type < SurfaceType_Max && SurfaceTypes[Type] != EFPSImpactSurface::Unknown)
            return SurfaceTypes[Type];
        const auto Surface = SurfaceForObject(Hit.PhysMaterial.Get());
        if (Surface != EFPSImpactSurface::Unknown) return Surface;
    }
    if (Cast<APawn>(Actor)) return EFPSImpactSurface::Flesh;
    // A merged building mesh has many materials and a shared physics material.
    // Resolve the struck cell instead of treating slot zero as the whole wall.
    if (const auto* Building = Cast<AVoxelBuildWorld>(Actor))
    {
        FVoxelBuildKey Key;
        if (Building->ResolveHit(Hit,Key))
        {
            const auto Surface = FPSImpact::FromName(Building->VolumeMaterialAt(Key.Volume,Key.Cell).ToString());
            if (Surface != EFPSImpactSurface::Unknown) return Surface;
        }
    }
    if (Component)
    {
        int32 Section = INDEX_NONE;
        UMaterialInterface* Material = Hit.FaceIndex != INDEX_NONE ? Component->GetMaterialFromCollisionFaceIndex(Hit.FaceIndex,Section) : nullptr;
        if (!Material && Component->GetNumMaterials()==1) Material=Component->GetMaterial(0);
        if (Material)
        {
            const auto Physical = SurfaceForObject(Material->GetPhysicalMaterial());
            if (Physical != EFPSImpactSurface::Unknown) return Physical;
            const auto Surface = SurfaceForObject(Material);
            if (Surface != EFPSImpactSurface::Unknown) return Surface;
        }
        const auto Surface = SurfaceForObject(Component);
        if (Surface != EFPSImpactSurface::Unknown) return Surface;
        // Landscape / authored procedural ground remain dirt without a tagged layer.
        const FString ClassName=Component->GetClass()->GetName();
        if (ClassName.Contains(TEXT("Landscape")) || (Actor && Actor->GetClass()->GetFName()==TEXT("TemperateHillsWorld"))) return EFPSImpactSurface::Dirt;
    }
    return EFPSImpactSurface::Stone;
}

void UFPSImpactFXSubsystem::SpawnImpact(const FHitResult& Hit, UCameraComponent* ViewCamera)
{
    if (!bReady || !Hit.bBlockingHit || !IsValid(ViewCamera)) return;
    const FVector ToHit=Hit.ImpactPoint-ViewCamera->GetComponentLocation();
    const float Distance=ToHit.Size();
    const double Now=GetWorld()->GetTimeSeconds();
    // Reject before surface lookup or any renderer update. ADS retains distant
    // readable hits without making their physical particle sizes enormous.
    const float LensScale=FMath::Clamp(FMath::Tan(FMath::DegreesToRadians(ViewCamera->FieldOfView*.5f)),.28f,1.f);
    const float ApparentDistance=Distance*LensScale;
    if (ApparentDistance>FMath::Max(0.f,FPSImpact::MaxDistance.GetValueOnGameThread())
        || FVector::DotProduct(ToHit,ViewCamera->GetForwardVector()) < -Distance*.1f) return;
    if (BudgetFrame!=GFrameCounter) {BudgetFrame=GFrameCounter;FrameBursts=0;}
    BurstTokens=FMath::Min(8.f,BurstTokens+static_cast<float>(FMath::Max(0.,Now-LastBudgetTime))*FMath::Max(0.f,FPSImpact::BurstsPerSecond.GetValueOnGameThread()));
    LastBudgetTime=Now;
    if (FrameBursts>=8 || BurstTokens<1.f) return;
    // Coalesce overlapping cosmetic hits on the same surface, including catch-up
    // volleys. Never feed this decision back into projectile/damage processing.
    for (const auto& Recent:RecentHits)
        if (Recent.Component==Hit.Component && Now-Recent.Time<.025 && FVector::DistSquared(Recent.Position,Hit.ImpactPoint)<36.f) return;
    RecentHits[RecentCursor]={Hit.Component,Hit.ImpactPoint,Now};
    RecentCursor=(RecentCursor+1)%UE_ARRAY_COUNT(RecentHits);
    ++FrameBursts; BurstTokens-=1.f; Camera=ViewCamera;
    const auto Surface=ResolveSurface(Hit);
    const bool Full=ApparentDistance<FMath::Max(0.f,FPSImpact::DetailDistance.GetValueOnGameThread());
    const bool Far=ApparentDistance>6000.f;
    const FVector Normal=Hit.ImpactNormal.GetSafeNormal(SMALL_NUMBER,FVector::UpVector);
    if (Surface==EFPSImpactSurface::Flesh)
    {
        FHitResult Ground;
        const bool bLanding=Distance<4500.f && FindBloodLanding(Hit,ViewCamera,Now,Ground);
        AddFleshBurst(Hit,Normal,Full,Far,bLanding?&Ground:nullptr);
        if (bLanding) AddBloodStain(Ground,Hit.ImpactPoint,Now);
        PlayImpactSound(Hit.ImpactPoint,Surface,Distance,Now);
        return;
    }
    const FVector Position=Hit.ImpactPoint+Normal*1.2f;
    const int32 SparkCount=Surface==EFPSImpactSurface::Metal?(Full?5:Far?1:2):0;
    const int32 ChipCount=Surface==EFPSImpactSurface::Flesh?0:(Full?2:Far?0:1);
    for(int32 I=0;I<SparkCount;++I)AddParticle(0,Position,Normal,Surface,1.f);
    AddParticle(1,Position,Normal,Surface,Far?1.25f:1.f);
    for(int32 I=0;I<ChipCount;++I)AddParticle(2,Position,Normal,Surface,1.f);
    if (ApparentDistance<3000.f) AddDecal(Hit,Surface,Now);
    PlayImpactSound(Hit.ImpactPoint,Surface,Distance,Now);
}

void UFPSImpactFXSubsystem::AddParticle(int32 Group,const FVector& Position,const FVector& Normal,EFPSImpactSurface Surface,float DetailScale)
{
    if(ActiveParticles>=MaxActiveParticles)return;
    const double Now=GetWorld()->GetTimeSeconds();
    const int32 Start=FPSImpact::Starts[Group],End=Start+FPSImpact::Counts[Group];
    int32 Slot=INDEX_NONE;
    for(int32 I=Start;I<End;++I)if(Particles[I].Life<=0.f){Slot=I;break;}
    if(Slot==INDEX_NONE)return; // Full pool drops cosmetic detail; never allocates.
    auto& P=Particles[Slot];P=FParticle();
    P.Position=Position;P.Born=Now;
    P.Color=FPSImpact::DustColors[static_cast<uint8>(Surface)];
    FVector Side=FMath::VRand();Side=FVector::VectorPlaneProject(Side,Normal);
    P.Velocity=Normal*FMath::FRandRange(Group==0?180.f:35.f,Group==0?420.f:100.f)+Side*(Group==0?115.f:45.f);
    P.Rotation=FRotator(FMath::FRandRange(-180.f,180.f),FMath::FRandRange(-180.f,180.f),FMath::FRandRange(-180.f,180.f));
    if(Group==0){P.Life=FMath::FRandRange(.12f,.24f);P.Gravity=-450.f;P.Size=FVector(.65f,FMath::FRandRange(3.f,6.f),1.f);P.Color=FLinearColor(1.f,.56f,.12f);P.Opacity=.95f;}
    else if(Group==1){P.Life=Surface==EFPSImpactSurface::Flesh?.18f:FMath::FRandRange(.26f,.42f);P.Gravity=12.f;P.Size=FVector(Surface==EFPSImpactSurface::Metal?4.f:7.f)*DetailScale;P.Opacity=Surface==EFPSImpactSurface::Glass?.19f:.48f;}
    else
    {
        P.Life=FMath::FRandRange(.22f,.38f);P.Gravity=-650.f;P.Opacity=1.f;
        P.Size=Surface==EFPSImpactSurface::Wood?FVector(.18f,.4f,FMath::FRandRange(1.5f,3.f)):FVector(.45f,.7f,.4f);
        P.Spin=FRotator(500.f,-370.f,650.f);
        if(Surface==EFPSImpactSurface::Glass){P.Size=FVector(.1f,.8f,1.4f);P.Color=FLinearColor(.55f,.65f,.68f);}
    }
    ++ActiveParticles;
}

void UFPSImpactFXSubsystem::AddFleshBurst(const FHitResult& Hit,const FVector& Normal,bool Full,bool Far,const FHitResult* Ground)
{
    const double Now=GetWorld()->GetTimeSeconds();
    const FVector Incoming=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(SMALL_NUMBER,-Normal);
    // Entry spray leaves the actual struck surface. Bias glancing hits toward
    // the incoming bullet, rather than tying a red cloud to the camera or bone.
    const FVector Axis=(Normal*.72f-Incoming*.28f).GetSafeNormal(SMALL_NUMBER,Normal);
    for(int32 Group=3;Group<ParticleGroups;++Group)
    {
        const int32 Wanted=Group==3?(Full?3:Far?1:2):(Far?1:Full?11:6);
        int32 Added=0;
        const int32 Start=FPSImpact::Starts[Group],End=Start+FPSImpact::Counts[Group];
        for(int32 Slot=Start;Slot<End && Added<Wanted && ActiveParticles<MaxActiveParticles;++Slot)
        {
            if(Particles[Slot].Life>0.f)continue;
            auto& P=Particles[Slot];P=FParticle();
            P.Born=Now;
            P.Position=Hit.ImpactPoint+Normal*2.f;
            P.Rotation.Roll=FMath::FRandRange(-180.f,180.f);
            P.Variation=FMath::FRand();
            const FVector Direction=FMath::VRandCone(Axis,FMath::DegreesToRadians(Group==3?36.f:48.f));
            if(Group==3)
            {
                P.Position+=FVector::VectorPlaneProject(Direction,Normal)*3.f;
                P.Velocity=Direction*FMath::FRandRange(65.f,115.f)+FVector(0,0,14.f);
                P.Life=FMath::FRandRange(.32f,.44f);P.Gravity=-25.f;
                P.Size=FVector(FMath::FRandRange(25.f,33.f)*(Far?1.15f:1.f));
                P.Color=FLinearColor(.34f,.010f,.007f);
                P.Opacity=Added==0?.80f:.48f;
            }
            else
            {
                P.Velocity=Direction*FMath::FRandRange(150.f,290.f)+FVector(0,0,24.f);
                P.Life=FMath::FRandRange(.60f,.88f);P.Gravity=-980.f;
                P.Size=FVector(FMath::FRandRange(1.6f,2.9f),FMath::FRandRange(5.f,9.f),1.f);
                P.Color=FLinearColor(FMath::FRandRange(.23f,.36f),.006f,.004f);
                P.Opacity=.96f;
                if(Ground)
                {
                    P.LandingPoint=Ground->ImpactPoint;P.LandingNormal=Ground->ImpactNormal;
                    P.bHasLandingPlane=true;
                    if(Added<4)
                    {
                        // A few heavier drops connect the airborne burst to its
                        // queried landing point. Solve the same analytic motion
                        // used in Tick; no per-drop traces or physics bodies.
                        const float Height=FMath::Max(0.f,static_cast<float>(P.Position.Z-Ground->ImpactPoint.Z));
                        const float Flight=FMath::Clamp(FMath::Sqrt(2.f*Height/980.f),.24f,1.1f)*FMath::FRandRange(.96f,1.06f);
                        const float Travel=(1.f-FMath::Exp(-1.6f*Flight))/1.6f;
                        const FVector Spread=FVector::VectorPlaneProject(FMath::VRand()*FMath::FRandRange(2.f,12.f),P.LandingNormal);
                        const FVector Target=P.LandingPoint+Spread+P.LandingNormal*.5f;
                        P.Velocity=(Target-P.Position-FVector(0,0,P.Gravity*.5f*Flight*Flight))/Travel;
                        P.Life=Flight+.18f;
                        P.Size.Y*=.75f;
                    }
                }
            }
            ++Added;++ActiveParticles;
        }
    }
}

bool UFPSImpactFXSubsystem::FindBloodLanding(const FHitResult& Hit,UCameraComponent* ViewCamera,double Now,FHitResult& Ground)
{
    // At most two queries per accepted burst, globally capped near 11/sec.
    // The vertical fallback reaches the floor below a head/chest hit even when
    // the initial outward ray hits an unsuitable prop or steep wall.
    if(!BloodStainMaterial)return false;
    if(Now-LastBloodStainTime<.09)
    {
        // Closely spaced shots on the same creature share the recent ground
        // result, keeping falling drops connected without extra traces.
        if(Now-LastBloodLandingTime<.18 && LastBloodVictim==Hit.GetActor()
            && IsValid(LastBloodLanding.GetComponent()) && FVector::DistSquared(LastBloodOrigin,Hit.ImpactPoint)<FMath::Square(75.f))
        {Ground=LastBloodLanding;return true;}
        return false;
    }
    LastBloodStainTime=Now;
    const FVector Incoming=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(SMALL_NUMBER,-Hit.ImpactNormal);
    const FVector Axis=(Hit.ImpactNormal*.72f-Incoming*.28f).GetSafeNormal();
    const FVector Start=Hit.ImpactPoint+Hit.ImpactNormal*3.f+FVector(0,0,8.f);
    FVector Offset=FVector::VectorPlaneProject(Axis,FVector::UpVector)*FMath::FRandRange(25.f,70.f);
    Offset+=FVector(FMath::FRandRange(-15.f,15.f),FMath::FRandRange(-15.f,15.f),0.f);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FleshImpactStain),true,Hit.GetActor());
    Params.AddIgnoredActor(ViewCamera->GetOwner());
    for(int32 Attempt=0;Attempt<2;++Attempt)
    {
        const FVector End=Start+(Attempt==0?Offset:FVector::ZeroVector)-FVector(0,0,600.f);
        if(!GetWorld()->LineTraceSingleByChannel(Ground,Start,End,ECC_Visibility,Params))continue;
        UPrimitiveComponent* Component=Ground.GetComponent();
        if(Component && Component->bReceivesDecals && !Component->IsSimulatingPhysics()
            && Ground.ImpactNormal.Z>.35f && !Cast<APawn>(Ground.GetActor()) && !Cast<AVoxelBuildWorld>(Ground.GetActor()))
        {
            LastBloodLanding=Ground;LastBloodOrigin=Hit.ImpactPoint;LastBloodVictim=Hit.GetActor();LastBloodLandingTime=Now;
            return true;
        }
        if(Ground.GetActor() && Cast<APawn>(Ground.GetActor()))Params.AddIgnoredActor(Ground.GetActor());
    }
    return false;
}

void UFPSImpactFXSubsystem::AddBloodStain(const FHitResult& Ground,const FVector& Origin,double Now)
{
    UPrimitiveComponent* Component=Ground.GetComponent();
    int32 Index=INDEX_NONE;
    for(int32 I=0;I<BloodDecalSlots;++I)
        if(BloodDecalUntil[I]>Now && BloodDecals[I]->GetAttachParent()==Component
            && FVector::DistSquared(BloodDecals[I]->GetComponentLocation(),Ground.ImpactPoint)<FMath::Square(25.f))
        {Index=I;break;}
    if(Index!=INDEX_NONE)
    {
        // Repeated hits feed the existing patch instead of suppressing blood
        // or layering identical transparent decals at the same location.
        auto* Existing=BloodDecals[Index].Get();
        const float Growth=FMath::Min(1.13f,34.f/Existing->DecalSize.Y);
        Existing->DecalSize.Y*=Growth;Existing->DecalSize.Z*=Growth;
        Existing->MarkRenderStateDirty();
        FLinearColor Color=Existing->DecalColor;
        const float RemainingFlight=FMath::Max(0.f,Color.G-static_cast<float>(Now));
        Existing->SetFadeIn(RemainingFlight,RemainingFlight>0.f?.09f:0.f);
        Existing->SetFadeOut(RemainingFlight+22.f,6.f,false);Existing->SetLifeSpan(0.f);
        Color.G=static_cast<float>(Now)+RemainingFlight;Existing->SetDecalColor(Color);
        BloodDecalUntil[Index]=Now+RemainingFlight+28.;
        return;
    }
    Index=BloodDecalCursor;BloodDecalCursor=(BloodDecalCursor+1)%BloodDecalSlots;
    auto* Decal=BloodDecals[Index].Get();Decal->SetVisibility(false);
    Decal->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    const FVector Normal=Ground.ImpactNormal.GetSafeNormal();
    const FQuat Rotation=(-Normal).ToOrientationQuat()*FQuat(FVector::ForwardVector,FMath::FRandRange(0.f,2.f*PI));
    const float Radius=FMath::FRandRange(16.f,24.f);
    Decal->DecalSize=FVector(8.f,Radius,Radius*FMath::FRandRange(.85f,1.2f));
    Decal->SetWorldLocationAndRotation(Ground.ImpactPoint+Normal*.3f,Rotation);
    Decal->AttachToComponent(Component,FAttachmentTransformRules::KeepWorldTransform);
    const float Height=FMath::Max(0.f,static_cast<float>(Origin.Z-Ground.ImpactPoint.Z));
    const float Flight=FMath::Clamp(FMath::Sqrt(2.f*Height/980.f),.24f,1.1f);
    Decal->SetDecalColor(FLinearColor(FMath::FRand(),static_cast<float>(Now)+Flight,1.f,1.f));
    Decal->SetFadeIn(Flight,.09f);Decal->SetFadeOut(Flight+22.f,6.f,false);Decal->SetLifeSpan(0.f);
    Decal->SetVisibility(true);BloodDecalUntil[Index]=Now+Flight+28.;
}

void UFPSImpactFXSubsystem::AddDecal(const FHitResult& Hit,EFPSImpactSurface Surface,double Now)
{
    // No projected bullet holes on deforming flesh or loose dirt. No decals on
    // merged destructible buildings: a removed cell would leave a floating mark.
    if(Surface==EFPSImpactSurface::Flesh || Surface==EFPSImpactSurface::Dirt || Cast<AVoxelBuildWorld>(Hit.GetActor()) || !Hit.GetComponent())return;
    UMaterialInterface* Material=DecalMaterials[static_cast<uint8>(Surface)];
    if(!Material)return;
    for(int32 I=0;I<DecalSlots;++I)
        if(DecalUntil[I]>Now && Decals[I]->GetAttachParent()==Hit.GetComponent() && FVector::DistSquared(Decals[I]->GetComponentLocation(),Hit.ImpactPoint)<16.f)return;
    const int32 Index=DecalCursor;DecalCursor=(DecalCursor+1)%DecalSlots;
    auto* Decal=Decals[Index].Get();Decal->SetVisibility(false);
    Decal->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Decal->SetDecalMaterial(Material);
    const FVector Normal=Hit.ImpactNormal.GetSafeNormal();
    const FQuat Rotation=(-Normal).ToOrientationQuat()*FQuat(FVector::ForwardVector,FMath::FRandRange(0.f,2.f*PI));
    Decal->DecalSize=FVector(.7f,2.3f,Surface==EFPSImpactSurface::Wood?3.5f:2.3f);
    Decal->SetWorldLocationAndRotation(Hit.ImpactPoint+Normal*.3f,Rotation);
    Decal->AttachToComponent(Hit.GetComponent(),FAttachmentTransformRules::KeepWorldTransform,Hit.BoneName);
    Decal->SetFadeIn(0.f,.025f);Decal->SetFadeOut(6.f,1.f,false);
    // SetFadeOut schedules component destruction even when owner destruction
    // is disabled. Keep the fixed pool alive while retaining the shader fade.
    Decal->SetLifeSpan(0.f);
    Decal->SetVisibility(true);DecalUntil[Index]=Now+7.;
}

void UFPSImpactFXSubsystem::PlayImpactSound(const FVector& Position,EFPSImpactSurface Surface,float Distance,double Now)
{
    if(Distance>6000.f || Now-LastSoundTime<.035)return;
    int32 Slot=INDEX_NONE;
    for(int32 I=0;I<VoiceSlots;++I)if(VoiceUntil[I]<=Now && !Voices[I]->IsPlaying()){Slot=I;break;}
    if(Slot==INDEX_NONE)return; // Preserve playing tails; skip extra impacts.
    const int32 Bank=static_cast<uint8>(Surface);
    int32 Variant=FMath::RandRange(0,2);if(Variant==LastSoundVariant[Bank])Variant=(Variant+1)%3;
    USoundBase* Sound=Sounds[Bank*3+Variant];if(!Sound)return;
    auto* Voice=Voices[Slot].Get();Voice->SetSound(Sound);Voice->SetWorldLocation(Position);
    Voice->SetVolumeMultiplier(Surface==EFPSImpactSurface::Metal?.28f:.23f);
    Voice->SetPitchMultiplier(FMath::FRandRange(.94f,1.06f));Voice->Play();
    VoiceUntil[Slot]=Now+.45;LastSoundVariant[Bank]=Variant;LastSoundTime=Now;
}

void UFPSImpactFXSubsystem::Tick(float DeltaTime)
{
    const double Now=GetWorld()->GetTimeSeconds();
    const FVector Eye=Camera.IsValid()?Camera->GetComponentLocation():FVector::ZeroVector;
    for(int32 Group=0;Group<ParticleGroups;++Group)
    {
        bool Dirty=false;
        for(int32 Local=0;Local<FPSImpact::Counts[Group];++Local)
        {
            auto& P=Particles[FPSImpact::Starts[Group]+Local];if(P.Life<=0.f)continue;
            Dirty=true;
            const float Age=FMath::Max(0.f,static_cast<float>(Now-P.Born));
            if(Age>=P.Life || !Camera.IsValid())
            {
                P.Life=0.f;--ActiveParticles;
                Transforms[Group][Local].SetScale3D(FVector::ZeroVector);
                continue;
            }
            const float Life=Age/P.Life;
            // Analytic non-colliding motion: no raycasts/Chaos bodies per fragment.
            const float Drag=Group==3?6.f:Group==4?1.6f:Group==1?5.f:0.f;
            const float Damping=Drag>0.f?FMath::Exp(-Drag*Age):1.f;
            const float Travel=Drag>0.f?(1.f-Damping)/Drag:Age;
            const FVector Position=P.Position+P.Velocity*Travel+FVector(0,0,P.Gravity*.5f*Age*Age);
            if(P.bHasLandingPlane && FVector::DotProduct(Position-P.LandingPoint,P.LandingNormal)<.3f)
            {
                P.Life=0.f;--ActiveParticles;Transforms[Group][Local].SetScale3D(FVector::ZeroVector);
                continue;
            }
            const FVector Velocity=P.Velocity*Damping+FVector(0,0,P.Gravity*Age);
            FQuat Rotation=(P.Rotation+P.Spin*Age).Quaternion();
            if(Group!=2)
            {
                const FVector Facing=(Eye-Position).GetSafeNormal();
                Rotation=(Group==0 || Group==4)?FRotationMatrix::MakeFromZY(Facing,Velocity).ToQuat()
                    :FRotationMatrix::MakeFromZ(Facing).ToQuat()*FQuat(FVector::UpVector,FMath::DegreesToRadians(P.Rotation.Roll));
            }
            const float SizeScale=Group==1?.65f+Life*1.5f:Group==3?.70f+Life*1.25f:1.f;
            FVector Size=P.Size*SizeScale;
            if(Group==4)Size.Y*=FMath::Lerp(1.f,.50f,Life);
            Transforms[Group][Local]=FTransform(Rotation,Position,Size/100.f);
            float Fade=Group==4?1.f-FMath::SmoothStep(.78f,1.f,Life):Group==2?1.f-FMath::SmoothStep(.5f,1.f,Life):FMath::Square(1.f-Life);
            if(Group==3)Fade=FMath::SmoothStep(0.f,.035f,Life)*(1.f-FMath::SmoothStep(.20f,1.f,Life));
            const float NearFade=Group>=3?FMath::SmoothStep(12.f,45.f,static_cast<float>(FVector::Dist(Eye,Position))):1.f;
            const float Data[]={P.Color.R,P.Color.G,P.Color.B,P.Opacity*Fade*NearFade,Life,P.Variation};
            Renderers[Group]->SetCustomData(Local,MakeArrayView(Data,Group>=3?6:4),false);
        }
        if(Dirty)Renderers[Group]->BatchUpdateInstancesTransforms(0,Transforms[Group],false,true,true);
    }
}

TStatId UFPSImpactFXSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UFPSImpactFXSubsystem,STATGROUP_Tickables); }

void UFPSImpactFXSubsystem::Deinitialize()
{
    bReady=false;ActiveParticles=0;
    for(const auto& Renderer:Renderers)if(Renderer)Renderer->DestroyComponent();
    for(const auto& Decal:Decals)if(Decal)Decal->DestroyComponent();
    for(const auto& Decal:BloodDecals)if(Decal)Decal->DestroyComponent();
    for(const auto& Voice:Voices)if(Voice){Voice->Stop();Voice->DestroyComponent();}
    Renderers.Reset();Decals.Reset();BloodDecals.Reset();Voices.Reset();SurfaceCache.Reset();Camera.Reset();
    LastBloodLanding=FHitResult();LastBloodVictim.Reset();
    Super::Deinitialize();
}
