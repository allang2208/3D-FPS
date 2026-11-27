#include "FPSIceWall.h"
#include "FPSFrostSurfaceMesh.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../Combat/RangedAttackQuery.h"
#include "FPSIceWallComponent.h"
#include "IceWallPlacement.h"
#include "IceWallLandingCameraShake.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"

AFPSIceWall::AFPSIceWall()
{
    PrimaryActorTick.bCanEverTick=true;
    // 联机：服务端权威生成；升降期变换由 ReplicateMovement 搬运，远端只重演 FX。
    bReplicates=true;SetReplicateMovement(true);
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

void AFPSIceWall::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSIceWall,NetTuning);
    DOREPLIFETIME(AFPSIceWall,NetPlan);
    DOREPLIFETIME(AFPSIceWall,NetComponent);
    DOREPLIFETIME(AFPSIceWall,NetReleaseOrigin);
    DOREPLIFETIME(AFPSIceWall,NetState);
    DOREPLIFETIME(AFPSIceWall,NetStateAge);
    DOREPLIFETIME(AFPSIceWall,NetStateAt);
    DOREPLIFETIME(AFPSIceWall,NetDropHeight);
    DOREPLIFETIME(AFPSIceWall,NetHealth);
    // Health is mirrored by OnRep_Health; MaxHealth comes from NetTuning.
    // These local presentation fields are not UPROPERTY(Replicated).
}

void AFPSIceWall::Initialize(UFPSIceWallComponent* Ability,const FIceWallCast& Cast,
    const TArray<TObjectPtr<UStaticMesh>>& Meshes,UMaterialInterface* Ice,
    UMaterialInterface* Preview,UParticleSystem* ShatterFX,USoundBase* Sound,bool bGhost)
{
    Component=Ability;Tuning=Cast;BreakFX=ShatterFX;BreakSound=Sound;
    AddTickPrerequisiteComponent(Ability);
    MaxHealth=FMath::Max(1.f,Cast.MaxHealth);Health=0;
    State=bGhost?EState::Preview:EState::Seed;
    if(GetNetMode()!=NM_DedicatedServer)
    {
        if(bGhost)GhostMaterial=UMaterialInstanceDynamic::Create(Preview,this);
        else if(Ice)WallMaterial=UMaterialInstanceDynamic::Create(Ice,this);
        UMaterialInterface* ActiveMat=bGhost?static_cast<UMaterialInterface*>(GhostMaterial.Get()):(WallMaterial?static_cast<UMaterialInterface*>(WallMaterial.Get()):Ice);
        for(int32 I=0;I<Meshes.Num();++I)
        {
            auto* Mesh=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(Mesh);Mesh->SetupAttachment(Scene);Mesh->SetStaticMesh(Meshes[I]);
            Mesh->SetMaterial(0,ActiveMat);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
            Mesh->SetCastShadow(!bGhost);Mesh->bReceivesDecals=false;Mesh->RegisterComponent();Blocks.Add(Mesh);
        }
        if(!bGhost&&!Blocks.IsEmpty())
            Blocks[0]->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.24f)));
    }
    if(bGhost)SetActorTickEnabled(false);
}

void AFPSIceWall::Gather(float Fraction,const FVector& Origin)
{
    if(State!=EState::Seed)return;
    const float Progress=FMath::Clamp(Fraction,0.f,1.f);
    const float Scale=FMath::Lerp(.12f,1.f,Progress);
    const float Condensation=FMath::Clamp((Progress-.20f)/.65f,0.f,1.f);
    const float Core=Condensation*Condensation*(3.f-2.f*Condensation);
    SetActorLocation(Origin);
    SetActorScale3D(FVector(Scale));
    // The frost reaches cube faces before a solid ice core becomes visible.
    for(const auto& Mesh:Blocks)
    {
        Mesh->SetVisibility(Core>.001f);
        Mesh->SetRelativeScale3D(FVector(FMath::Max(.001f,Core)/Scale));
    }
    SetActorRotation(FRotator(2*FMath::Sin(GetWorld()->GetTimeSeconds()*.8f),GetWorld()->GetTimeSeconds()*4.f,0));
}

void AFPSIceWall::BuildLayout(EIceWallShape Shape)
{
    if(Blocks.IsEmpty())return;
    TArray<FIceWallSection> Sections=Plan.Sections;
    if(Sections.IsEmpty())
    {
        FIceWallSection S;S.MinAlong=-Tuning.Width()*.5f;S.MaxAlong=Tuning.Width()*.5f;S.Top=Tuning.Height(Shape);
        Sections.Add(S); // Invalid previews still have a visible red silhouette.
    }
    uint32 Hash=GetTypeHash(int32(Shape));
    for(const auto& S:Sections)
        for(float Value:{S.MinAlong,S.MaxAlong,S.Bottom,S.Top})Hash=HashCombine(Hash,GetTypeHash(Value));
    if(LayoutShape==int32(Hash))return;
    LayoutShape=int32(Hash);for(const auto& Mesh:Blocks)Mesh->ClearInstances();
    FRandomStream Random(93030); // Preview and final wall share the same fractured slab layout.
    for(int32 Column=0;Column<Sections.Num();++Column)
    {
        const auto& S=Sections[Column];const float Span=S.MaxAlong-S.MinAlong,Height=S.Top-S.Bottom;
        const int32 Pieces=Shape==EIceWallShape::Low?(Column%3==1?1:2):Random.RandRange(2,4);
        TArray<float> HeightWeights;
        float TotalHeightWeight=0;
        for(int32 Piece=0;Piece<Pieces;++Piece)
        {
            const float Weight=Random.FRandRange(.65f,1.35f);
            HeightWeights.Add(Weight);TotalHeightWeight+=Weight;
        }
        float Bottom=S.Bottom;
        for(int32 Piece=0;Piece<Pieces;++Piece)
        {
            const float PieceHeight=Height*HeightWeights[Piece]/TotalHeightWeight;
            const float Depth=Tuning.Thickness+Random.FRandRange(0,2.2f);
            const bool bTopLow=Shape==EIceWallShape::Low&&Piece==Pieces-1;
            const float DepthStagger=bTopLow?0.f:Random.FRandRange(-1.6f,1.6f);
            const FVector Center(DepthStagger,S.Center(),Bottom+PieceHeight*.5f);
            // Organic glacial slab orientation: alternate 180-deg face flips + subtle angular variation
            // while keeping Low-wall top slabs level for machine-gun bipod seating and tight interlocking seams.
            const float YawFlip=(Random.RandRange(0,1)?180.f:0.f)+Random.FRandRange(-1.8f,1.8f);
            const float TiltPitch=bTopLow?0.f:Random.FRandRange(-1.2f,1.2f);
            const float TiltRoll=bTopLow?0.f:Random.FRandRange(-1.1f,1.1f);
            const FQuat SlabRot=FRotator(TiltPitch,YawFlip,TiltRoll).Quaternion();
            // Upright, stepped columns sink into the sampled patch instead of
            // floating over its lower edge. Low cover follows local ground height.
            Blocks[Random.RandRange(0,Blocks.Num()-1)]->AddInstance(FTransform(SlabRot,Center,FVector((Depth+1.4f)/100,(Span+3.4f)/100,(PieceHeight+1.2f)/100)));
            Bottom+=PieceHeight;
        }
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
    Plan=Placement;ReleaseOrigin=Origin;Age=0;State=EState::Rising;
    SetActorScale3D(FVector::OneVector);SetActorLocation(Origin);
    if(HasAuthority())
    {
        NetPlan=Plan;NetTuning=Tuning;NetComponent=Component.Get();NetReleaseOrigin=Origin;
        NetState=uint8(EState::Rising);NetStateAge=0;NetStateAt=GetWorld()->GetTimeSeconds();
    }
}

void AFPSIceWall::BeginDrop()
{
    FString Reason;
    if(!Component.IsValid()||!Component->ValidatePlacement(Plan,Tuning,Reason))
    { if(HasAuthority())NetState=uint8(EState::Shattered); Shatter(); return; }
    // The seed disappears at the staff. Re-form a full wall directly above the
    // locked placement; no seed or wall traverses the horizontal aim path.
    State=EState::Falling;Age=0;LayoutShape=-1;BuildLayout(Plan.Shape);
    DropHeight=Tuning.DropHeight;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallDrop),false,this);
    Query.AddIgnoredActor(GetInstigator());
    for(const auto& S:Plan.Sections)
    {
        const float Bottom=S.MaxGround+4,HalfHeight=(S.Top-Bottom)*.5f;
        const FVector Center=Plan.Location+Plan.Rotation.RotateVector(FVector(0,S.Center(),Bottom+HalfHeight));
        TArray<FHitResult> Hits;
        RangedAttackQuery::SweepObjects(GetWorld(),GetInstigator(),Hits,Center,Center+FVector(0,0,DropHeight),Plan.Rotation.Quaternion(),
            FCollisionObjectQueryParams::AllObjects,FCollisionShape::MakeBox(
                FVector(Tuning.Thickness*.5f,(S.MaxAlong-S.MinAlong)*.5f,FMath::Max(1.f,HalfHeight))),Query);
        for(const auto& Hit:Hits)
        {
            const auto* Primitive=Hit.GetComponent();const auto* Actor=Hit.GetActor();
            if(!Primitive||Primitive->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)continue;
            if(Actor&&Actor->FindComponentByClass<UMonsterCombatComponent>())continue;
            DropHeight=FMath::Min(DropHeight,FMath::Max(0.f,float(Hit.Distance)-4.f));
        }
    }
    SetActorLocationAndRotation(Plan.Location+FVector(0,0,DropHeight),Plan.Rotation);
    SetActorScale3D(FVector::OneVector);
    for(const auto& Mesh:Blocks)Mesh->SetRelativeScale3D(FVector::OneVector);
    // Clear the seed's particles before relocating this world-space system.
    // Otherwise its previous-position input would draw a trail across the map.
    if(ColdMist)ColdMist->DeactivateImmediate();
    PreviousMistPosition=GetActorLocation();UpdateColdMist(0);
    if(ColdMist)IceWallPlacement::SetEffectProfile(ColdMist,Plan);
    if(ColdMist)ColdMist->Activate(true);
    if(HasAuthority()){NetState=uint8(EState::Falling);NetStateAge=Age;NetStateAt=GetWorld()->GetTimeSeconds();NetDropHeight=DropHeight;}
}

void AFPSIceWall::Land()
{
    SetActorLocationAndRotation(Plan.Location,Plan.Rotation);
    FString Reason;
    if(!Component.IsValid()||!Component->ValidatePlacement(Plan,Tuning,Reason)){Shatter();return;}
    auto* Shooter=GetInstigator();
    auto* M=ColdSteelAuthority::ForPawn(Shooter);
    if(!M||!Shooter){Destroy();return;}
    TSet<AActor*> Impacted;
    M->ApplyIceWallSpawn(Shooter,Plan,Tuning,&Impacted);
    ExtrudeMonsters();
    M->ApplyIceWallChill(Shooter,Plan,Tuning,&Impacted);
    EmitLandingFX();
    ShakeNearbyPlayers();
    EnableTerrainBarriers();
    Health=MaxHealth;SetCanBeDamaged(true);
    State=EState::Solid;Age=0;AuraAge=0;bSettledTickRate=false;SetActorTickInterval(0.f);
    ActivateSolidVisuals();
    if(HasAuthority()){NetState=uint8(EState::Solid);NetStateAge=0;NetStateAt=GetWorld()->GetTimeSeconds();NetHealth=Health;}
}

void AFPSIceWall::EmitLandingFX()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* System=Component.IsValid()?Component->LandingSystem():nullptr;
    if(!System)return;
    auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,System,Plan.Location+FVector(0,0,4),
        Plan.Rotation,FVector::OneVector,true,false,ENCPoolMethod::AutoRelease);
    if(!FX)return;
    const int32 DustCount=FMath::Clamp(FMath::CeilToInt(Plan.Width()/32.f),12,48);
    const int32 MistCount=FMath::Clamp(FMath::CeilToInt(Plan.Width()/48.f),8,28);
    FX->SetVariableVec3(TEXT("User.WallSize"),FVector(Tuning.Thickness,Plan.Width(),Tuning.Height(Plan.Shape)));
    IceWallPlacement::SetEffectProfile(FX,Plan);
    FX->SetVariableFloat(TEXT("User.DustCount"),DustCount);
    FX->SetVariableFloat(TEXT("User.MistCount"),MistCount);
    FX->SetVariableFloat(TEXT("User.DetailReduction"),0);
    FX->SetVariableVec3(TEXT("User.Wind"),FVector::ZeroVector);
    const float AlongRadius=FMath::Max(FMath::Abs(Plan.MinAlong()),FMath::Abs(Plan.MaxAlong()))+190;
    float CrossSlope=0;for(const auto& S:Plan.Sections)CrossSlope=FMath::Max(CrossSlope,FMath::Abs(S.SlopeAcross));
    const float VerticalMargin=240+460*CrossSlope;
    FX->SetSystemFixedBounds(FBox(FVector(-460,-AlongRadius,Plan.GroundMin()-VerticalMargin),FVector(460,AlongRadius,Plan.GroundMax()+VerticalMargin)));
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->ConfigureSmoke(FX,DustCount+MistCount);
    FX->Activate(true);
    if(BreakSound)UGameplayStatics::PlaySoundAtLocation(this,BreakSound,Plan.Location,1.f,.88f);
}

void AFPSIceWall::EnableTerrainBarriers()
{
    for(int32 I=0;I<Plan.Sections.Num();++I)
    {
        auto* Box=I==0?Barrier.Get():NewObject<UBoxComponent>(this);
        if(I>0)
        {
            AddInstanceComponent(Box);Box->SetupAttachment(Scene);
            Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);Box->SetCanEverAffectNavigation(false);
            Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Block);
            Box->SetGenerateOverlapEvents(false);Box->CanCharacterStepUpOn=ECB_No;
            Box->RegisterComponent();TerrainBarriers.Add(Box);
        }
        const auto& S=Plan.Sections[I];
        Box->SetBoxExtent(FVector(Tuning.Thickness*.5f,(S.MaxAlong-S.MinAlong)*.5f+.4f,(S.Top-S.Bottom)*.5f));
        Box->SetRelativeLocation(FVector(0,S.Center(),(S.Bottom+S.Top)*.5f));
        Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->SetCanEverAffectNavigation(true);
    }
}

void AFPSIceWall::ExtrudeMonsters()
{
    const auto Occupants=IceWallPlacement::Monsters(GetWorld(),Plan,Tuning);
    auto Ordered=Occupants.Array();
    Ordered.Sort([](const AActor& A,const AActor& B){return A.GetName()<B.GetName();});
    TArray<FVector4> Reserved;
    for(auto* Target:Ordered)
    {
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if((!Combat||Combat->IsDead())&&!UnknownSpell::IsTarget(GetInstigator(),Target))continue;
        if(IceWallPlacement::Displace(GetWorld(),Target,this,Plan,Tuning,Occupants,Reserved))continue;
        // A trapped monster cannot veto the slam. Keep only this actor's movement
        // clear of this wall until it finds an exit; all other wall collision stays active.
        if(auto* Root=Cast<UPrimitiveComponent>(Target->GetRootComponent()))
        {
            Root->IgnoreActorWhenMoving(this,true);PendingMonsters.Add(Target);
        }
    }
}

void AFPSIceWall::RetryExtrusion()
{
    if(PendingMonsters.IsEmpty())return;
    ExtrusionCursor%=PendingMonsters.Num();
    auto* Target=PendingMonsters[ExtrusionCursor].Get();
    const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    bool Clear=!Target||((!Combat||Combat->IsDead())&&!UnknownSpell::IsTarget(GetInstigator(),Target))||!IceWallPlacement::Occupies(Target,Plan,Tuning);
    if(!Clear)
    {
        const auto Occupants=IceWallPlacement::Monsters(GetWorld(),Plan,Tuning);
        TArray<FVector4> Reserved;
        Clear=IceWallPlacement::Displace(GetWorld(),Target,this,Plan,Tuning,Occupants,Reserved);
    }
    if(Clear)
    {
        if(Target)if(auto* Root=Cast<UPrimitiveComponent>(Target->GetRootComponent()))Root->IgnoreActorWhenMoving(this,false);
        PendingMonsters.RemoveAt(ExtrusionCursor);
    }
    else ++ExtrusionCursor;
}

void AFPSIceWall::RestoreMonsterIgnores()
{
    for(auto& Weak:PendingMonsters)if(auto* Target=Weak.Get())
        if(auto* Root=Cast<UPrimitiveComponent>(Target->GetRootComponent()))Root->IgnoreActorWhenMoving(this,false);
    PendingMonsters.Reset();
}

void AFPSIceWall::ShakeNearbyPlayers()
{
    const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
    const float UserScale=Setting?FMath::Max(0.f,Setting->GetFloat()):1.f;
    if(UserScale<=0)return;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();APawn* Pawn=PC?PC->GetPawn():nullptr;
        if(!PC||!PC->IsLocalController()||!PC->PlayerCameraManager||!Pawn)continue;
        FVector Feet=Pawn->GetActorLocation();
        if(const auto* Character=Cast<ACharacter>(Pawn))
            Feet=Character->GetCapsuleComponent()->GetComponentLocation()-FVector(0,0,Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const FVector Local=Plan.Rotation.UnrotateVector(Feet-Plan.Location);
        const float X=FMath::Clamp(float(Local.X),-Tuning.Thickness*.5f,Tuning.Thickness*.5f);
        const float Y=FMath::Clamp(float(Local.Y),Plan.MinAlong(),Plan.MaxAlong());
        const FVector Closest(X,Y,IceWallPlacement::GroundAt(Plan,X,Y));
        // Measure to the nearest wall edge, so a wide high-level wall shakes a
        // player near either end just as it does one near the center.
        const float Distance=float((Local-Closest).Size());
        const float Attenuation=FMath::Square(1.f-FMath::Clamp((Distance-100.f)/550.f,0.f,1.f));
        const float Strength=Attenuation*UserScale*(Plan.Shape==EIceWallShape::Low?.80f:1.15f);
        if(Strength>0)PC->PlayerCameraManager->StartCameraShake(UIceWallLandingCameraShake::StaticClass(),Strength);
    }
}

void AFPSIceWall::UpdateDrop()
{
    const float T=FMath::Clamp(Age/Tuning.DropSeconds,0.f,1.f);
    SetActorLocation(Plan.Location+FVector(0,0,DropHeight*(1-(.2f*T+.8f*T*T))));
    if(T>=1)Land();
}

bool AFPSIceWall::IsSolid() const { return State==EState::Solid; }

void AFPSIceWall::UpdateColdMist(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer||State==EState::Preview||State==EState::Shattered||IsActorBeingDestroyed())return;
    const bool bNewMist=!ColdMist;
    if(bNewMist)
    {
        auto* Asset=Component.IsValid()?Component->ColdMistSystem():nullptr;
        if(!Asset)return; // The async preload may finish after gathering has started.
        ColdMist=NewObject<UNiagaraComponent>(this);AddInstanceComponent(ColdMist);
        ColdMist->SetupAttachment(Scene);ColdMist->SetAbsolute(false,true,true);
        ColdMist->SetAsset(Asset);ColdMist->SetAutoActivate(false);ColdMist->SetCastShadow(false);
        ColdMist->SetCanEverAffectNavigation(false);ColdMist->RegisterComponent();
        ColdMist->AddTickPrerequisiteActor(this);
        PreviousMistPosition=GetActorLocation();
    }
    const bool bWall=State==EState::Falling||State==EState::Solid;
    // Keep low-wall vapour below the bipod and sight line; preserve particle size
    // as levels widen the emission region instead of scaling a single smoke jet.
    const FVector MistSize(Tuning.Thickness,bWall?Plan.Width():Tuning.Width(),
        Tuning.Height(Plan.Shape)*(Plan.Shape==EIceWallShape::Low?.5f:.8f));
    const FVector Position=GetActorLocation();
    const FRotationMatrix MistBasis(State==EState::Rising?FVector::UpVector.Rotation():GetActorRotation());
    const bool bGather=State==EState::Seed;
    const float GatherProgress=bGather?FMath::Clamp((float(GetActorScale3D().X)-.12f)/.88f,0.f,1.f):1.f;
    const float Strength=bWall?(State==EState::Falling?.4f:1.f):(bGather?1.f:.65f*FMath::Clamp(float(GetActorScale3D().X),0.f,1.f));
    const float Rate=bWall?FMath::Clamp(float(MistSize.Y)*.065f,20.f,72.f):
        (bGather?(GatherProgress>=.98f?14.f:76.f)+22.f*GatherProgress:83.f);
    ColdMist->SetWorldLocation(Position);
    ColdMist->SetVariablePosition(TEXT("User.PreviousPosition"),PreviousMistPosition);
    ColdMist->SetVariablePosition(TEXT("User.CurrentPosition"),Position);
    ColdMist->SetVariableVec3(TEXT("User.FlightDirection"),MistBasis.GetUnitAxis(EAxis::X));
    ColdMist->SetVariableVec3(TEXT("User.Side"),MistBasis.GetUnitAxis(EAxis::Y));
    ColdMist->SetVariableVec3(TEXT("User.Up"),bWall?FVector::UpVector:MistBasis.GetUnitAxis(EAxis::Z));
    ColdMist->SetVariableVec3(TEXT("User.WallSize"),MistSize);
    ColdMist->SetVariableFloat(TEXT("User.WallPhase"),bWall?1.f:0.f);
    ColdMist->SetVariableFloat(TEXT("User.GatherPhase"),bGather?1.f:0.f);
    ColdMist->SetVariableFloat(TEXT("User.GatherProgress"),GatherProgress);
    ColdMist->SetVariableFloat(TEXT("User.Flight"),State==EState::Rising?1.f:0.f);
    ColdMist->SetVariableFloat(TEXT("User.Strength"),Strength);
    // World-space particles retain their position as the seed moves. These
    // symmetric component-space bounds cover either wall yaw and its thin drift.
    const float Radius=bWall?FMath::Max(FMath::Abs(Plan.MinAlong()),FMath::Abs(Plan.MaxAlong()))+160.f:
        (State==EState::Rising?Tuning.RiseHeight+160.f:160.f);
    ColdMist->SetSystemFixedBounds(bWall?
        FBox(FVector(-Radius,-Radius,Plan.Bottom()-160.f),FVector(Radius,Radius,Plan.Top()+100.f)):
        FBox(FVector(-Radius),FVector(Radius)));
    MistEnvironmentAge+=Delta;
    if(MistEnvironmentAge>=.2f)
    {
        MistEnvironmentAge=0;
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        {
            const int32 Wanted=FMath::Max(1,FMath::CeilToInt(Rate*Strength*.2f));
            const int32 Granted=Fluid->AllocateDetail(Position,Wanted,false);
            ColdMist->SetVariableFloat(TEXT("User.DetailReduction"),1.f-float(Granted)/Wanted);
            // Sample outside the wall's blocking box so its own ice is not a roof.
            const FVector WindPosition=bWall?
                Position+GetActorForwardVector()*(Tuning.Thickness*.5f+20.f)+FVector(0,0,18):Position;
            ColdMist->SetVariableVec3(TEXT("User.Wind"),Fluid->WindAt(WindPosition)*.25f);
        }
    }
    PreviousMistPosition=Position;
    if(bNewMist){if(bWall)IceWallPlacement::SetEffectProfile(ColdMist,Plan);ColdMist->Activate(true);}
}

void AFPSIceWall::ActivateSolidVisuals()
{
    if(bSolidVisualsActive||GetNetMode()==NM_DedicatedServer)return;
    bSolidVisualsActive=true;
    const float MidAlong=(Plan.MinAlong()+Plan.MaxAlong())*.5f;
    const float MidGroundZ=IceWallPlacement::GroundAt(Plan,0.f,MidAlong);
    const FVector WallFwd=Plan.Rotation.Vector();
    const FVector WallRight=Plan.Rotation.RotateVector(FVector::RightVector);

    // 1) Dynamic glacial shader parameters: ground-contact rime height + bottom-up freeze wave.
    if(WallMaterial)
    {
        WallMaterial->SetScalarParameterValue(TEXT("BaseFrostZ"),float(Plan.Location.Z)+Plan.GroundMin());
        WallMaterial->SetScalarParameterValue(TEXT("FreezeProgress"),Age>=.45f?1.f:0.f);
        WallMaterial->SetScalarParameterValue(TEXT("DamageCrack"),FMath::Clamp(1.f-Health/FMath::Max(1.f,MaxHealth),0.f,1.f));
    }

    // 2) Continuous terrain-conforming frozen ground collar (reusing M_FrostSurfaceSheet — immune to decal truncation).
    UMaterialInterface* SheetMat=Component.IsValid()?Component->FrostSheetMaterialAsset():nullptr;
    if(!SheetMat)SheetMat=LoadObject<UMaterialInterface>(nullptr,FrostSurfaceMesh::SheetMaterialPath);
    if(SheetMat)
    {
        const FVector FrostCenter=Plan.Location+WallRight*MidAlong+FVector(0,0,MidGroundZ);
        const float RadiusX=Tuning.Thickness*.5f+205.f;
        const float RadiusY=Plan.Width()*.5f+165.f;
        FrostSurface=FrostSurfaceMesh::BuildConformingDisc(this,Scene,GetInstigator(),FrostCenter,WallFwd,
            RadiusX,RadiusY,SheetMat,FrostSurfaceMID,36,7,true,3.6f);
        if(FrostSurfaceMID)
        {
            const float InitReveal=Age>=.45f?1.15f:.14f;
            FrostSurfaceMID->SetScalarParameterValue(TEXT("RevealRadius"),InitReveal);
            FrostSurfaceMID->SetScalarParameterValue(TEXT("FrostDensity"),.86f);
            FrostSurfaceMID->SetScalarParameterValue(TEXT("EmissiveBoost"),Age>=.65f?.08f:.95f);
            FrostSurfaceMID->SetScalarParameterValue(TEXT("Fade"),1.f);
        }
    }

    // 3) Drifting crystalline frost sparkles along the wall (feathered NS_FrostCrystalsV2 using M_AbsoluteZeroIceDust).
    UNiagaraSystem* CrystalSys=Component.IsValid()?Component->FrostCrystalsSystem():nullptr;
    if(!CrystalSys)CrystalSys=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystalsV2.NS_FrostCrystalsV2"));
    if(CrystalSys)
    {
        FrostCrystals=NewObject<UNiagaraComponent>(this);AddInstanceComponent(FrostCrystals);
        FrostCrystals->SetupAttachment(Scene);FrostCrystals->SetAbsolute(false,true,true);
        FrostCrystals->SetAsset(CrystalSys);FrostCrystals->SetAutoActivate(false);
        FrostCrystals->SetCastShadow(false);FrostCrystals->SetCanEverAffectNavigation(false);
        FrostCrystals->RegisterComponent();
        const float SweepZ=MidGroundZ+Tuning.Height(Plan.Shape)*(Plan.Shape==EIceWallShape::Low?.35f:.55f);
        const FVector StartPt=Plan.Location+WallRight*MidAlong+FVector(0,0,SweepZ);
        FrostCrystals->SetWorldLocation(StartPt);
        FrostCrystals->SetVariablePosition(TEXT("User.PreviousPosition"),StartPt);
        FrostCrystals->SetVariablePosition(TEXT("User.CurrentPosition"),StartPt);
        FrostCrystals->SetVariableVec3(TEXT("User.FlightDirection"),WallFwd);
        FrostCrystals->SetVariableVec3(TEXT("User.Side"),WallRight);
        FrostCrystals->SetVariableVec3(TEXT("User.Up"),FVector::UpVector);
        FrostCrystals->SetVariableFloat(TEXT("User.Flight"),.35f);
        FrostCrystals->SetVariableFloat(TEXT("User.Strength"),1.f);
        const float R=FMath::Max(FMath::Abs(Plan.MinAlong()),FMath::Abs(Plan.MaxAlong()))+160.f;
        FrostCrystals->SetSystemFixedBounds(FBox(FVector(-R,-R,Plan.Bottom()-120.f),FVector(R,R,Plan.Top()+120.f)));
        FrostCrystals->Activate(true);
    }

    // 5) Subtle shadow-free glacial rim glow so carved ice facets read clearly in shadow and night.
    WallLight=NewObject<UPointLightComponent>(this);AddInstanceComponent(WallLight);
    WallLight->SetupAttachment(Scene);
    WallLight->SetRelativeLocation(FVector(0.f,MidAlong,MidGroundZ+Tuning.Height(Plan.Shape)*.45f));
    WallLight->SetLightColor(FLinearColor(.34f,.78f,1.f));
    WallLight->SetIntensity(Age>=.55f?1500.f:5800.f);
    WallLight->SetAttenuationRadius(FMath::Clamp(Plan.Width()*.85f,360.f,750.f));
    WallLight->SetCastShadows(false);
    WallLight->RegisterComponent();
}

void AFPSIceWall::UpdateSolidVisuals(float Delta)
{
    if(!bSolidVisualsActive||GetNetMode()==NM_DedicatedServer)return;
    const float FreezeAlpha=FMath::Clamp(Age/.45f,0.f,1.f);
    const float DamageAlpha=FMath::Clamp(1.f-Health/FMath::Max(1.f,MaxHealth),0.f,1.f);
    const float EndFade=Tuning.Duration>1.4f&&Age>Tuning.Duration-1.2f?FMath::Clamp((Tuning.Duration-Age)/1.2f,0.f,1.f):1.f;

    if(WallMaterial)
    {
        WallMaterial->SetScalarParameterValue(TEXT("FreezeProgress"),FreezeAlpha);
        WallMaterial->SetScalarParameterValue(TEXT("DamageCrack"),DamageAlpha);
    }
    if(FrostSurface&&FrostSurfaceMID)
    {
        const float Reveal=FMath::Lerp(.14f,1.15f,FMath::InterpEaseOut(0.f,1.f,FreezeAlpha,2.2f));
        const float Emissive=FMath::Lerp(.95f,.08f,FMath::Clamp(Age/.65f,0.f,1.f));
        FrostSurfaceMID->SetScalarParameterValue(TEXT("RevealRadius"),Reveal);
        FrostSurfaceMID->SetScalarParameterValue(TEXT("EmissiveBoost"),Emissive);
        FrostSurfaceMID->SetScalarParameterValue(TEXT("Fade"),EndFade);
        FrostSurface->SetVisibility(EndFade>.01f);
    }
    if(FrostCrystals)
    {
        const FVector WallFwd=Plan.Rotation.Vector();
        const FVector WallRight=Plan.Rotation.RotateVector(FVector::RightVector);
        const float PrevPhase=CrystalSweepPhase;
        CrystalSweepPhase+=Delta*1.9f;
        const auto SampleAt=[&](float Phase)
        {
            const float U=.5f+.46f*FMath::Sin(Phase);
            const float Along=FMath::Lerp(Plan.MinAlong(),Plan.MaxAlong(),U);
            const float Side=((FMath::FloorToInt(Phase/PI)&1)==0?1.f:-1.f)*(Tuning.Thickness*.5f+14.f);
            const float ZFrac=Plan.Shape==EIceWallShape::Low?(.22f+.18f*FMath::Abs(FMath::Cos(Phase*1.7f))):(.25f+.55f*FMath::Abs(FMath::Cos(Phase*1.7f)));
            const float Z=IceWallPlacement::GroundAt(Plan,Side,Along)+Tuning.Height(Plan.Shape)*ZFrac;
            return Plan.Location+WallFwd*Side+WallRight*Along+FVector(0,0,Z);
        };
        const FVector PrevPt=SampleAt(PrevPhase);
        const FVector CurrPt=SampleAt(CrystalSweepPhase);
        FrostCrystals->SetWorldLocation(CurrPt);
        FrostCrystals->SetVariablePosition(TEXT("User.PreviousPosition"),PrevPt);
        FrostCrystals->SetVariablePosition(TEXT("User.CurrentPosition"),CurrPt);
        FrostCrystals->SetVariableFloat(TEXT("User.Strength"),EndFade);
    }
    if(WallLight)
    {
        const float FlashT=FMath::Clamp(Age/.55f,0.f,1.f);
        WallLight->SetIntensity(FMath::Lerp(5800.f,1500.f,FlashT*FlashT)*EndFade);
    }
    if(Age>=.68f&&!bSettledTickRate)
    {
        bSettledTickRate=true;
        SetActorTickInterval(.1f);
    }
}

void AFPSIceWall::ClearSolidVisuals()
{
    bSolidVisualsActive=false;
    if(FrostSurface){FrostSurface->DestroyComponent();FrostSurface=nullptr;FrostSurfaceMID=nullptr;}
    if(FrostCrystals){FrostCrystals->DestroyComponent();FrostCrystals=nullptr;}
    if(WallLight){WallLight->DestroyComponent();WallLight=nullptr;}
}

float AFPSIceWall::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||!IsSolid()||!CanBeDamaged()||Damage<=0||!FMath::IsFinite(Damage))return 0;
    const float Applied=FMath::Min(Health,Damage);
    Health-=Applied;NetHealth=Health;ForceNetUpdate();
    if(WallMaterial)WallMaterial->SetScalarParameterValue(TEXT("DamageCrack"),FMath::Clamp(1.f-Health/FMath::Max(1.f,MaxHealth),0.f,1.f));
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if(Health<=0)Shatter();
    return Applied;
}

void AFPSIceWall::Tick(float Delta)
{
    Super::Tick(Delta);
    // 远端副本：状态/变换来自复制，本地只重演起落表现与冷气。
    if(!HasAuthority()){NetTick(Delta);return;}
    Age+=Delta;
    if(State==EState::Rising)
    {
        const float T=FMath::Clamp(Age/Tuning.RiseSeconds,0.f,1.f);
        SetActorLocation(ReleaseOrigin+FVector(0,0,Tuning.RiseHeight*(.3f*T+.7f*T*T)));
        SetActorScale3D(FVector(FMath::Max(.001f,(1-T)*(1-T))));
        if(T>=1)
        {
            const float Remaining=FMath::Max(0.f,Age-Tuning.RiseSeconds);
            BeginDrop();
            if(State==EState::Falling){Age=Remaining;UpdateDrop();}
        }
    }
    else if(State==EState::Falling)
    {
        UpdateDrop();
    }
    else if(State==EState::Solid)
    {
        if(Age>=Tuning.Duration){Shatter();return;}
        ExtrusionAge+=Delta;
        if(!PendingMonsters.IsEmpty()&&ExtrusionAge>=.25f){ExtrusionAge=0;RetryExtrusion();}
        AuraAge+=Delta;
        if(AuraAge>=Tuning.ChillInterval)
        {
            AuraAge=FMath::Fmod(AuraAge,Tuning.ChillInterval);
            if(auto* M=ColdSteelAuthority::ForPawn(GetInstigator()))M->ApplyIceWallChill(GetInstigator(),Plan,Tuning);
        }
        UpdateSolidVisuals(Delta);
    }
    UpdateColdMist(Delta);
}

void AFPSIceWall::Shatter()
{
    if(State==EState::Shattered||IsActorBeingDestroyed())return;
    const EState Previous=State;State=EState::Shattered;
    SetCanBeDamaged(false);SetActorTickEnabled(false);
    Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);Barrier->SetCanEverAffectNavigation(false);
    for(const auto& Box:TerrainBarriers){Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);Box->SetCanEverAffectNavigation(false);}
    ClearSolidVisuals();
    RestoreMonsterIgnores();
    if(GetNetMode()!=NM_DedicatedServer&&Previous!=EState::Preview)
    {
        if(BreakSound)UGameplayStatics::PlaySoundAtLocation(this,BreakSound,GetActorLocation(),.65f);
        if(BreakFX)
        {
            const int32 Bursts=(Previous==EState::Solid||Previous==EState::Falling)?FMath::Min(8,Tuning.Count):1;
            for(int32 I=0;I<Bursts;++I)
            {
                const float Along=FMath::Lerp(Plan.MinAlong(),Plan.MaxAlong(),(I+.5f)/Bursts);
                const FVector At=GetActorLocation()+GetActorRightVector()*Along+FVector(0,0,IceWallPlacement::GroundAt(Plan,0,Along)+35);
                UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),BreakFX,At,FRotator::ZeroRotator,FVector(1.4f));
            }
        }
    }
    // 联机：先播报碎裂态再延时销毁——远端 OnRep 有一帧窗口播同款碎裂 FX。
    if(GetWorld()&&GetWorld()->GetNetMode()!=NM_Standalone)
    {
        NetState=uint8(EState::Shattered);NetStateAge=0;NetStateAt=GetWorld()->GetTimeSeconds();
        for(const auto& Mesh:Blocks)Mesh->SetVisibility(false,true);
        SetLifeSpan(.5f);return;
    }
    Destroy();
}

// ══ 远端副本（非权威）：自载素材建布局，OnRep 状态重演 ═════════════════
void AFPSIceWall::NetInit()
{
    if(bNetInit||!NetPlan.bValid||NetTuning.Count<=0||!NetComponent||NetStateAt<0||!GetWorld()->GetGameState())return;
    // 素材自载——与组件 BeginPlay 同路径，远端副本不走 Initialize。
    for(int32 I=1;I<=4;++I)
    {
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_%02d.SM_IceBlock_%02d"),I,I));
        if(!Mesh)return;
        auto* Inst=NewObject<UInstancedStaticMeshComponent>(this);
        AddInstanceComponent(Inst);Inst->SetupAttachment(Scene);Inst->SetStaticMesh(Mesh);
        Inst->SetCollisionEnabled(ECollisionEnabled::NoCollision);Inst->SetCanEverAffectNavigation(false);
        Inst->SetCastShadow(true);Inst->bReceivesDecals=false;Inst->RegisterComponent();Blocks.Add(Inst);
    }
    if(auto* Ice=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceWall/FabIceV3/M_IceWall.M_IceWall")))
    {
        WallMaterial=UMaterialInstanceDynamic::Create(Ice,this);
        for(const auto& Inst:Blocks)Inst->SetMaterial(0,WallMaterial?static_cast<UMaterialInterface*>(WallMaterial.Get()):Ice);
    }
    BreakFX=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    BreakSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    Tuning=NetTuning;Plan=NetPlan;Component=NetComponent;ReleaseOrigin=NetReleaseOrigin;
    MaxHealth=FMath::Max(1.f,Tuning.MaxHealth);Health=NetHealth>0?NetHealth:MaxHealth;
    DropHeight=NetDropHeight>0?NetDropHeight:Tuning.DropHeight;
    LayoutShape=-1;BuildLayout(NetPlan.Shape);
    bNetInit=true;
    OnRep_State(); // 首包可能已带落地/碎裂态——按当前态对齐表现
}
void AFPSIceWall::OnRep_State()
{
    if(!bNetInit)return; // 初包先于 NetInit 到达时由 NetInit 尾调兜底重演
    const auto S=static_cast<EState>(NetState);
    if(S==State)return;
    const auto Was=State;State=S;Age=NetworkAge();
    if(S==EState::Falling)
    {
        State=Was; // 先恢复供 BuildLayout 读
        LayoutShape=-1;BuildLayout(Plan.Shape);State=EState::Falling;
        DropHeight=NetDropHeight>0?NetDropHeight:Tuning.DropHeight;
        SetActorLocationAndRotation(Plan.Location+FVector(0,0,DropHeight),Plan.Rotation);
        for(const auto& Mesh:Blocks)Mesh->SetRelativeScale3D(FVector::OneVector);
        if(ColdMist){ColdMist->DeactivateImmediate();IceWallPlacement::SetEffectProfile(ColdMist,Plan);ColdMist->Activate(true);}
        PreviousMistPosition=GetActorLocation();
    }
    else if(S==EState::Solid)NetLanded();
    else if(S==EState::Shattered)
    {
        ClearSolidVisuals();
        for(const auto& Mesh:Blocks)Mesh->SetVisibility(false,true);
        Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);Barrier->SetCanEverAffectNavigation(false);
        for(const auto& Box:TerrainBarriers){Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);Box->SetCanEverAffectNavigation(false);}
        if(Was!=EState::Seed&&Was!=EState::Preview&&Age<.75f)
        {
            if(BreakSound)UGameplayStatics::PlaySoundAtLocation(this,BreakSound,GetActorLocation(),.65f);
            if(BreakFX)
            {
                const int32 Bursts=(Was==EState::Solid||Was==EState::Falling)?FMath::Min(8,Tuning.Count):1;
                for(int32 I=0;I<Bursts;++I)
                {
                    const float Along=FMath::Lerp(Plan.MinAlong(),Plan.MaxAlong(),(I+.5f)/Bursts);
                    const FVector At=GetActorLocation()+GetActorRightVector()*Along+FVector(0,0,IceWallPlacement::GroundAt(Plan,0,Along)+35);
                    UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),BreakFX,At,FRotator::ZeroRotator,FVector(1.4f));
                }
            }
        }
    }
}
void AFPSIceWall::OnRep_Health()
{
    Health=NetHealth;
    if(WallMaterial)WallMaterial->SetScalarParameterValue(TEXT("DamageCrack"),FMath::Clamp(1.f-Health/FMath::Max(1.f,MaxHealth),0.f,1.f));
}

void AFPSIceWall::NetLanded()
{
    SetActorLocationAndRotation(Plan.Location,Plan.Rotation);
    // Opening an old wall's channel must not replay its impact or camera shake.
    if(Age<.75f){EmitLandingFX();ShakeNearbyPlayers();}
    EnableTerrainBarriers();
    Health=NetHealth>0?NetHealth:MaxHealth;
    bSettledTickRate=Age>=.68f;
    SetActorTickInterval(bSettledTickRate?.1f:0.f);
    ActivateSolidVisuals();
    if(ColdMist){ColdMist->SetVariableFloat(TEXT("User.WallPhase"),1.f);}
    UpdateColdMist(0);
}
void AFPSIceWall::NetTick(float Delta)
{
    if(!bNetInit){NetInit();if(!bNetInit)return;}
    Age=FMath::Max(Age,NetworkAge());AuraAge+=Delta;
    // 升降位姿由 ReplicateMovement 搬运；这里只管冷气持续发射与到期兜底。
    if(State==EState::Solid)
    {
        if(Age>=Tuning.Duration+2.f){Destroy();return;} // 服务端销毁超时兜底
        UpdateSolidVisuals(Delta);
    }
    UpdateColdMist(Delta);
}
float AFPSIceWall::NetworkAge() const
{
    const auto* GS=GetWorld()->GetGameState();
    return NetStateAge+float(FMath::Max(0.,(GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds())-NetStateAt));
}
void AFPSIceWall::EndPlay(EEndPlayReason::Type Reason)
{
    ClearSolidVisuals();
    if(ColdMist){ColdMist->DestroyComponent();ColdMist=nullptr;}
    Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);Barrier->SetCanEverAffectNavigation(false);
    for(const auto& Box:TerrainBarriers){Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);Box->SetCanEverAffectNavigation(false);}
    RestoreMonsterIgnores();
    if(Component.IsValid())Component->WallEnded(this);
    Super::EndPlay(Reason);
}
