#include "WarhammerSlamFXSubsystem.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"

namespace
{
    constexpr int32 Capacity=8;
    constexpr float Lifetime=5.f;
    const FSoftObjectPath PlanePath(TEXT("/Engine/BasicShapes/Plane.Plane"));
    const FSoftObjectPath DustPath(TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/M_WarhammerDust.M_WarhammerDust"));
    const FSoftObjectPath RockPath(TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/SM_WarhammerDebris.SM_WarhammerDebris"));
    const FSoftObjectPath RockMaterialPath(TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/M_WarhammerDebris.M_WarhammerDebris"));
    const FSoftObjectPath CrackPath(TEXT("/Game/Weapons/SteelWarhammer20261014/CrackReliefV3/M_WarhammerFractureRelief.M_WarhammerFractureRelief"));
}

bool UWarhammerSlamFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type==EWorldType::Game||Type==EWorldType::PIE;
}

void UWarhammerSlamFXSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if(World.GetNetMode()==NM_DedicatedServer)return;
    // Resolve only at impact; keep a retained async handle so no slam loads from disk.
    Assets=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{PlanePath,DustPath,RockPath,RockMaterialPath,CrackPath});
    Impacts.SetNum(Capacity);Dust.SetNum(Capacity);Debris.SetNum(Capacity);
    Cracks.SetNum(Capacity);CrackMaterials.SetNum(Capacity);
}

bool UWarhammerSlamFXSubsystem::PrepareSlot(int32 Index)
{
    if(Dust[Index])return true;
    auto* Plane=Cast<UStaticMesh>(PlanePath.ResolveObject());
    auto* Rock=Cast<UStaticMesh>(RockPath.ResolveObject());
    auto* DustMat=Cast<UMaterialInterface>(DustPath.ResolveObject());
    auto* RockMat=Cast<UMaterialInterface>(RockMaterialPath.ResolveObject());
    auto* CrackMat=Cast<UMaterialInterface>(CrackPath.ResolveObject());
    if(!Plane||!Rock||!DustMat||!RockMat||!CrackMat)return false;
    auto MakeInstances=[&](UStaticMesh* Mesh,UMaterialInterface* Material,int32 DataCount)
    {
        auto* C=NewObject<UInstancedStaticMeshComponent>(GetWorld()->GetWorldSettings());
        C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);C->SetMaterial(0,Material);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);
        C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);C->SetReceivesDecals(false);
        C->SetNumCustomDataFloats(DataCount);C->SetVisibility(false);C->RegisterComponent();C->PrecachePSOs();return C;
    };
    Dust[Index]=MakeInstances(Plane,DustMat,3);Debris[Index]=MakeInstances(Rock,RockMat,0);
    auto* Decal=NewObject<UDecalComponent>(GetWorld()->GetWorldSettings());
    Decal->SetDecalMaterial(CrackMat);Decal->SetFadeScreenSize(.001f);Decal->SetVisibility(false);Decal->RegisterComponent();Decal->PrecachePSOs();
    Cracks[Index]=Decal;CrackMaterials[Index]=Decal->CreateDynamicMaterialInstance();
    return true;
}

bool UWarhammerSlamFXSubsystem::PrepareBackground()
{
    if(Impacts.IsEmpty())return true;
    for(int32 I=0;I<Impacts.Num();++I)
    {
        if(!Dust[I]){PrepareSlot(I);return false;} // At most one slot per queue tick.
        if(Dust[I]->IsPSOPrecaching()||Debris[I]->IsPSOPrecaching()||Cracks[I]->GetPSOPrecacheComponentData().IsPSOPrecaching())return false;
    }
    return true;
}

void UWarhammerSlamFXSubsystem::Emit(const FVector& Point,const FQuat& Rotation,float Radius,float Age)
{
    if(Impacts.IsEmpty()||Age>=Lifetime)return;
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!Camera||FVector::DistSquared(Camera->GetCameraLocation(),Point)>FMath::Square(6000.f))return;
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    const int32 Detail=Budget?Budget->AllocateDetail(Point,12,true):12;
    if(Detail<2)return;
    int32 Index=0;
    for(int32 I=1;I<Impacts.Num();++I)if(Impacts[I].Age>Impacts[Index].Age)Index=I;
    if(!PrepareSlot(Index))return;
    FImpact& Impact=Impacts[Index];
    if(Impact.Age>=Lifetime)++ActiveCount;
    Impact=FImpact();Impact.Age=FMath::Max(0.f,Age);Impact.Point=Point;Impact.Rotation=Rotation;
    FRandomStream Random(GetTypeHash(Point)^uint32(GetWorld()->GetTimeSeconds()*1000.));
    const int32 PuffCount=FMath::Clamp(Detail,4,10),StoneCount=FMath::Clamp(Detail+2,4,14);
    Dust[Index]->ClearInstances();Debris[Index]->ClearInstances();
    Dust[Index]->SetWorldLocation(Point);Debris[Index]->SetWorldTransform(FTransform(Rotation,Point));
    Dust[Index]->SetVisibility(true);Debris[Index]->SetVisibility(true);Cracks[Index]->SetVisibility(true);
    for(int32 I=0;I<PuffCount;++I)
    {
        const float Angle=I*2.f*PI/PuffCount+Random.FRandRange(-.2f,.2f);
        FPuff P;P.Direction=FVector(FMath::Cos(Angle),FMath::Sin(Angle),0);
        P.Travel=Radius*Random.FRandRange(.35f,.72f);P.Size=Random.FRandRange(75,115);
        P.Seed=Random.FRand();P.Delay=I<2?0.f:.045f;P.Life=Random.FRandRange(1.3f,1.9f);
        if(I<2){P.Travel*=.22f;P.Size*=.9f;}
        // Decorative motion is clipped to nearby cover without spending gameplay query budgets.
        if(Budget&&Budget->ReserveGeometryQueries(1))
        {
            FHitResult Hit;const FVector Start=Point+Rotation.GetAxisZ()*18.f;
            const FVector End=Start+Rotation.RotateVector(P.Direction)*P.Travel;
            FCollisionQueryParams Q(SCENE_QUERY_STAT(WarhammerDustCover),false);
            if(GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Q))
                P.Travel=FMath::Max(5.f,float(Hit.Distance)-P.Size*.25f);
        }
        Impact.Puffs.Add(P);Dust[Index]->AddInstance(FTransform(FVector::ZeroVector));
    }
    for(int32 I=0;I<StoneCount;++I)
    {
        const FPuff& P=Impact.Puffs[I%PuffCount];
        FStone S;S.Velocity=P.Direction*Random.FRandRange(140,260);
        S.Velocity.Z=Random.FRandRange(190,310);
        const float FlightSeconds=2*S.Velocity.Z/980.f;
        const float MaxSpeed=P.Travel/FMath::Max(.01f,FlightSeconds*1.14f);
        const float Speed=FMath::Min(float(S.Velocity.Size2D()),MaxSpeed);
        S.Velocity.X=P.Direction.X*Speed;S.Velocity.Y=P.Direction.Y*Speed;
        S.Axis=Random.VRand();S.Rotation=Random.VRand().Rotation().Quaternion();
        S.Spin=Random.FRandRange(4,11);S.Size=Random.FRandRange(1.5f,4.5f);
        Impact.Stones.Add(S);Debris[Index]->AddInstance(FTransform(FVector::ZeroVector));
    }
    // Thin, floor-normal projection prevents a hovering plane and limits wall/ceiling bleed.
    Cracks[Index]->DecalSize=FVector(7.f,Radius*.66f,Radius*.66f);
    Cracks[Index]->SetWorldLocation(Point);
    Cracks[Index]->SetWorldRotation(FRotationMatrix::MakeFromX(-Rotation.GetAxisZ()).Rotator());
    Cracks[Index]->MarkRenderStateDirty();
    CrackMaterials[Index]->SetScalarParameterValue(TEXT("Seed"),Random.FRand());
    CrackMaterials[Index]->SetScalarParameterValue(TEXT("Age"),Impact.Age);
}

void UWarhammerSlamFXSubsystem::Tick(float Delta)
{
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!Camera)return;
    const FVector Eye=Camera->GetCameraLocation();
    for(int32 I=0;I<Impacts.Num();++I)
    {
        auto& Impact=Impacts[I];if(Impact.Age>=Lifetime)continue;
        Impact.Age+=Delta;
        if(Impact.Age>=Lifetime)
        {
            Dust[I]->SetVisibility(false);Debris[I]->SetVisibility(false);Cracks[I]->SetVisibility(false);
            --ActiveCount;continue;
        }
        CrackMaterials[I]->SetScalarParameterValue(TEXT("Age"),Impact.Age);
        if(Impact.Age<2.f)
        {
            for(int32 J=0;J<Impact.Puffs.Num();++J)
            {
                const auto& P=Impact.Puffs[J];const float A=FMath::Max(0.f,Impact.Age-P.Delay);
                const float N=FMath::Clamp(A/P.Life,0.f,1.f),Spread=1-FMath::Exp(-A*3.7f);
                FVector Offset=P.Direction*P.Travel*Spread;
                Offset.Z=22.f+30.f*N+(J<2?26.f*N:0.f);
                Offset=Impact.Rotation.RotateVector(Offset);
                const FVector Position=Impact.Point+Offset;
                const FQuat Facing=FRotationMatrix::MakeFromZY((Eye-Position).GetSafeNormal(),Impact.Rotation.GetAxisZ()).ToQuat();
                const float Size=P.Size*(.55f+.95f*Spread);
                const FVector Scale(Size/100.f,Size*(J<2?1.f:.66f)/100.f,1.f);
                Dust[I]->UpdateInstanceTransform(J,FTransform(Facing,Offset,Scale),false,false,true);
                const float NearFade=FMath::Clamp(float(FVector::Distance(Eye,Position)-35.f)/90.f,0.f,1.f);
                const float Fade=FMath::Clamp(A/.06f,0.f,1.f)*(1-FMath::SmoothStep(.24f,1.f,N))*NearFade*.6f;
                Dust[I]->SetCustomDataValue(J,0,Fade,false);Dust[I]->SetCustomDataValue(J,1,P.Seed,false);
                Dust[I]->SetCustomDataValue(J,2,N,false);
            }
            Dust[I]->MarkRenderStateDirty();
        }
        else Dust[I]->SetVisibility(false);
        if(Impact.Age<1.5f)
        {
            for(int32 J=0;J<Impact.Stones.Num();++J)
            {
                const auto& S=Impact.Stones[J];const float Flight=2.f*S.Velocity.Z/980.f;
                const float T=FMath::Min(Impact.Age,Flight);
                FVector P=S.Velocity*T;P.Z=FMath::Max(0.f,P.Z-490.f*T*T)+S.Size;
                if(Impact.Age>Flight)
                {
                    const float B=FMath::Min(Impact.Age-Flight,.22f);
                    P+=FVector(S.Velocity.X,S.Velocity.Y,0.f)*B*.18f;
                    P.Z+=FMath::Max(0.f,75.f*B-490.f*B*B);
                }
                const float Fade=1.f-FMath::SmoothStep(1.05f,1.5f,Impact.Age);
                const FQuat Turn=FQuat(S.Axis,S.Spin*FMath::Min(Impact.Age,Flight+.22f))*S.Rotation;
                Debris[I]->UpdateInstanceTransform(J,FTransform(Turn,P,FVector(S.Size*Fade)),false,false,true);
            }
            Debris[I]->MarkRenderStateDirty();
        }
        else Debris[I]->SetVisibility(false);
    }
}

TStatId UWarhammerSlamFXSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(WarhammerSlamFX,STATGROUP_Tickables);
}

void UWarhammerSlamFXSubsystem::Deinitialize()
{
    for(const auto& C:Dust)if(C)C->DestroyComponent();
    for(const auto& C:Debris)if(C)C->DestroyComponent();
    for(const auto& C:Cracks)if(C)C->DestroyComponent();
    Dust.Reset();Debris.Reset();Cracks.Reset();CrackMaterials.Reset();Impacts.Reset();ActiveCount=0;
    if(Assets){Assets->CancelHandle();Assets.Reset();}
    Super::Deinitialize();
}
