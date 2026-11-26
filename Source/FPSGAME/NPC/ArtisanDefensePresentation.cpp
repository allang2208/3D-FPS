#include "ArtisanDefenseComponent.h"
#include "ArtisanDefenseArrow.h"
#include "SmithHammerAnimInstance.h"
#include "VillageArtisanMerchant.h"
#include "../Characters/FPSBodyBowMotion.h"
#include "../Weapons/Bow/BowFlexMeshComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInterface.h"

namespace ArtisanEquipment
{
    const FSoftObjectPath Hammer(TEXT("/Game/Weapons/SteelWarhammer20261014/SM_SteelWarhammer.SM_SteelWarhammer"));
    const FSoftObjectPath Bow(TEXT("/Game/Weapons/DarkBow20260925/ElasticV15/SK_Bow_Flex_Original.SK_Bow_Flex_Original"));
    const FSoftObjectPath Grip(TEXT("/Game/Weapons/DarkBow20260925/GripContactV22/SM_Bow_GripWrap_Fitted.SM_Bow_GripWrap_Fitted"));
    const FSoftObjectPath Rest(TEXT("/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_ArrowRestWood.SM_Bow_ArrowRestWood"));
    const FSoftObjectPath Sight(TEXT("/Game/Weapons/DarkBow20260925/WoodBracketV19/SM_Bow_WoodBracketSight.SM_Bow_WoodBracketSight"));
    const FSoftObjectPath Arrow(TEXT("/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow.SM_Bow_WoodArrow"));
    const FSoftObjectPath Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    const FSoftObjectPath Cord(TEXT("/Game/Weapons/DarkBow20260925/ArmsV2/Materials/M_BowString.M_BowString"));
    const FSoftObjectPath SmithWalk(TEXT("/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SourceGripV16/Animations/J_Hammer_Gait_Fwd.J_Hammer_Gait_Fwd"));
    const FSoftObjectPath SmithReady(TEXT("/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/SourceGripV16/Animations/J_Hammer_Idle.J_Hammer_Idle"));
    const FSoftObjectPath SmithSwing(TEXT("/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/NaturalComboV17/Animations/J_Hammer_Natural_Slash2.J_Hammer_Natural_Slash2"));
    const FSoftObjectPath SmithClose(TEXT("/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/NaturalComboV17/Animations/J_Hammer_Natural_Slash1.J_Hammer_Natural_Slash1"));
    const FSoftObjectPath Walk(TEXT("/Game/Characters/JasonPlayer20261003/Animations/J_MF_Unarmed_Walk_Fwd.J_MF_Unarmed_Walk_Fwd"));
    const FSoftObjectPath BowCarry(TEXT("/Game/Characters/JasonPlayer20261003/BowSparrow20261018/AnimationsV3/J_SparrowBowV3_Carry.J_SparrowBowV3_Carry"));
    const FSoftObjectPath BowDraw(TEXT("/Game/Characters/JasonPlayer20261003/BowSparrow20261018/AnimationsV3/J_SparrowBowV3_Draw.J_SparrowBowV3_Draw"));
    const FSoftObjectPath BowRelease(TEXT("/Game/Characters/JasonPlayer20261003/BowSparrow20261018/AnimationsV3/J_SparrowBowV3_Release.J_SparrowBowV3_Release"));

    const FTransform BowInLeftHand(FQuat(-.99535266,-.06922950,-.06692311,-.00128438).GetNormalized(),
        FVector(7.674,-2.934,-4.303));
    const FVector Brace(-24.081, .123, 1.5);

    template<class T>
    T* MakePart(AActor* Owner, USceneComponent* Parent, FName Name, FName Socket = NAME_None)
    {
        T* Part = NewObject<T>(Owner, Name);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
        Part->SetupAttachment(Parent, Socket);
        Owner->AddInstanceComponent(Part);
        Part->RegisterComponent();
        return Part;
    }

    UStaticMeshComponent* StaticPart(AActor* Owner, USceneComponent* Parent, FName Name, const FSoftObjectPath& Path, FName Socket = NAME_None)
    {
        auto* Part = MakePart<UStaticMeshComponent>(Owner, Parent, Name, Socket);
        Part->SetStaticMesh(Cast<UStaticMesh>(Path.ResolveObject()));
        return Part;
    }
}

void UArtisanDefenseComponent::WarmPresentation()
{
    using namespace ArtisanEquipment;
    const TArray<FSoftObjectPath> Paths = IsBow()
        ? TArray<FSoftObjectPath>{ArtisanEquipment::Bow, Grip, Rest, Sight, Arrow, Cylinder, Cord, Walk, BowCarry, BowDraw, BowRelease}
        : TArray<FSoftObjectPath>{ArtisanEquipment::Hammer, SmithWalk, SmithReady, SmithSwing, SmithClose};
    PresentationAssets = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateUObject(this, &UArtisanDefenseComponent::RefreshPresentation));
}

void UArtisanDefenseComponent::RefreshPresentation()
{
    using namespace ArtisanEquipment;
    if (!GetOwner() || GetNetMode() == NM_DedicatedServer) return;
    const bool bActive = !IsAtWork() && State != EArtisanGuardState::Downed;
    if (Hammer) Hammer->SetVisibility(bActive);
    if (Bow) Bow->SetVisibility(bActive, true);
    if (!bActive) return;
    auto* Character = Cast<ACharacter>(GetOwner());
    Body = Character ? Character->GetMesh() : nullptr;
    if (!Body || !Body->GetSkeletalMeshAsset()) return;
    const bool bBow = IsBow();
    if (!bBow && !Hammer && ArtisanEquipment::Hammer.ResolveObject())
    {
        Hammer = StaticPart(GetOwner(), Body, TEXT("GuardSteelHammer"), ArtisanEquipment::Hammer, TEXT("hand_r"));
        Hammer->SetRelativeTransform(USmithHammerAnimInstance::HammerInRightHand);
    }
    if (bBow && !Bow && ArtisanEquipment::Bow.ResolveObject())
    {
        Bow = MakePart<UBowFlexMeshComponent>(GetOwner(), Body, TEXT("GuardHuntingBow"), TEXT("hand_l"));
        Bow->SetFlexMesh(Cast<USkeletalMesh>(ArtisanEquipment::Bow.ResolveObject()));
        Bow->SetRelativeTransform(BowInLeftHand);
        StaticPart(GetOwner(), Bow, TEXT("GuardHuntingGrip"), Grip);
        StaticPart(GetOwner(), Bow, TEXT("GuardHuntingRest"), Rest);
        StaticPart(GetOwner(), Bow, TEXT("GuardWoodSight"), Sight);
        for (const FName Name : {FName(TEXT("GuardUpperString")), FName(TEXT("GuardLowerString"))})
        {
            auto* String = StaticPart(GetOwner(), Bow, Name, Cylinder);
            String->SetMaterial(0, Cast<UMaterialInterface>(Cord.ResolveObject()));
            Strings.Add(String);
        }
        NockedArrow = StaticPart(GetOwner(), Bow, TEXT("GuardNockedArrow"), Arrow);
    }
    if (!bBow)
    {
        if (Clips.IsEmpty())
        {
            auto* Gait = Cast<UAnimSequence>(SmithWalk.ResolveObject());
            auto* Ready = Cast<UAnimSequence>(SmithReady.ResolveObject());
            auto* Swing = Cast<UAnimSequence>(SmithSwing.ResolveObject());
            HammerCloseClip = Cast<UAnimSequence>(SmithClose.ResolveObject());
            // Dressing, asset streaming and the guard state can arrive in any order.
            if (!Gait || !Ready || !Swing || !HammerCloseClip) return;
            Clips.Add(EArtisanGuardState::Approach, Gait);
            Clips.Add(EArtisanGuardState::Ready, Ready);
            Clips.Add(EArtisanGuardState::Attack, Swing);
            for (const auto& Marker : Swing->AuthoredSyncMarkers)
                if (Marker.MarkerName == TEXT("Contact")) { HammerClipContact = Marker.Time; break; }
        }
        if (!Cast<USmithHammerAnimInstance>(Body->GetAnimInstance()))
        {
            Body->SetRelativeRotation(FRotator(0, FResidentConversationFacing::RestYaw, 0));
            Body->SetAnimInstanceClass(USmithHammerAnimInstance::StaticClass());
        }
        return;
    }
    if (Clips.IsEmpty())
    {
        auto* Gait = Cast<UAnimSequence>(Walk.ResolveObject());
        auto* Carry = Cast<UAnimSequence>(BowCarry.ResolveObject());
        auto* Draw = Cast<UAnimSequence>(BowDraw.ResolveObject());
        auto* Release = Cast<UAnimSequence>(BowRelease.ResolveObject());
        if (!Gait || !Carry || !Draw || !Release) return;
        Clips.Add(EArtisanGuardState::Approach, Gait);
        Clips.Add(EArtisanGuardState::Returning, Gait);
        Clips.Add(EArtisanGuardState::Ready, Carry);
        Clips.Add(EArtisanGuardState::Attack, Draw);
        Clips.Add(EArtisanGuardState::Release, Release);
    }
    UAnimSequence* Clip = Clips.FindRef(State == EArtisanGuardState::Watching ? EArtisanGuardState::Ready : State);
    if (!Clip) return;
    const bool bAttack = State == EArtisanGuardState::Attack || State == EArtisanGuardState::Release;
    const float Duration = State == EArtisanGuardState::Release ? .3f : 1.4f;
    const float Rate = bAttack ? Clip->GetPlayLength() / Duration : 1.f;
    Body->SetRelativeRotation(FRotator(0, FResidentConversationFacing::RestYaw, 0));
    Body->PlayAnimation(Clip, !bAttack);
    Body->SetPlayRate(Rate);
    if (const auto* GS = GetWorld()->GetGameState(); GS && bAttack)
        Body->SetPosition(FMath::Clamp(float(GS->GetServerWorldTimeSeconds() - StateStartedAt) * Rate, 0.f, Clip->GetPlayLength()), false);
    UpdateGrip();
}

void UArtisanDefenseComponent::UpdateGrip()
{
    using namespace ArtisanEquipment;
    if (!Bow || !Body || !Body->GetAnimInstance()) return;
    const auto* Animation = Body->GetAnimInstance();
    const bool bRight = Animation->GetCurveValue(FPSBodyBowMotion::RightHoldCurve) > .5f;
    const FName Socket(bRight ? TEXT("hand_r") : TEXT("hand_l"));
    if (Bow->GetAttachSocketName() != Socket)
        Bow->AttachToComponent(Body, FAttachmentTransformRules::KeepRelativeTransform, Socket);
    const auto* Curves = bRight ? FPSBodyBowMotion::RightGripCurves : FPSBodyBowMotion::GripCurves;
    float V[7];
    for (int32 I = 0; I < 7; ++I) V[I] = Animation->GetCurveValue(Curves[I]);
    const FQuat Rotation(V[3], V[4], V[5], V[6]);
    Bow->SetRelativeTransform(Rotation.SizeSquared() > .1 ?
        FTransform(Rotation.GetNormalized(), FVector(V[0], V[1], V[2])) : BowInLeftHand);
    FVector Nock = Brace;
    const bool bDraw = State == EArtisanGuardState::Attack;
    if (bDraw)
    {
        const auto* N = FPSBodyBowMotion::NockCurves;
        const FVector InHand(Animation->GetCurveValue(N[0]), Animation->GetCurveValue(N[1]), Animation->GetCurveValue(N[2]));
        if (!InHand.IsNearlyZero())
            Nock = Bow->GetComponentTransform().InverseTransformPosition(Body->GetSocketTransform(TEXT("hand_r")).TransformPosition(InHand));
    }
    FVector Tips[2] = {FVector(-24.082,.095,69.51), FVector(-24.081,.152,-70.598)};
    Bow->ApplyStringLoad(Nock, Brace, 1.15f);
    Bow->Tips(Tips[0], Tips[1]);
    for (int32 I = 0; I < Strings.Num(); ++I)
    {
        const FVector Segment = Tips[I] - Nock;
        Strings[I]->SetRelativeTransform(FTransform(FQuat::FindBetweenNormals(FVector::UpVector, Segment.GetSafeNormal()),
            (Tips[I] + Nock) * .5, FVector(.09 / 50., .09 / 50., Segment.Size() / 100.)));
    }
    if (NockedArrow)
    {
        NockedArrow->SetVisibility(bDraw);
        if (bDraw)
        {
            const FVector Axis = (FVector(-3.5, -3.9, 2.6) - Nock).GetSafeNormal();
            AArtisanDefenseArrow::FitWoodArrow(*NockedArrow, Nock, Nock + Axis * 76.f);
        }
    }
}
