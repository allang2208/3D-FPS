#include "FPSIceWall.h"
#include "FPSIceWallComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

AFPSIceWall::AFPSIceWall()
{
    PrimaryActorTick.bCanEverTick=true;
    Scene=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Scene);
    Barrier=CreateDefaultSubobject<UBoxComponent>(TEXT("ContinuousIceBarrier"));Barrier->SetupAttachment(Scene);
    Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Barrier->SetCollisionObjectType(ECC_WorldStatic);Barrier->SetCollisionResponseToAllChannels(ECR_Block);
    Barrier->SetGenerateOverlapEvents(false);Barrier->SetCanEverAffectNavigation(false);
    Barrier->CanCharacterStepUpOn=ECB_No;
    Tags.Add(TEXT("IceWall"));
    Tags.Add(TEXT("Neutral"));Tags.Add(TEXT("NoSkillTraining"));
    SetCanBeDamaged(false);
}

void AFPSIceWall::Initialize(UFPSIceWallComponent* Ability,const FIceWallCast& Cast,
    const TArray<TObjectPtr<UStaticMesh>>& Meshes,UMaterialInterface* Ice,
    UMaterialInterface* Preview,UParticleSystem* ShatterFX,USoundBase* Sound,bool bGhost)
{
    Component=Ability;Tuning=Cast;BreakFX=ShatterFX;BreakSound=Sound;
    MaxHealth=FMath::Max(1.f,Cast.MaxHealth);Health=0;
    State=bGhost?EState::Preview:EState::Seed;
    if(bGhost)GhostMaterial=UMaterialInstanceDynamic::Create(Preview,this);
    for(int32 I=0;I<Meshes.Num();++I)
    {
        auto* Mesh=NewObject<UInstancedStaticMeshComponent>(this);
        AddInstanceComponent(Mesh);Mesh->SetupAttachment(Scene);Mesh->SetStaticMesh(Meshes[I]);
        Mesh->SetMaterial(0,bGhost?static_cast<UMaterialInterface*>(GhostMaterial.Get()):Ice);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
        Mesh->SetCastShadow(!bGhost);Mesh->bReceivesDecals=false;Mesh->RegisterComponent();Blocks.Add(Mesh);
    }
    if(!bGhost)
        for(int32 I=0;I<3;++I)Blocks[I%Blocks.Num()]->AddInstance(FTransform(
            FRotator(I==0?8:-11,I*37,5),FVector(I==0?0:-2,I==0?0:(I==1?-9:8),I==2?5:-2),
            I==0?FVector(.18f,.22f,.22f):FVector(.075f,.085f,.105f)));
    else SetActorTickEnabled(false);
}

void AFPSIceWall::Gather(float Fraction,const FVector& Origin)
{
    if(State!=EState::Seed)return;
    SetActorLocation(Origin);
    SetActorScale3D(FVector(FMath::Lerp(.12f,1.f,FMath::Clamp(Fraction,0.f,1.f))));
    SetActorRotation(FRotator(3*FMath::Sin(GetWorld()->GetTimeSeconds()*.8f),GetWorld()->GetTimeSeconds()*7.f,0));
}

void AFPSIceWall::BuildLayout(EIceWallShape Shape)
{
    if(LayoutShape==int32(Shape))return;
    LayoutShape=int32(Shape);for(const auto& Mesh:Blocks)Mesh->ClearInstances();
    const float Height=Tuning.Height(Shape),Width=Tuning.Width();
    const int32 Columns=FMath::Max(1,FMath::RoundToInt(Width/FMath::Max(75.f,Tuning.SegmentSpacing*2.f)));
    FRandomStream Random(93030); // Preview and final wall share the same fractured slab layout.
    TArray<float> ColumnWeights;
    float TotalWidthWeight=0;
    for(int32 Column=0;Column<Columns;++Column)
    {
        const float Weight=Random.FRandRange(.8f,1.2f);
        ColumnWeights.Add(Weight);TotalWidthWeight+=Weight;
    }
    float Cursor=-Width*.5f;
    for(int32 Column=0;Column<Columns;++Column)
    {
        const float Span=Width*ColumnWeights[Column]/TotalWidthWeight;
        const int32 Pieces=Shape==EIceWallShape::Low?(Column%3==1?1:2):Random.RandRange(2,4);
        TArray<float> HeightWeights;
        float TotalHeightWeight=0;
        for(int32 Piece=0;Piece<Pieces;++Piece)
        {
            const float Weight=Random.FRandRange(.65f,1.35f);
            HeightWeights.Add(Weight);TotalHeightWeight+=Weight;
        }
        float Bottom=0;
        for(int32 Piece=0;Piece<Pieces;++Piece)
        {
            const float PieceHeight=Height*HeightWeights[Piece]/TotalHeightWeight;
            const float Depth=Tuning.Thickness+Random.FRandRange(0,1.5f);
            const FVector Center(0,Cursor+Span*.5f,Bottom+PieceHeight*.5f);
            // No shared horizontal courses. Bearing faces still meet the continuous
            // collision volume; low-wall tops remain at the exact bipod height.
            Blocks[Random.RandRange(0,Blocks.Num()-1)]->AddInstance(FTransform(FQuat::Identity,Center,FVector((Depth+.5f)/100,(Span+1.8f)/100,(PieceHeight+.5f)/100)));
            Bottom+=PieceHeight;
        }
        Cursor+=Span;
    }
}

void AFPSIceWall::PreviewAt(const FIceWallPlacement& Placement)
{
    if(State!=EState::Preview)return;
    Plan=Placement;BuildLayout(Plan.Shape);SetActorLocationAndRotation(Plan.Location,Plan.Rotation);
    if(GhostMaterial)GhostMaterial->SetVectorParameterValue(TEXT("Tint"),Plan.bValid?FLinearColor(.08f,.8f,.38f):FLinearColor(.9f,.05f,.035f));
    SetActorHiddenInGame(false);
}

void AFPSIceWall::Launch(const FVector& Origin,const FIceWallPlacement& Placement)
{
    Plan=Placement;FlightStart=Origin;Age=0;State=EState::Flight;
    FlightSeconds=FMath::Max(.15f,float(FVector::Distance(Origin,Plan.Location))/Tuning.FlySpeed);
    SetActorScale3D(FVector::OneVector);SetActorLocation(Origin);
}

void AFPSIceWall::Land()
{
    FString Reason;
    if(!Component.IsValid()||!Component->ValidatePlacement(Plan,Tuning,true,Reason)){Shatter();return;}
    State=EState::Growing;Age=0;LayoutShape=-1;BuildLayout(Plan.Shape);
    SetActorLocationAndRotation(Plan.Location,Plan.Rotation);SetActorScale3D(FVector::OneVector);
    for(const auto& Mesh:Blocks)Mesh->SetRelativeScale3D(FVector(1,1,.02));
}

void AFPSIceWall::BecomeSolid()
{
    FString Reason;
    if(!Component.IsValid()||!Component->ValidatePlacement(Plan,Tuning,true,Reason)){Shatter();return;}
    auto* M=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    auto* Shooter=GetInstigator();
    if(!M||!Shooter){Destroy();return;}
    // Resolve every occupied enemy once before enabling the single blocking volume.
    M->ApplyIceWallSpawn(Shooter,Plan,Tuning);
    if(!Component->ValidatePlacement(Plan,Tuning,false,Reason)){Shatter();return;}
    Barrier->SetBoxExtent(FVector(Tuning.Thickness*.5f,Tuning.Width()*.5f,Tuning.Height(Plan.Shape)*.5f));
    Barrier->SetRelativeLocation(FVector(0,0,Tuning.Height(Plan.Shape)*.5f));
    Barrier->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Barrier->SetCanEverAffectNavigation(true);
    Health=MaxHealth;SetCanBeDamaged(true);
    State=EState::Solid;Age=0;AuraAge=0;SetActorTickInterval(.1f);
}

bool AFPSIceWall::IsSolid() const { return State==EState::Solid; }

float AFPSIceWall::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||!IsSolid()||!CanBeDamaged()||Damage<=0||!FMath::IsFinite(Damage))return 0;
    const float Applied=FMath::Min(Health,Damage);
    Health-=Applied;
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if(Health<=0)Shatter();
    return Applied;
}

void AFPSIceWall::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    if(State==EState::Flight)
    {
        const float T=FMath::Clamp(Age/FlightSeconds,0.f,1.f);
        // The seed stops above the ground, never launches a damaging wall-sized projectile.
        const FVector End=Plan.Location+FVector(0,0,24);
        const FVector Next=FMath::Lerp(FlightStart,End,T);
        FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallSeed),false,this);Query.AddIgnoredActor(GetInstigator());
        bool Blocked=false;
        for(int32 Retry=0;Retry<8;++Retry)
        {
            Blocked=GetWorld()->SweepSingleByChannel(Hit,GetActorLocation(),Next,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(6),Query);
            if(!Blocked)break;
            const auto* Actor=Hit.GetActor();
            if(!Actor||!Actor->FindComponentByClass<UMonsterCombatComponent>()||Actor->ActorHasTag(TEXT("Friendly")))break;
            Query.AddIgnoredActor(Actor); // Landing owns enemy impact/push; the harmless seed passes enemies.
            // If the per-frame pass budget is exhausted, resume from this point next frame.
            if(Retry==7){SetActorLocation(Hit.Location);return;}
            Blocked=false;
        }
        if(Blocked){Shatter();return;}
        SetActorLocation(Next);
        if(T>=1)Land();
    }
    else if(State==EState::Growing)
    {
        const float T=FMath::Clamp(Age/Tuning.GrowthSeconds,0.f,1.f),Growth=T*T*(3-2*T);
        for(const auto& Mesh:Blocks)Mesh->SetRelativeScale3D(FVector(1,1,FMath::Max(.02f,Growth)));
        if(T>=1)BecomeSolid();
    }
    else if(State==EState::Solid)
    {
        if(Age>=Tuning.Duration){Shatter();return;}
        AuraAge+=Delta;
        if(AuraAge>=Tuning.ChillInterval)
        {
            AuraAge=FMath::Fmod(AuraAge,Tuning.ChillInterval);
            if(auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())M->ApplyIceWallChill(GetInstigator(),Plan,Tuning);
        }
    }
}

void AFPSIceWall::Shatter()
{
    if(State==EState::Shattered||IsActorBeingDestroyed())return;
    const EState Previous=State;State=EState::Shattered;
    SetCanBeDamaged(false);SetActorTickEnabled(false);
    Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);Barrier->SetCanEverAffectNavigation(false);
    if(Previous!=EState::Preview)
    {
        if(BreakSound)UGameplayStatics::PlaySoundAtLocation(this,BreakSound,GetActorLocation(),.65f);
        if(BreakFX)
        {
            const int32 Bursts=(Previous==EState::Solid||Previous==EState::Growing)?FMath::Min(8,Tuning.Count):1;
            for(int32 I=0;I<Bursts;++I)
            {
                const FVector At=GetActorLocation()+GetActorRightVector()*((I+.5f)/Bursts-.5f)*Tuning.Width()+FVector(0,0,35);
                UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),BreakFX,At,FRotator::ZeroRotator,FVector(1.4f));
            }
        }
    }
    Destroy();
}

void AFPSIceWall::EndPlay(EEndPlayReason::Type Reason)
{
    Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);Barrier->SetCanEverAffectNavigation(false);
    if(Component.IsValid())Component->WallEnded(this);
    Super::EndPlay(Reason);
}
