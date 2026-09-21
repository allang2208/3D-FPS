#include "WitchMonster.h"
#include "WitchSpellAnimInstance.h"
#include "WitchProjectile.h"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "AIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
#if WITH_EDITOR
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "HAL/IConsoleManager.h"
#include "UObject/UObjectIterator.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

static FAutoConsoleCommand WitchDumpRenderState(
    TEXT("fps.Witch.DumpRenderState"), TEXT("Report the Witch mesh/bone/cloth render state without spawning an actor."),
    FConsoleCommandDelegate::CreateLambda([]
    {
        FString Report;
        auto Log = [&Report](const FString& Line) { Report += Line + TEXT("\n"); UE_LOG(LogTemp, Display, TEXT("%s"), *Line); };
        USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy.SK_Witch_Meshy"));
        if (!Mesh) { UE_LOG(LogTemp, Warning, TEXT("WITCH_RENDER_STATE mesh missing")); return; }
        const auto Bounds = Mesh->GetImportedBounds();
        Log(FString::Printf(TEXT("WITCH_RENDER_STATE imported_origin=%s extent=%s bones=%d"),
            *Bounds.Origin.ToString(), *Bounds.BoxExtent.ToString(), Mesh->GetRefSkeleton().GetNum()));
        if (auto* Model = Mesh->GetImportedModel(); Model && Model->LODModels.Num())
        {
            for (int32 I = 0; I < Model->LODModels[0].Sections.Num(); ++I)
            {
                const auto& S = Model->LODModels[0].Sections[I];
                Log(FString::Printf(TEXT("WITCH_RENDER_SECTION %d slot=%d disabled=%d vertices=%d triangles=%d cloth=%d source=%d"),
                    I, S.MaterialIndex, S.bDisabled, S.NumVertices, S.NumTriangles, S.CorrespondClothAssetIndex, S.OriginalDataSectionIndex));
            }
        }
        const auto& Ref = Mesh->GetRefSkeleton();
        for (const FName Name : {FName("Hips"), FName("Head"), FName("LeftHand"), FName("LeftFoot")})
        {
            const int32 Index = Ref.FindBoneIndex(Name); if (Index == INDEX_NONE) continue;
            FTransform T = Ref.GetRefBonePose()[Index];
            for (int32 P = Ref.GetParentIndex(Index); P != INDEX_NONE; P = Ref.GetParentIndex(P)) T *= Ref.GetRefBonePose()[P];
            Log(FString::Printf(TEXT("WITCH_RENDER_BONE %s position=%s scale=%s"), *Name.ToString(), *T.GetLocation().ToString(), *T.GetScale3D().ToString()));
        }
        for (const auto& Asset : Mesh->GetMeshClothingAssets())
        {
            auto* Cloth = Cast<UClothingAssetCommon>(Asset); if (!Cloth || Cloth->LodData.IsEmpty()) continue;
            const auto& Data = Cloth->LodData[0].PhysicalMeshData;
            FBox Box(ForceInit); for (const auto& V : Data.Vertices) Box += FVector(V);
            Log(FString::Printf(TEXT("WITCH_RENDER_CLOTH %s vertices=%d fixed=%d reference_bone=%d bounds=%s collisions=%d"),
                *Cloth->GetName(), Data.Vertices.Num(), Data.NumFixedVerts, Cloth->ReferenceBoneIndex, *Box.ToString(),
                Cloth->PhysicsAsset ? Cloth->PhysicsAsset->SkeletalBodySetups.Num() : 0));
        }
        for (TObjectIterator<AWitchMonster> It; It; ++It)
        {
            if (It->IsTemplate() || !It->GetWorld() || !It->GetWorld()->IsGameWorld()) continue;
            auto* C = It->GetMesh();
            Log(FString::Printf(TEXT("WITCH_RENDER_ACTOR %s actor=%s mesh=%s scale=%s visible=%d bounds=%s extent=%s hips=%s head=%s"),
                *It->GetName(), *It->GetActorLocation().ToString(), *C->GetComponentLocation().ToString(), *C->GetComponentScale().ToString(),
                C->IsVisible(), *C->Bounds.Origin.ToString(), *C->Bounds.BoxExtent.ToString(), *C->GetBoneLocation("Hips").ToString(), *C->GetBoneLocation("Head").ToString()));
        }
        FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("WitchV06-native-render-state.txt")));
    }));
#endif

AWitchMonster::AWitchMonster(const FObjectInitializer& Initializer) : Super(Initializer)
{
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("Witch"));
    GetCapsuleComponent()->InitCapsuleSize(34.f, 94.f);
    // Health/magic/cooldowns come from the original witch config. World units
    // are authored centimetres, not an automatic conversion of source pixels.
    // V05 retains the donor's 3.2667 s stride and its 73.16 cm travel.
    MaxHealth = 1300.f; Health = MaxHealth; WalkSpeed = 22.3955f; AggroRadius = 1600.f;
    AttackRange = SpellRange; AttackDamage = 0.f; RecoveryTime = 0.f;
    // The inherited attack clock drives our overridden presentation hook.
    // Its melee contact branch is disabled: only ReleaseSpell deals attacks.
    ContactTime = 0.f; ContactEnd = -1.f; CorpseSeconds = 15.f;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy.SK_Witch_Meshy"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_Idle.A_Witch_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Walk(TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_Walk.A_Witch_Walk"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Cast(TEXT("/Game/Monsters/WitchMeshy/SpellSupportV07/A_Witch_CastPoison.A_Witch_CastPoison"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Throw(TEXT("/Game/Monsters/WitchMeshy/SpellSupportV07/A_Witch_ThrowPoisonBottle.A_Witch_ThrowPoisonBottle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Death(TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_DeathBackward.A_Witch_DeathBackward"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> StaffAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff.SM_Witch_Staff"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> BottleAsset(TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_PoisonBottle.SM_Witch_PoisonBottle"));
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    VisualMesh = Model.Object; IdleClip = Idle.Object; WalkClip = Walk.Object;
    CastClip = Cast.Object; ThrowClip = Throw.Object; DeathClip = Death.Object; AttackClip = CastClip;
    GetMesh()->bCollideWithEnvironment = true;
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    Staff = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WitchStaff"));
    Staff->SetupAttachment(GetMesh(), TEXT("LeftHand")); Staff->SetStaticMesh(StaffAsset.Object);
    Bottle = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WitchBottle"));
    Bottle->SetupAttachment(GetMesh(), TEXT("RightHand")); Bottle->SetStaticMesh(BottleAsset.Object);
    for (auto* Prop : {Staff.Get(), Bottle.Get()})
    {
        Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Prop->SetGenerateOverlapEvents(false); Prop->SetCanEverAffectNavigation(false);
    }
    AlignVisual();
}

void AWitchMonster::AlignVisual()
{
    // Navigation profiles within 5 cm are equivalent in UE. Keep explicit
    // clearance distinct from Nurse (184 cm), while retaining our 188 cm body.
    auto* Movement = GetCharacterMovement();
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = GetCapsuleComponent()->GetScaledCapsuleRadius();
    Agent.AgentHeight = FMath::Max(192.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * 2.f);
    Agent.AgentStepHeight = Movement->MaxStepHeight;
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto& Ref = VisualMesh->GetRefSkeleton();
    const int32 Head = Ref.FindBoneIndex(TEXT("Head")), Front = Ref.FindBoneIndex(TEXT("headfront"));
    auto Position = [&Ref](int32 Bone)
    {
        FTransform Transform = Ref.GetRefBonePose()[Bone];
        for (int32 Parent = Ref.GetParentIndex(Bone); Parent != INDEX_NONE; Parent = Ref.GetParentIndex(Parent))
            Transform = Transform * Ref.GetRefBonePose()[Parent];
        return Transform.GetLocation();
    };
    if (Head != INDEX_NONE && Front != INDEX_NONE)
    {
        const FVector Forward = (Position(Front) - Position(Head)).GetSafeNormal2D();
        GetMesh()->SetRelativeRotation(FRotator(0, -Forward.Rotation().Yaw, 0));
    }
    const auto Bounds = VisualMesh->GetBounds();
    // Alive clips place actual skinned soles at Z=0. The original ragged hem
    // and the hidden simulation cage must not set the ground reference.
    const bool bSoleGrounded = VisualMesh->GetPathName().Contains(TEXT("/LayeredV04/"))
        || VisualMesh->GetPathName().Contains(TEXT("/OriginalRobeV05/"));
    const float SoleZ = bSoleGrounded
        ? 0.f : Bounds.Origin.Z - Bounds.BoxExtent.Z;
    GetMesh()->SetRelativeLocation(FVector(0, 0,
        -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - SoleZ));
}

void AWitchMonster::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform); AlignVisual();
}

void AWitchMonster::BeginPlay()
{
    // Editor imports may complete after the native CDO was loaded. Resolve the
    // task's fixed assets again for newly spawned characters in that session.
    if (!VisualMesh) VisualMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy.SK_Witch_Meshy"));
    if (!IdleClip) IdleClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_Idle.A_Witch_Idle"));
    if (!WalkClip) WalkClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_Walk.A_Witch_Walk"));
    if (!CastClip) CastClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/WitchMeshy/SpellSupportV07/A_Witch_CastPoison.A_Witch_CastPoison"));
    if (!ThrowClip) ThrowClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/WitchMeshy/SpellSupportV07/A_Witch_ThrowPoisonBottle.A_Witch_ThrowPoisonBottle"));
    if (!DeathClip) DeathClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/WitchMeshy/OriginalRobeV05/Animations/A_Witch_DeathBackward.A_Witch_DeathBackward"));
    if (!Staff->GetStaticMesh()) Staff->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff.SM_Witch_Staff")));
    if (!Bottle->GetStaticMesh()) Bottle->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Monsters/WitchMeshy/Props/SM_Witch_PoisonBottle.SM_Witch_PoisonBottle")));
    AttackClip = CastClip; AlignVisual();
    Super::BeginPlay();
    // The initial idle pose provides the attachment frame. Preserve that offset
    // while the same hand bones subsequently raise the staff and throw.
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    AttachProps();
}

void AWitchMonster::AttachProps()
{
    auto Attach = [this](UStaticMeshComponent* Prop, FName Bone, float GripHeight)
    {
        Prop->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        Prop->SetWorldRotation(FRotator(0, GetActorRotation().Yaw, 0));
        Prop->SetWorldLocation(GetMesh()->GetSocketLocation(Bone) - FVector(0,0,GripHeight));
        Prop->AttachToComponent(GetMesh(), FAttachmentTransformRules::KeepWorldTransform, Bone);
    };
    // Match the authored closed palm, not the wrist joint origin. Reference
    // bone transforms keep this independent of FBX's scene-axis conversion.
    const auto& Ref = GetMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
    auto ReferenceTransform = [&Ref](FName Name)
    {
        const int32 Index = Ref.FindBoneIndex(Name);
        FTransform Transform = Ref.GetRefBonePose()[Index];
        for (int32 Parent = Ref.GetParentIndex(Index); Parent != INDEX_NONE; Parent = Ref.GetParentIndex(Parent))
            Transform = Transform * Ref.GetRefBonePose()[Parent];
        return Transform;
    };
    const FTransform RestHand = ReferenceTransform(TEXT("LeftHand"));
    const FVector AlongHand = (RestHand.GetLocation() - ReferenceTransform(TEXT("LeftForeArm")).GetLocation()).GetSafeNormal();
    const FVector Forward = (ReferenceTransform(TEXT("headfront")).GetLocation()
        - ReferenceTransform(TEXT("Head")).GetLocation()).GetSafeNormal();
    const FVector Palm = (Forward - AlongHand * FVector::DotProduct(Forward, AlongHand)).GetSafeNormal();
    const FVector RestGrip = RestHand.GetLocation() + AlongHand * 4.5f + Palm * 2.7f;
    FVector RestShaft = FVector::CrossProduct(Palm, AlongHand).GetSafeNormal();
    if (RestShaft.Z < 0.f) RestShaft *= -1.f;
    const FTransform HandWorld = GetMesh()->GetSocketTransform(TEXT("LeftHand"), RTS_World);
    const FVector GripWorld = HandWorld.TransformPosition(RestHand.InverseTransformPosition(RestGrip));
    const FVector ShaftWorld = HandWorld.TransformVectorNoScale(RestHand.InverseTransformVectorNoScale(RestShaft)).GetSafeNormal();
    const FQuat ShaftRotation = FRotationMatrix::MakeFromZ(ShaftWorld).ToQuat();
    Staff->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Staff->SetWorldRotation(ShaftRotation);
    // The revised staff mesh is centered on its actual shaft at the grip height.
    Staff->SetWorldLocation(GripWorld - ShaftRotation.RotateVector(FVector(0, 0, 92.f)));
    Staff->AttachToComponent(GetMesh(), FAttachmentTransformRules::KeepWorldTransform, TEXT("LeftHand"));
    Attach(Bottle, TEXT("RightHand"), 9.f);
}

bool AWitchMonster::CanCast(APawn* Candidate) const
{
    if (!IsValid(Candidate) || !CastClip || !ThrowClip || State == ENurseState::Dead
        || State == ENurseState::Stagger || State == ENurseState::Attack) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextMagicAt && Now < NextBottleAt) return false;
    if (FVector::Dist2D(GetActorLocation(), Candidate->GetActorLocation()) > SpellRange) return false;
    // Finish facing during approach/idle, before planting for the spell.
    const FVector Aim = (Candidate->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    if (FVector::DotProduct(GetActorForwardVector(), Aim) < .98f) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchSight), false, this);
    Query.AddIgnoredActor(Candidate);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation() + FVector(0,0,35),
        Candidate->GetActorLocation(), ECC_Visibility, Query);
}

void AWitchMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority() || (State != ENurseState::Idle && State != ENurseState::Chase)) return;
    const auto* AI = Cast<AAIController>(GetController());
    const auto* Board = AI ? AI->GetBlackboardComponent() : nullptr;
    auto* AimTarget = Board ? Cast<APawn>(Board->GetValueAsObject(TEXT("Target"))) : nullptr;
    if (!AimTarget || Board->GetValueAsBool(TEXT("Returning"))
        || FVector::DistSquared2D(GetActorLocation(), AimTarget->GetActorLocation()) > FMath::Square(SpellRange)) return;
    const FRotator Facing(0, (AimTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0);
    SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, DeltaSeconds, 110.f));
}

UWitchSpellAnimInstance* AWitchMonster::GetSpellAnimation()
{
    if (!Cast<UWitchSpellAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UWitchSpellAnimInstance::StaticClass());
    return Cast<UWitchSpellAnimInstance>(GetMesh()->GetAnimInstance());
}

void AWitchMonster::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (State == ENurseState::Attack)
    {
        const double Now = GetWorld()->GetTimeSeconds();
        bThrowing = Now < NextMagicAt && Now >= NextBottleAt;
        AttackClip = bThrowing ? ThrowClip : CastClip;
        Clip = AttackClip; bReleased = false;
        Bottle->SetVisibility(true);
        if (bThrowing) NextBottleAt = Now + BottleCooldown;
        else NextMagicAt = Now + MagicCooldown;
        if (const auto* AI = Cast<AAIController>(GetController()))
            if (const auto* Blackboard = AI->GetBlackboardComponent())
                SpellTarget = Cast<APawn>(Blackboard->GetValueAsObject(TEXT("Target")));
    }
    else if (Bottle) Bottle->SetVisibility(true);
    if (auto* Animation = GetSpellAnimation()) Animation->PlayState(Clip, bLoop);
}

void AWitchMonster::SetAttackAnimationTime(float Seconds)
{
    if (auto* Animation = GetSpellAnimation()) Animation->SetCombatTime(Seconds);
    const float Release = bThrowing ? .75f : 1.5f * 5.f / 14.f;
    if (!bReleased && State == ENurseState::Attack && Seconds >= Release)
    {
        bReleased = true; ReleaseSpell();
    }
}

void AWitchMonster::ReleaseSpell()
{
    if (!HasAuthority() || State != ENurseState::Attack || !SpellTarget.IsValid()) return;
    GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    const FVector Start = bThrowing ? Bottle->GetComponentTransform().TransformPosition(FVector(0,0,9))
        : Staff->GetComponentLocation() + Staff->GetUpVector() * 150.f;
    const FVector AimLocation = SpellTarget->GetActorLocation();
    Spells.RemoveAll([](const auto& Spell) { return !Spell.IsValid(); });
    for (int32 Index = 0; Index < (bThrowing ? 1 : 3); ++Index)
    {
        FActorSpawnParameters Params; Params.Owner = this; Params.Instigator = this;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Spell = GetWorld()->SpawnActor<AWitchProjectile>(Start, FRotator::ZeroRotator, Params);
        if (!Spell) continue;
        const FVector Prediction = AimLocation + SpellTarget->GetVelocity() * FMath::Min(.5f,
            FVector::Dist(Start, AimLocation) / FMath::Max(1.f, ProjectileSpeed));
        const FVector Aim = (Prediction - Start).GetSafeNormal().RotateAngleAxis((Index - 1) * 15.f, FVector::UpVector);
        Spell->Launch(this, bThrowing, bThrowing ? AimLocation : Start + Aim * 1000.f,
            ProjectileSpeed, MagicAttack * .75f, PoisonRadius);
        Spells.Add(Spell);
    }
    if (bThrowing) Bottle->SetVisibility(false);
}

void AWitchMonster::SetWalkAnimationRate(float)
{
    if (auto* Animation = GetSpellAnimation())
        Animation->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / FMath::Max(1.f, WalkSpeed), 0.f, 2.f));
}

void AWitchMonster::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    bReleased = true; SpellTarget.Reset(); Bottle->SetVisibility(true);
    // The native player freezes its current pose while the shared state is Stagger.
    if (Clip) if (auto* Animation = GetSpellAnimation()) Animation->PlayState(Clip, false);
}

void AWitchMonster::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    if (!Clip) return;
    const float Time = Elapsed < .15f ? Elapsed : Remaining > .4f ? .15f : Clip->GetPlayLength() - FMath::Max(0.f, Remaining);
    if (auto* Animation = GetSpellAnimation()) Animation->SetCombatTime(FMath::Clamp(Time, 0.f, Clip->GetPlayLength()));
}

void AWitchMonster::StartDeathPresentation()
{
    bReleased = true; SpellTarget.Reset();
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (DeathClip) { GetMesh()->PlayAnimation(DeathClip, false); GetMesh()->SetPlayRate(1.f); }
    const float Delay = DeathClip ? DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction : 0.f;
    if (Delay > 0) GetWorldTimerManager().SetTimer(RagdollTimer, this, &ThisClass::StartRagdoll, Delay, false);
    else StartRagdoll();
}

void AWitchMonster::StartRagdoll()
{
    if (State != ENurseState::Dead || !GetMesh()->GetPhysicsAsset()) return;
    if (DeathClip)
    {
        GetMesh()->SetPosition(DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction, false);
        GetMesh()->TickAnimation(0.f, false); GetMesh()->RefreshBoneTransforms();
    }
    GetMesh()->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
    GetMesh()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    GetMesh()->bPauseAnims = true;
    GetMesh()->SetAllBodiesSimulatePhysics(true); GetMesh()->SetSimulatePhysics(true);
    GetMesh()->WakeAllRigidBodies();
}

void AWitchMonster::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(RagdollTimer);
    for (const auto& Spell : Spells) if (Spell.IsValid()) Spell->Destroy();
    Spells.Reset(); Super::EndPlay(Reason);
}

bool AWitchMonster::PrepareCombatPhysics(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetPhysicsAsset() || !InMesh->GetPathName().StartsWith(TEXT("/Game/Monsters/WitchMeshy/"))) return false;
    auto* Physics = InMesh->GetPhysicsAsset(); Physics->Modify();
    for (USkeletalBodySetup* Body : Physics->SkeletalBodySetups)
    {
        if (!Body) continue;
        Body->Modify(); Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        Body->DefaultInstance.LinearDamping = .8f; Body->DefaultInstance.AngularDamping = 2.5f;
    }
    const bool bOriginalRobe = InMesh->GetPathName().Contains(TEXT("/OriginalRobeV05/"));
    if (bOriginalRobe || InMesh->GetPathName().Contains(TEXT("/LayeredV04/")))
    {
        // This revision owns its physics asset; preserve V01-V03 packages.
        const FReferenceSkeleton& Ref = InMesh->GetRefSkeleton();
        TArray<FTransform> Frames = Ref.GetRefBonePose();
        for (int32 I = 0; I < Frames.Num(); ++I)
            if (Ref.GetParentIndex(I) != INDEX_NONE) Frames[I] *= Frames[Ref.GetParentIndex(I)];
        auto FitCapsule = [&](FName BoneName, FName EndName, float Radius)
        {
            const int32 Index = Physics->FindBodyIndex(BoneName);
            const int32 Bone = Ref.FindBoneIndex(BoneName), End = Ref.FindBoneIndex(EndName);
            if (Index == INDEX_NONE || Bone == INDEX_NONE || End == INDEX_NONE) return;
            USkeletalBodySetup* Body = Physics->SkeletalBodySetups[Index];
            const FVector A = Frames[Bone].GetLocation(), B = Frames[End].GetLocation();
            const float Scale = Frames[Bone].GetScale3D().GetAbsMax();
            FKSphylElem Shape;
            Shape.Center = Frames[Bone].InverseTransformPosition((A + B) * .5f);
            Shape.Rotation = FRotationMatrix::MakeFromZ(
                Frames[Bone].InverseTransformVectorNoScale(B - A)).Rotator();
            Shape.Radius = Radius / Scale;
            Shape.Length = FMath::Max(0.f, (B - A).Size() - Radius) / Scale;
            Body->AggGeom.EmptyElements(); Body->AggGeom.SphylElems.Add(Shape);
            Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes();
        };
        FitCapsule(TEXT("LeftUpLeg"), TEXT("LeftLeg"), 6.7f);
        FitCapsule(TEXT("RightUpLeg"), TEXT("RightLeg"), 6.7f);
        FitCapsule(TEXT("LeftLeg"), TEXT("LeftFoot"), 5.0f);
        FitCapsule(TEXT("RightLeg"), TEXT("RightFoot"), 5.0f);
        FitCapsule(TEXT("LeftFoot"), TEXT("LeftToeBase"), 4.3f);
        FitCapsule(TEXT("RightFoot"), TEXT("RightToeBase"), 4.3f);

        FSkeletalMeshModel* Model = InMesh->GetImportedModel();
        if (!Model || Model->LODModels.Num() == 0) return false;
        auto FindSection = [&](const TCHAR* Slot) -> int32
        {
            const auto& Sections = InMesh->GetImportedModel()->LODModels[0].Sections;
            for (int32 I = 0; I < Sections.Num(); ++I)
            {
                const int32 MaterialIndex = Sections[I].MaterialIndex;
                if (InMesh->GetMaterials().IsValidIndex(MaterialIndex)
                    && InMesh->GetMaterials()[MaterialIndex].ImportedMaterialSlotName.ToString().Contains(Slot))
                    return I;
            }
            return INDEX_NONE;
        };
        int32 ClothSection = FindSection(bOriginalRobe ? TEXT("OriginalRobe") : TEXT("RobeCloth"));
        if (ClothSection == INDEX_NONE) return false;
        const bool bCleanRobe = FindSection(TEXT("OriginalRobeV06")) != INDEX_NONE;
        UClothingAssetCommon* CleanCloth = nullptr;
        if (bCleanRobe)
        {
            for (UClothingAssetBase* Asset : InMesh->GetMeshClothingAssets())
                if (Asset && Asset->GetName().StartsWith(TEXT("Witch_CleanRobe_ChaosV06Cm")))
                    CleanCloth = Cast<UClothingAssetCommon>(Asset);
            if (!CleanCloth)
            {
                // Replacing the old cage also retires its simulation, not just
                // its visible section. Clear persisted section user data too.
                for (int32 S = 0; S < Model->LODModels[0].Sections.Num(); ++S)
                {
                    if (UClothingAssetBase* Old = InMesh->GetSectionClothingAsset(0, S))
                        Old->UnbindFromSkeletalMesh(InMesh, 0, S);
                    const FSkelMeshSection& Section = Model->LODModels[0].Sections[S];
                    auto& User = Model->LODModels[0].UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
                    User.CorrespondClothAssetIndex = INDEX_NONE;
                    User.ClothingData.AssetGuid = FGuid(); User.ClothingData.AssetLodIndex = INDEX_NONE;
                }
                InMesh->SetMeshClothingAssets({});
            }
        }
        // Import stage may resume after a later save failed. Do not add another
        // simulation to a section that already owns the completed cloth asset.
        if (!Model->LODModels[0].Sections[ClothSection].HasClothingData() && !CleanCloth)
        {
            InMesh->Modify();
            FSkeletalMeshClothBuildParams Params;
            Params.AssetName = bCleanRobe ? TEXT("Witch_CleanRobe_ChaosV06Cm")
                : bOriginalRobe ? TEXT("Witch_OriginalRobe_ChaosV05") : TEXT("Witch_Robe_ChaosV04");
            Params.LodIndex = 0;
            Params.SourceSection = bOriginalRobe ? FindSection(TEXT("SimProxy")) : ClothSection;
            if (Params.SourceSection == INDEX_NONE) return false;
            // V05 extracts its low-poly cage and removes only that render
            // section. The dense original skirt is bound to the cloth below.
            Params.bRemoveFromMesh = bOriginalRobe; Params.PhysicsAsset = Physics;
            if (bCleanRobe)
            {
                // Dedicated cloth collisions: do not inherit auto-generated
                // torso volumes fitted to a fused long robe, or ragdoll shapes.
                UPhysicsAsset* ClothPhysics = NewObject<UPhysicsAsset>(InMesh,
                    MakeUniqueObjectName(InMesh, UPhysicsAsset::StaticClass(), TEXT("Witch_ClothCollisionV06")), RF_Transactional);
                auto AddCollider = [&](FName BoneName, FName EndName, float Radius)
                {
                    const int32 Bone = Ref.FindBoneIndex(BoneName), End = Ref.FindBoneIndex(EndName);
                    if (Bone == INDEX_NONE || End == INDEX_NONE) return;
                    USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(ClothPhysics);
                    Body->BoneName = BoneName;
                    const FVector A = Frames[Bone].GetLocation(), B = Frames[End].GetLocation();
                    const float Scale = Frames[Bone].GetScale3D().GetAbsMax();
                    FKSphylElem Shape;
                    Shape.Center = Frames[Bone].InverseTransformPosition((A + B) * .5f);
                    Shape.Rotation = FRotationMatrix::MakeFromZ(Frames[Bone].InverseTransformVectorNoScale(B - A)).Rotator();
                    Shape.Radius = Radius / Scale;
                    Shape.Length = FMath::Max(0.f, (B - A).Size() - Radius) / Scale;
                    Body->AggGeom.SphylElems.Add(Shape);
                    ClothPhysics->SkeletalBodySetups.Add(Body);
                };
                AddCollider(TEXT("Hips"), TEXT("Spine02"), 8.f);
                AddCollider(TEXT("LeftUpLeg"), TEXT("LeftLeg"), 6.0f);
                AddCollider(TEXT("RightUpLeg"), TEXT("RightLeg"), 6.0f);
                AddCollider(TEXT("LeftLeg"), TEXT("LeftFoot"), 4.3f);
                AddCollider(TEXT("RightLeg"), TEXT("RightFoot"), 4.3f);
                ClothPhysics->UpdateBodySetupIndexMap();
                ClothPhysics->SetPreviewMesh(InMesh, false);
                Params.PhysicsAsset = ClothPhysics;
            }
            UClothingAssetFactory* Factory = NewObject<UClothingAssetFactory>();
            UClothingAssetCommon* Cloth = Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(InMesh, Params));
            if (!Cloth || Cloth->LodData.IsEmpty()) return false;
            FClothLODDataCommon& Lod = Cloth->LodData[0];
            if (bOriginalRobe)
            {
                Lod.bUseMultipleInfluences = true;
                Lod.SkinningKernelRadius = 4.f;
                Lod.bSmoothTransition = true;
                // Removing the cage can shift the remaining section indices.
                ClothSection = FindSection(TEXT("OriginalRobe"));
                if (ClothSection == INDEX_NONE) return false;
            }
            Lod.PointWeightMaps.Reset();
            FPointWeightMap MaxDistance(Lod.PhysicalMeshData.Vertices.Num());
            MaxDistance.Name = bCleanRobe ? TEXT("WaistAndAnklePins_LimitedDrape") : TEXT("WaistPinToFreeHem");
            MaxDistance.CurrentTarget = static_cast<uint8>(EWeightMapTargetCommon::MaxDistance);
            MaxDistance.bEnabled = true;
            for (int32 I = 0; I < MaxDistance.Num(); ++I)
            {
                const float Z = Lod.PhysicalMeshData.Vertices[I].Z;
                if (bCleanRobe)
                {
                    // Keep both copies of each waist/ankle cut on their common
                    // skin. Only the middle garment receives secondary motion.
                    const float Waist = FMath::SmoothStep(0.f, 1.f, (82.f - Z) / 16.f);
                    const float Ankle = FMath::SmoothStep(0.f, 1.f, (Z - 26.f) / 16.f);
                    MaxDistance[I] = 6.f * Waist * Ankle;
                }
                else
                {
                    const float Free = FMath::Clamp((91.f - Z) / 82.f, 0.f, 1.f);
                    MaxDistance[I] = 65.f * Free * Free;
                }
            }
            Lod.PointWeightMaps.Add(MoveTemp(MaxDistance));
            UChaosClothConfig* Config = NewObject<UChaosClothConfig>(Cloth);
            Config->Density = .45f;
            Config->EdgeStiffnessWeighted = { .85f, .85f };
            Config->BendingStiffnessWeighted = { bCleanRobe ? .35f : .12f, bCleanRobe ? .35f : .12f };
            Config->AreaStiffnessWeighted = { .8f, .8f };
            Config->AnimDriveStiffness = { bCleanRobe ? .25f : .04f, bCleanRobe ? .25f : .04f };
            Config->bUseBendingElements = true;
            Config->CollisionThickness = bCleanRobe ? .5f : 1.2f;
            Config->FrictionCoefficient = .3f;
            Config->DampingCoefficient = bCleanRobe ? .12f : .025f;
            Config->LocalDampingCoefficient = .3f;
            Config->bUseCCD = true;
            Config->bUseSelfCollisions = true;
            Config->SelfCollisionThickness = bCleanRobe ? .25f : .6f;
            Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(), Config);
            UChaosClothSharedSimConfig* Shared = NewObject<UChaosClothSharedSimConfig>(Cloth);
            Shared->IterationCount = 6; Shared->MaxIterationCount = 12; Shared->SubdivisionCount = 3;
            Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(), Shared);
            Cloth->ApplyParameterMasks(true);
            Cloth->InvalidateAllCachedData();
            InMesh->AddClothingAsset(Cloth);
            if (bCleanRobe) CleanCloth = Cloth;
            else
            {
                if (!Cloth->BindToSkeletalMesh(InMesh, 0, ClothSection, 0)) return false;
                InMesh->PostEditChange(); InMesh->MarkPackageDirty();
            }
        }
        if (bCleanRobe)
        {
            if (!CleanCloth || CleanCloth->LodData.IsEmpty()) return false;
            // Same persistence contract as the Skeletal Mesh Editor's Apply
            // Clothing action, including after the render-only FBX reimport.
            FScopedSkeletalMeshPostEditChange ScopedPostEditChange(InMesh);
            InMesh->Modify(); CleanCloth->Modify();
            ClothSection = FindSection(TEXT("OriginalRobeV06"));
            if (ClothSection == INDEX_NONE) return false;
            if (UClothingAssetBase* Current = InMesh->GetSectionClothingAsset(0, ClothSection))
                Current->UnbindFromSkeletalMesh(InMesh, 0, ClothSection);
            // A reimport can retain LodMap after dropping transient section
            // binding data. Unbind the retained asset itself to reset both.
            CleanCloth->UnbindFromSkeletalMesh(InMesh, 0, INDEX_NONE);
            InMesh->SetMeshClothingAssets({ CleanCloth });
            if (!CleanCloth->BindToSkeletalMesh(InMesh, 0, ClothSection, 0)) return false;
            const FSkelMeshSection& Section = InMesh->GetImportedModel()->LODModels[0].Sections[ClothSection];
            auto& User = InMesh->GetImportedModel()->LODModels[0].UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
            User.CorrespondClothAssetIndex = 0;
            User.ClothingData.AssetGuid = CleanCloth->GetAssetGuid();
            User.ClothingData.AssetLodIndex = 0;
            // FBX reimport preserves disabled flags by source section index.
            // The removed cage's index can now belong to the visible robe.
            for (FSkelMeshSection& VisibleSection : InMesh->GetImportedModel()->LODModels[0].Sections)
            {
                const int32 Slot = VisibleSection.MaterialIndex;
                if (InMesh->GetMaterials().IsValidIndex(Slot)
                    && !InMesh->GetMaterials()[Slot].ImportedMaterialSlotName.ToString().Contains(TEXT("SimProxy")))
                {
                    VisibleSection.bDisabled = false;
                    InMesh->GetImportedModel()->LODModels[0].UserSectionsData.FindOrAdd(VisibleSection.OriginalDataSectionIndex).bDisabled = false;
                }
            }
            InMesh->MarkPackageDirty();
        }
    }
    Physics->MarkPackageDirty(); return true;
#else
    return false;
#endif
}
