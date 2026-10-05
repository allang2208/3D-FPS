#include "RuneSwordComponent.h"
#include "AzureDragonEnergyComponent.h"
#include "AzureDragonStrikeClock.h"
#include "RuneSwordWhirlwindFeel.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/PlayerController.h"
#include "SceneView.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
const FSoftObjectPath ClawPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Meshes/SK_AzureDragonClaw_RakeV9.SK_AzureDragonClaw_RakeV9"));
const FSoftObjectPath GrabPath(TEXT("/Game/Weapons/AzureDragon20261004/CoherentV9/Animations/A_AzureDragonClaw_RakeV9.A_AzureDragonClaw_RakeV9"));
const FSoftObjectPath MaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/Materials/M_AzureDragonClaw.M_AzureDragonClaw"));
float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
FVector FitClawCenter(const FVector& Center,const FQuat& Rotation,const FVector& Extent,
    const FVector& Eye,const FVector& Forward,const FVector& Right,const FVector& Up,float TanH,float TanV)
{
    const FVector Offset=Center-Eye;
    const float Depth=FMath::Clamp(float(FVector::DotProduct(Offset,Forward)),180.f,280.f);
    const float HalfWidth=FMath::Abs(FVector::DotProduct(Right,Rotation.GetAxisX()))*Extent.X
        +FMath::Abs(FVector::DotProduct(Right,Rotation.GetAxisY()))*Extent.Y
        +FMath::Abs(FVector::DotProduct(Right,Rotation.GetAxisZ()))*Extent.Z;
    const float HalfHeight=FMath::Abs(FVector::DotProduct(Up,Rotation.GetAxisX()))*Extent.X
        +FMath::Abs(FVector::DotProduct(Up,Rotation.GetAxisY()))*Extent.Y
        +FMath::Abs(FVector::DotProduct(Up,Rotation.GetAxisZ()))*Extent.Z;
    // Reposition the enlarged silhouette rather than undoing its requested 2x size.
    const float LimitH=FMath::Max(0.f,Depth*TanH*.96f-HalfWidth);
    const float LimitV=FMath::Max(0.f,Depth*TanV*.94f-HalfHeight);
    return Eye+Forward*Depth+Right*FMath::Clamp(float(FVector::DotProduct(Offset,Right)),-LimitH,LimitH)
        +Up*FMath::Clamp(float(FVector::DotProduct(Offset,Up)),-LimitV,LimitV);
}
}

void URuneSwordComponent::RefreshAzureDragon(const FColdSteelItem* Item,UColdSteelStatusModel* Profile)
{
    const auto* Enchant=Profile?Profile->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    const bool Enabled=Item&&Enchant&&Enchant->Effect(*Item,TEXT("azureDragonClaw"))>0.;
    const FString NewInstance=Enabled?Item->InstanceId:FString();
    if(NewInstance!=AzureDragonInstance){StopAzureDragon();ClearAzureDragonEnergy();bSwingAzureDragon=false;}
    AzureDragonInstance=NewInstance;bAzureDragonEquipped=Enabled;
    const int32 NewLimit=Enabled?FMath::Max(1,int32(Enchant->Effect(*Item,TEXT("azureDragonHitsToSummon"),9.))):9;
    if(NewLimit!=AzureDragonHitsToSummon){ClearAzureDragonEnergy();AzureDragonHitsToSummon=NewLimit;}
    if(Enabled)
    {
        AzureDragonSeconds=FMath::Max(.1f,float(Enchant->Effect(*Item,TEXT("azureDragonActiveSeconds"),30.)));
        AzureDragonReachMultiplier=FMath::Max(1.f,float(Enchant->Effect(*Item,TEXT("azureDragonReachMultiplier"),1.5)));
        AzureDragonPhysicalMultiplier=FMath::Max(1.f,float(Enchant->Effect(*Item,TEXT("azureDragonPhysicalMultiplier"),2.)));
        AzureDragonMagicScale=FMath::Max(0.f,float(Enchant->Effect(*Item,TEXT("azureDragonMagicAttackScale"),1.)));
    }
    if(Enabled&&Character.IsValid())
    {
        AzureDragonHealth=Character->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!AzureDragonEnergyDisplay&&Character->IsLocallyControlled())
        {
            AzureDragonEnergyDisplay=NewObject<UAzureDragonEnergyComponent>(Character.Get());
            AzureDragonEnergyDisplay->RegisterComponent();
        }
        PrepareAzureDragon();
    }
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->Configure(Enabled);
}

void URuneSwordComponent::OnAzureDragonHit()
{
    // Invoked only after a live enemy accepted the original sword hit, including lethal contact.
    // Nine successful attacks, not nine targets inside a single cleave/whirlwind.
    if(!bSwingAzureDragon||!bAzureDragonEquipped||AzureDragonInstance!=InstanceId)return;
    // Active attacks consume this summon, not charge or refresh the next one.
    if(bSwingAzureDragonActive||AzureDragonActiveUntil>GetWorld()->GetTimeSeconds())return;
    if(bSwingAzureDragonCharged)return;
    bSwingAzureDragonCharged=true;
    ++AzureDragonCharge;
    const bool Summoned=AzureDragonCharge>=AzureDragonHitsToSummon;
    if(Summoned)
    {
        AzureDragonCharge=0;
        AzureDragonNextClaw=SwingAzureDragonClaw=0;
        AzureDragonActiveUntil=GetWorld()->GetTimeSeconds()+AzureDragonSeconds;
        UE_LOG(LogTemp,Display,TEXT("AzureDragon: summoned after %d attacks, duration=%.1fs, claw components=%d"),
            AzureDragonHitsToSummon,AzureDragonSeconds,AzureDragonClaws.Num());
    }
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->SetEnergy(Summoned?1.f:float(AzureDragonCharge)/AzureDragonHitsToSummon,Summoned);
}

void URuneSwordComponent::CaptureAzureDragonAttack(UColdSteelStatusModel* Profile)
{
    bSwingAzureDragonCharged=false;
    bSwingAzureDragon=bAzureDragonEquipped&&AzureDragonInstance==InstanceId;
    bSwingAzureDragonActive=bSwingAzureDragon&&GetWorld()&&GetWorld()->GetTimeSeconds()<AzureDragonActiveUntil;
    if(bSwingAzureDragonActive)
    {
        // Freeze the selected side for this attack; misses do not reorder its pose.
        SwingAzureDragonClaw=AzureDragonNextClaw;
        AzureDragonNextClaw=SwingAzureDragonClaw^1;
    }
    SwingAzureDragonReachMultiplier=bSwingAzureDragonActive?AzureDragonReachMultiplier:1.f;
    SwingSkills.AzureDragonPhysicalMultiplier=bSwingAzureDragonActive?AzureDragonPhysicalMultiplier:1.f;
    // The character's physical attack stat, before this enchantment's doubling.
    // Do not use weapon damage, a heavy/skill multiplier, or already mitigated HP.
    SwingSkills.AzureDragonMagicDamage=bSwingAzureDragonActive&&Profile?
        FMath::Max(0.f,Profile->Derived(TEXT("atk")))*AzureDragonMagicScale:0.f;
}

void URuneSwordComponent::ClearAzureDragonEnergy()
{
    AzureDragonCharge=0;AzureDragonActiveUntil=0.f;bSwingAzureDragonActive=bSwingAzureDragonCharged=false;
    AzureDragonNextClaw=SwingAzureDragonClaw=0;
    SwingAzureDragonReachMultiplier=1.f;
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->ClearEnergy();
}

void URuneSwordComponent::PrepareAzureDragon()
{
    if(!Character.IsValid()||!Character->IsLocallyControlled())return;
    if(!AzureDragonMesh||!AzureDragonMaterial||!AzureDragonGrab)
    {
        // Loading is owned by equipment refresh, never the strike or hit path.
        if(AzureDragonLoad)return;
        TWeakObjectPtr<URuneSwordComponent> Weak(this);
        AzureDragonLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{ClawPath,MaterialPath,GrabPath},FStreamableDelegate::CreateLambda([Weak]()
            {
                if(!Weak.IsValid())return;
                auto* Self=Weak.Get();
                Self->AzureDragonMesh=Cast<USkeletalMesh>(ClawPath.ResolveObject());
                Self->AzureDragonGrab=Cast<UAnimSequence>(GrabPath.ResolveObject());
                Self->AzureDragonMaterial=Cast<UMaterialInterface>(MaterialPath.ResolveObject());
                if(Self->AzureDragonMesh&&Self->AzureDragonMaterial&&Self->AzureDragonGrab&&Self->bAzureDragonEquipped)Self->PrepareAzureDragon();
            }));
        return;
    }
    if(!AzureDragonClaws.IsEmpty())return;
    for(int32 I=0;I<2;++I)
    {
        auto* Claw=NewObject<USkeletalMeshComponent>(Character.Get());
        Claw->SetMobility(EComponentMobility::Movable);
        Claw->SetSkeletalMesh(AzureDragonMesh);
        Claw->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Claw->SetGenerateOverlapEvents(false);
        Claw->SetCanEverAffectNavigation(false);
        Claw->SetCastShadow(false);
        Claw->SetOnlyOwnerSee(true);
        Claw->bVisibleInRayTracing=false;
        Claw->SetHiddenInGame(false);
        Claw->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Claw->SetVisibility(false);
        auto* MID=UMaterialInstanceDynamic::Create(AzureDragonMaterial,this);
        MID->SetScalarParameterValue(TEXT("Reveal"),0.f);
        const auto Bounds=AzureDragonMesh->GetBounds();
        MID->SetScalarParameterValue(TEXT("WristX"),Bounds.Origin.X-Bounds.BoxExtent.X);
        MID->SetScalarParameterValue(TEXT("LengthX"),FMath::Max(1.f,2.f*Bounds.BoxExtent.X));
        // The selected Fab silhouette is retained; all original slots become energy.
        for(int32 Slot=0;Slot<FMath::Max(1,AzureDragonMesh->GetMaterials().Num());++Slot)Claw->SetMaterial(Slot,MID);
        Claw->RegisterComponent();
        Claw->PlayAnimation(AzureDragonGrab,false);
        Claw->SetPlayRate(0.f); // Only the sword's published source time advances the gesture.
        Claw->bEnableUpdateRateOptimizations=false;
        Claw->SetForcedLOD(1); // Preserve all three deforming joints of each finger.
        Claw->SetBoundsScale(1.8f); // Hooked fingers extend below the straight source bounds.
        Claw->SetComponentTickEnabled(false); // Gesture is sampled on the same clock as opacity and sweep.
        AzureDragonClaws.Add(Claw);AzureDragonMIDs.Add(MID);
    }
}

void URuneSwordComponent::TickAzureDragon(float Delta)
{
    if(AzureDragonHealth.IsValid()&&AzureDragonHealth->IsDead())
    {ClearAzureDragonEnergy();StopAzureDragon();bSwingAzureDragon=false;return;}
    if(AzureDragonActiveUntil>0.f&&GetWorld())
    {
        const float Remaining=FMath::Max(0.f,AzureDragonActiveUntil-GetWorld()->GetTimeSeconds());
        if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->SetEnergy(Remaining/AzureDragonSeconds,false,false);
        if(Remaining<=0.f)AzureDragonActiveUntil=0.f;
    }
}

void URuneSwordComponent::UpdateAzureDragonPose()
{
    // Called after the sword has published its final source time and bone pose.
    // Thus low FPS, accelerated attacks, retimed windups and whirlwind hitstop
    // never advance the dragon on an independent clock or leave it a frame late.
    if(!bAzureDragonEquipped||!Character.IsValid()||!Character->IsLocallyControlled()||!CanUse())
    {StopAzureDragon();return;}
    const float Now=GetWorld()->GetTimeSeconds();
    const bool Active=Now<AzureDragonActiveUntil;
    const bool Striking=bSwingAzureDragonActive&&(bAttacking||bUppercut||bWhirlwind);
    if((!Active&&!Striking)||AzureDragonInstance!=InstanceId||AzureDragonClaws.Num()!=2||!Viewmodel)
    {StopAzureDragon();return;}
    const FTransform Aim=Character->GetMeleeAimTransform();
    const float Phase=Striking&&bWhirlwind?WhirlwindFeel::Phase(Elapsed,WhirlwindTuning):0.f;
    const auto Pose=Striking&&bWhirlwind?AzureDragonStrikeClock::Revolution(Phase):
        AzureDragonStrikeClock::Contact(Elapsed,ContactStart,ContactEnd);
    const bool ContactPose=Striking&&Pose.Visible;
    if(!Active&&!ContactPose){StopAzureDragon();return;}
    const uint8 Stroke=!ContactPose?0:(bUppercut||IsRisingDragonFinisher())?4:
        (bThrustAttack||bPommelAttack?3:(bOverheadAttack||bHeavyAttack?2:(CurrentClip==TEXT("Slash2")?1:0)));
    auto* PC=Cast<APlayerController>(Character->GetController());
    const auto* Local=PC?PC->GetLocalPlayer():nullptr;
    FSceneViewProjectionData Projection;
    if(!Local||!Local->ViewportClient||!Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))
    {StopAzureDragon();return;}
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    const FQuat ViewRotation=View.Quaternion();
    const FVector Forward=ViewRotation.GetAxisX(),Right=ViewRotation.GetAxisY(),Up=ViewRotation.GetAxisZ();
    const float TanH=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[0][0]));
    const float TanV=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[1][1]));
    constexpr float IdleDepth=210.f;
    const float SummonAge=FMath::Max(0.f,Now-(AzureDragonActiveUntil-AzureDragonSeconds));
    FVector Contact=Eye+Forward*IdleDepth;
    if(ContactPose&&bWhirlwind)
    {
        const float EffectiveReach=AzureDragonRange(WhirlwindCast.RadiusCM);
        const FVector Radial=FRotator(0,WhirlwindYaw+90.f+WhirlwindTuning.TurnDegrees*Phase,0).Vector();
        Contact=Aim.GetLocation()-FVector(0,0,45.f)+Radial*EffectiveReach;
    }
    else if(ContactPose&&bQuickCombatStrike)
    {
        const float EffectiveReach=AzureDragonRange(QuickCombatRangeCM);
        Contact=ReadBlade(Aim).Tip+Aim.GetUnitAxis(EAxis::X)*EffectiveReach*Pose.Sweep;
    }
    else if(ContactPose)
    {
        const float EffectiveReach=bDashAttack?AzureDragonRange(DashCast.RangeCM):AzureDragonRange(SwingReach);
        const auto Blade=ReadBlade(Aim);
        FVector DeltaTip=(Blade.Tip-Blade.Origin)*SwingRangeMultiplier*SwingAzureDragonReachMultiplier;
        if(bUppercut)
            DeltaTip+=Blade.Forward*FMath::Max(0.,FVector::DotProduct(DeltaTip,Blade.Forward))*(UppercutReachGrowth-1.f);
        Contact=Blade.Origin+DeltaTip.GetClampedToMaxSize(EffectiveReach);
    }
    // Long swords and revolutions can put the physical extension behind/offscreen.
    // Compress its presentation into the view frustum; damage keeps its real 1.5x reach.
    const FVector Offset=Contact-Eye;
    const float ContactDepth=FMath::Clamp(float(FVector::DotProduct(Offset,Forward)),180.f,280.f);
    Contact=Eye+Forward*ContactDepth
        +Right*FMath::Clamp(float(FVector::DotProduct(Offset,Right)),-ContactDepth*TanH*.32f,ContactDepth*TanH*.32f)
        +Up*FMath::Clamp(float(FVector::DotProduct(Offset,Up)),-ContactDepth*TanV*.28f,ContactDepth*TanV*.32f);
    const auto Bounds=AzureDragonMesh->GetBounds();
    const uint8 AttackingClaw=SwingAzureDragonClaw^(ContactPose&&bWhirlwind&&Phase>=.5f?1:0);
    if(ContactPose)AzureDragonNextClaw=AttackingClaw^1;
    const float Entry=Active?FMath::SmoothStep(0.f,.22f,SummonAge):1.f;
    for(int32 I=0;I<AzureDragonClaws.Num();++I)
    {
        const bool ClawStriking=ContactPose&&I==AttackingClaw;
        const bool Visible=Active||ClawStriking;
        if(!Visible){AzureDragonClaws[I]->SetVisibility(false);AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),0.f);continue;}
        const float Side=I==0?-1.f:1.f;
        const float Bob=1.4f*FMath::Sin(SummonAge*(I==0?1.6f:1.83f)+I*2.1f);
        const FVector IdleCenter=Eye+Forward*IdleDepth+Right*(Side*IdleDepth*TanH*.56f)
            +Up*(-IdleDepth*TanV*.14f+Bob);
        // Opposed yaw exposes the side of each palm; cant preserves depth and fingers.
        const FQuat IdleRotation=ViewRotation*FRotator(-14.f,-Side*40.f,Side*20.f).Quaternion();
        FVector Center=IdleCenter;
        FQuat Rotation=IdleRotation;
        if(ClawStriking)
        {
            const float Sweep=Ease(Pose.Sweep);
            float Pitch=26.f-48.f*Sweep;
            float Yaw=-Side*(48.f-96.f*Sweep),Roll=Side*(32.f-68.f*Sweep);
            if(Stroke==2){Pitch=70.f-120.f*Sweep;Yaw=-Side*(22.f-32.f*Sweep);Roll=Side*(30.f-25.f*Sweep);}
            else if(Stroke==4){Pitch=-45.f+105.f*Sweep;Yaw=-Side*(28.f-42.f*Sweep);Roll=Side*(16.f+18.f*Sweep);}
            else if(Stroke==3){Pitch=-12.f+26.f*Sweep;Yaw=-Side*(20.f-26.f*Sweep);Roll=Side*18.f;}
            const FQuat StrikeRotation=ViewRotation*FRotator(Pitch,Yaw,Roll).Quaternion();
            Rotation=FQuat::Slerp(IdleRotation,StrikeRotation,Pose.Reveal).GetNormalized();
            // A raking arc across the contact region: outer/high windup to inner/low exit.
            const float Lateral=Stroke==3?.10f*(1.f-Sweep):(.28f-.52f*Sweep);
            const float Vertical=Stroke==4?(-.20f+.40f*Sweep):
                (Stroke==3?.025f*FMath::Sin(Sweep*PI):(.20f-.40f*Sweep));
            const FVector StrikeCenter=Contact+Right*(Side*Lateral*ContactDepth*TanH)
                +Up*(Vertical*ContactDepth*TanV)+Forward*(12.f*FMath::Sin(Sweep*PI));
            Center=FMath::Lerp(IdleCenter,StrikeCenter,Pose.Reveal);
        }
        const float Depth=FMath::Clamp(float(FVector::DotProduct(Center-Eye,Forward)),180.f,280.f);
        const float StrikeSize=Stroke==2?1.25f:(Stroke==4?1.1f:1.f);
        const float DesiredSize=ClawStriking?FMath::Lerp(.85f,StrikeSize,Pose.Reveal):.85f;
        const float Size=2.f*FMath::Min(DesiredSize,Depth*TanV*.42f/FMath::Max(1.f,float(Bounds.SphereRadius)));
        // One original rig and gesture, with a mirrored left counterpart.
        const FVector ClawScale(Size,Side*Size,Size);
        Center=FitClawCenter(Center,Rotation,Bounds.BoxExtent*Size,Eye,Forward,Right,Up,TanH,TanV);
        AzureDragonClaws[I]->SetWorldTransform(FTransform(Rotation,
            Center-Rotation.RotateVector(Bounds.Origin*ClawScale),ClawScale));
        AzureDragonClaws[I]->SetVisibility(true);
        AzureDragonClaws[I]->SetPosition((ClawStriking?Pose.Grab:0.f)*AzureDragonGrab->GetPlayLength(),false);
        AzureDragonClaws[I]->TickAnimation(0.f,false);
        AzureDragonClaws[I]->RefreshBoneTransforms();
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),Entry*(Active?(ClawStriking?.65f+.35f*Pose.Reveal:.65f):Pose.Reveal));
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Age"),ClawStriking?Elapsed/FMath::Max(.1f,SwingRate):SummonAge);
    }
}

void URuneSwordComponent::StopAzureDragon()
{
    for(int32 I=0;I<AzureDragonClaws.Num();++I)
    {AzureDragonClaws[I]->SetVisibility(false);AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),0.f);}
}

void URuneSwordComponent::DestroyAzureDragon()
{
    ClearAzureDragonEnergy();
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->DestroyComponent();AzureDragonEnergyDisplay=nullptr;
    AzureDragonHealth.Reset();
    StopAzureDragon();
    if(AzureDragonLoad)AzureDragonLoad->CancelHandle();AzureDragonLoad.Reset();
    for(const auto& Claw:AzureDragonClaws)if(Claw)Claw->DestroyComponent();
    AzureDragonClaws.Reset();AzureDragonMIDs.Reset();AzureDragonMesh=nullptr;AzureDragonMaterial=nullptr;AzureDragonGrab=nullptr;
}
