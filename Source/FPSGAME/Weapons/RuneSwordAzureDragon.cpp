#include "RuneSwordComponent.h"
#include "AzureDragonPresentationPrivate.h"
using namespace AzureDragonPresentation;

#include "../Characters/FPSComponentVisibility.h"
#include "AzureDragonClawShake.h"
#include "AzureDragonEnergyComponent.h"
#include "AzureDragonStrikeClock.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/OverlapResult.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Animation/AnimSequence.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "SceneView.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
/** One fixed-topology ribbon per talon (talon, station, edge); only positions change per frame. */
UE::Geometry::FDynamicMesh3 BuildTrailRibbons()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 Talon=0;Talon<RiftTalons;++Talon)
        for(int32 I=0;I<TrailSamples;++I)
            for(int32 Edge=0;Edge<2;++Edge)
            {
                // Spread rest positions so the first bounds are sane before any update.
                Mesh.AppendVertex(FVector3d(300.,(Edge?-1.:1.)*(I+1)*5.,Talon*10.));
                UV->AppendElement(FVector2f(float(I)/(TrailSamples-1),float(Edge)));
                Normals->AppendElement(FVector3f(-1.f,0.f,0.f));
            }
    auto Triangle=[&](int32 A,int32 B,int32 C)
    {
        const int32 Id=Mesh.AppendTriangle(A,B,C);
        UV->SetTriangle(Id,FIndex3i(A,B,C));Normals->SetTriangle(Id,FIndex3i(A,B,C));
    };
    for(int32 Talon=0;Talon<RiftTalons;++Talon)
        for(int32 I=0;I<TrailSamples-1;++I)
        {
            const int32 V=(Talon*TrailSamples+I)*2;
            Triangle(V,V+2,V+1);Triangle(V+1,V+2,V+3);
        }
    return Mesh;
}
/** Expiry motes: one camera-facing quad each (collapsed until born); UV0.x = 2 * mote + corner x. */
UE::Geometry::FDynamicMesh3 BuildMotes(int32 Motes)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 Mote=0;Mote<Motes;++Mote)
        for(int32 Corner=0;Corner<4;++Corner)
        {
            Mesh.AppendVertex(FVector3d(800.,(Mote%32)*4.,(Mote/32)*4.));
            UV->AppendElement(FVector2f(2.f*Mote+float(Corner&1),float(Corner>>1)));
            Normals->AppendElement(FVector3f(-1.f,0.f,0.f));
        }
    for(int32 Mote=0;Mote<Motes;++Mote)
    {
        const int32 V=Mote*4;
        for(const FIndex3i& T:{FIndex3i(V,V+2,V+1),FIndex3i(V+1,V+2,V+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    return Mesh;
}
/** Camera-facing card quads; UV0.x = card index + across, UV0.y = up the flame. */
UE::Geometry::FDynamicMesh3 BuildCards(int32 Cards)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 Card=0;Card<Cards;++Card)
        for(int32 Corner=0;Corner<4;++Corner)
        {
            const float X=float(Corner&1),Y=float(Corner>>1);
            Mesh.AppendVertex(FVector3d(800.,(X-.5)*40.+Card*3.,(Y-.5)*60.));
            UV->AppendElement(FVector2f(Card+X,Y));
            Normals->AppendElement(FVector3f(-1.f,0.f,0.f));
        }
    for(int32 Card=0;Card<Cards;++Card)
    {
        const int32 V=Card*4;
        for(const FIndex3i& T:{FIndex3i(V,V+2,V+1),FIndex3i(V+1,V+2,V+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    return Mesh;
}
}

void URuneSwordComponent::RefreshAzureDragon(const FColdSteelItem* Item,UColdSteelStatusModel* Profile)
{
    const auto* Enchant=Profile?Profile->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    const bool Enabled=Item&&Enchant&&Enchant->Effect(*Item,TEXT("azureDragonClaw"))>0.;
    const FString NewInstance=Enabled?Item->InstanceId:FString();
    // Weapon switch, unequip or enchant removal: the claws on screen blow away (V10.15) while the
    // charge and active window clear at once.
    if(NewInstance!=AzureDragonInstance)
    {BeginAzureDragonDissolve(1.f);ClearAzureDragonEnergy();bSwingAzureDragon=false;AzureDragonClipSide.Reset();}
    AzureDragonInstance=NewInstance;bAzureDragonEquipped=Enabled;
    const int32 NewLimit=Enabled?FMath::Max(1,int32(Enchant->Effect(*Item,TEXT("azureDragonHitsToSummon"),9.))):9;
    if(NewLimit!=AzureDragonHitsToSummon){BeginAzureDragonDissolve(1.f);ClearAzureDragonEnergy();AzureDragonHitsToSummon=NewLimit;}
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
        AzureDragonSummonedAt=GetWorld()->GetTimeSeconds();AzureDragonDissolveStart=-100.f;
        AzureDragonActiveUntil=AzureDragonSummonedAt+AzureDragonSeconds;
        UE_LOG(LogTemp,Display,TEXT("AzureDragon: summoned after %d attacks, duration=%.1fs, claw components=%d"),
            AzureDragonHitsToSummon,AzureDragonSeconds,AzureDragonClaws.Num());
    }
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->SetEnergy(Summoned?1.f:float(AzureDragonCharge)/AzureDragonHitsToSummon,Summoned);
}

void URuneSwordComponent::CaptureAzureDragonAttack(UColdSteelStatusModel* Profile)
{
    bSwingAzureDragonCharged=false;AzureDragonSwingLateral=0.f;
    bSwingAzureDragon=bAzureDragonEquipped&&AzureDragonInstance==InstanceId;
    bSwingAzureDragonActive=bSwingAzureDragon&&GetWorld()&&GetWorld()->GetTimeSeconds()<AzureDragonActiveUntil;
    if(bSwingAzureDragonActive)
    {
        // Freeze the selected side for this attack; misses do not reorder its pose. Horizontal strokes
        // then take the side that matches the blade (ChooseAzureDragonClaw, once the clip is set).
        SwingAzureDragonClaw=AzureDragonNextClaw;
        AzureDragonNextClaw=SwingAzureDragonClaw^1;
        ++AzureDragonSwingSerial;AzureDragonStrikeEntry=-1.f;
    }
    SwingAzureDragonReachMultiplier=bSwingAzureDragonActive?AzureDragonReachMultiplier:1.f;
    SwingSkills.AzureDragonPhysicalMultiplier=bSwingAzureDragonActive?AzureDragonPhysicalMultiplier:1.f;
    // The character's physical attack stat, before this enchantment's doubling.
    // Do not use weapon damage, a heavy/skill multiplier, or already mitigated HP.
    SwingSkills.AzureDragonMagicDamage=bSwingAzureDragonActive&&Profile?
        FMath::Max(0.f,Profile->Derived(TEXT("atk")))*AzureDragonMagicScale:0.f;
}

void URuneSwordComponent::ChooseAzureDragonClaw()
{
    // The right claw rakes right -> left, the left claw left -> right: take the one that moves with the
    // blade. Each clip's direction is learned from its real contact sweep (SweepBlade) on any swing
    // while the enchantment is equipped; vertical strokes and not-yet-learned clips keep alternating.
    if(!AzureDragonClawSwing()||bOverheadAttack||IsRisingDragonFinisher())return;
    if(const int8* Side=AzureDragonClipSide.Find(CurrentClip);Side&&*Side!=0)
    {SwingAzureDragonClaw=*Side>0?1:0;AzureDragonNextClaw=SwingAzureDragonClaw^1;}
}

bool URuneSwordComponent::AzureDragonClawBand(const FVector& Origin,float& OutNear,float& OutFar)
{
    // One broad overlap per frame decides whether the claw line has anything to find and over which
    // distances, so idle swings skip its sweep and crowded ones sweep only the occupied band.
    if(AzureDragonBandFrame!=GFrameCounter)
    {
        AzureDragonBandFrame=GFrameCounter;AzureDragonBandNear=AzureDragonBandFar=0.f;
        const float Pad=AzureDragonReach::TraceRadiusCM;
        TArray<FOverlapResult> Overlaps;
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(AzureDragonClawBand),false,Character.Get());
        GetWorld()->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
            FCollisionShape::MakeSphere(AzureDragonReach::ClawReachCM+Pad),Query);
        float Near=TNumericLimits<float>::Max(),Far=0.f;
        for(const FOverlapResult& Overlap:Overlaps)
        {
            AActor* Target=Overlap.GetActor();const UPrimitiveComponent* Shape=Overlap.GetComponent();
            if(!IsValid(Target)||!Shape||Target==Character.Get()||!Target->CanBeDamaged()||HitActors.Contains(Target))continue;
            const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            if(Combat?Combat->IsDead():!Target->IsA<APawn>())continue;
            const float Distance=float(FVector::Distance(Shape->Bounds.Origin,Origin)),Radius=float(Shape->Bounds.SphereRadius);
            Near=FMath::Min(Near,Distance-Radius-Pad);Far=FMath::Max(Far,Distance+Radius+Pad);
        }
        if(Far>0.f){AzureDragonBandNear=FMath::Max(0.f,Near);AzureDragonBandFar=FMath::Min(AzureDragonReach::ClawReachCM,Far);}
    }
    OutNear=AzureDragonBandNear;OutFar=AzureDragonBandFar;
    return OutFar>OutNear;
}

void URuneSwordComponent::NotifyAzureDragonNetHit(AActor* Target,float Applied,bool bKilled)
{
    // Remote clients forward every hit and get 0 back locally, so their charge comes from the receipt.
    if(IsEquipped()&&(Applied>0.f||bKilled)&&IsValid(Target)&&Target->FindComponentByClass<UMonsterCombatComponent>())
        OnAzureDragonHit();
}

void URuneSwordComponent::BeginAzureDragonDissolve(float Rate)
{
    // V10.15: every way the owner's claws go away (expiry, death, weapon switch, unequip, enchant
    // removal) blows them away instead of cutting them. Presentation only; nothing if not on screen.
    if(!bAzureDragonShown||bAzureDragonRemote||!Character.IsValid()||!Character->IsLocallyControlled()||!GetWorld())return;
    const float Now=GetWorld()->GetTimeSeconds();
    if(AzureDragonDissolveStart>=0.f&&(Now-AzureDragonDissolveStart)*AzureDragonDissolveRate<DissolveSeconds)return;
    AzureDragonDissolveStart=Now;AzureDragonDissolveRate=Rate;
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
    // V10.13: also built for other players' pawns (driven by their replicated body state); those
    // copies are seen by the local viewer and are hidden by any geometry in front, not drawn over it.
    if(!Character.IsValid()||GetNetMode()==NM_DedicatedServer)return;
    const bool bOwnerView=Character->IsLocallyControlled();
    const float Occlusion=bOwnerView?NearOcclusionCM:1.e7f;
    if(!AzureDragonMesh||!AzureDragonMaterial||!AzureDragonGrab)
    {
        // Loading is owned by equipment refresh, never the strike or hit path.
        if(AzureDragonLoad)return;
        TWeakObjectPtr<URuneSwordComponent> Weak(this);
        AzureDragonLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{ClawPath,AzureDragonMaterialPath,GrabPath,TrailMaterialPath,FlameMaterialPath,DepthMaterialPath,DustMaterialPath},
            FStreamableDelegate::CreateLambda([Weak]()
            {
                if(!Weak.IsValid())return;
                auto* Self=Weak.Get();
                Self->AzureDragonMesh=Cast<USkeletalMesh>(ClawPath.ResolveObject());
                Self->AzureDragonGrab=Cast<UAnimSequence>(GrabPath.ResolveObject());
                Self->AzureDragonMaterial=Cast<UMaterialInterface>(AzureDragonMaterialPath.ResolveObject());
                Self->AzureDragonTrailMaterial=Cast<UMaterialInterface>(TrailMaterialPath.ResolveObject()); // optional
                Self->AzureDragonFlameMaterial=Cast<UMaterialInterface>(FlameMaterialPath.ResolveObject()); // optional
                Self->AzureDragonDustMaterial=Cast<UMaterialInterface>(DustMaterialPath.ResolveObject());   // optional
                if(Self->AzureDragonMesh&&Self->AzureDragonMaterial&&Self->AzureDragonGrab&&(Self->bAzureDragonEquipped||Self->bAzureDragonRemote))
                    Self->PrepareAzureDragon();
            }));
        return;
    }
    // View-space overlay meshes with fixed topology; only vertex positions change per frame.
    auto MakeOverlay=[this,bOwnerView,Occlusion](UMaterialInterface* Material,UE::Geometry::FDynamicMesh3&& Mesh,int32 SortPriority,
        TObjectPtr<UMaterialInstanceDynamic>& OutMID)
    {
        auto* Overlay=NewObject<UDynamicMeshComponent>(Character.Get());
        Overlay->SetMobility(EComponentMobility::Movable);
        Overlay->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Overlay->SetGenerateOverlapEvents(false);
        Overlay->SetCanEverAffectNavigation(false);
        Overlay->SetCastShadow(false);
        Overlay->SetReceivesDecals(false);
        Overlay->SetOnlyOwnerSee(bOwnerView);
        Overlay->bVisibleInRayTracing=false;
        Overlay->bAffectDistanceFieldLighting=false;
        Overlay->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        Overlay->SetTranslucentSortPriority(SortPriority); // claws (2) also skip the depth test
        Overlay->RegisterComponent();
        Overlay->SetMesh(MoveTemp(Mesh));
        OutMID=UMaterialInstanceDynamic::Create(Material,this);
        OutMID->SetScalarParameterValue(TEXT("NearOcclusion"),Occlusion);
        Overlay->SetMaterial(0,OutMID);
        Overlay->SetVisibility(false);
        return Overlay;
    };
    if(AzureDragonTrailMaterial&&AzureDragonRiftMeshes.IsEmpty())
        for(int32 Slot=0;Slot<2;++Slot)
        {
            TObjectPtr<UMaterialInstanceDynamic> MID;
            AzureDragonRiftMeshes.Add(MakeOverlay(AzureDragonTrailMaterial,BuildTrailRibbons(),1,MID));
            AzureDragonRiftMIDs.Add(MID);
        }
    if(AzureDragonFlameMaterial&&!AzureDragonFlames)
        AzureDragonFlames=MakeOverlay(AzureDragonFlameMaterial,BuildCards(2*FlameCards),3,AzureDragonFlameMID);
    if(AzureDragonDustMaterial&&!AzureDragonDust)
        AzureDragonDust=MakeOverlay(AzureDragonDustMaterial,BuildMotes(2*MotesPerClaw),4,AzureDragonDustMID);
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
        Claw->SetOnlyOwnerSee(bOwnerView);
        Claw->SetTranslucentSortPriority(2);
        Claw->bVisibleInRayTracing=false;
        Claw->SetHiddenInGame(false);
        Claw->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Claw->SetVisibility(false);
        auto* MID=UMaterialInstanceDynamic::Create(AzureDragonMaterial,this);
        MID->SetScalarParameterValue(TEXT("Reveal"),0.f);
        MID->SetScalarParameterValue(TEXT("NearOcclusion"),Occlusion);
        const auto Bounds=AzureDragonMesh->GetBounds();
        MID->SetScalarParameterValue(TEXT("WristX"),Bounds.Origin.X-Bounds.BoxExtent.X);
        MID->SetScalarParameterValue(TEXT("LengthX"),FMath::Max(1.f,2.f*Bounds.BoxExtent.X));
        // One spirit material covers body, talon and smoke slots; vertex color selects the layer.
        for(int32 Slot=0;Slot<FMath::Max(1,AzureDragonMesh->GetMaterials().Num());++Slot)Claw->SetMaterial(Slot,MID);
        Claw->RegisterComponent();
        Claw->PlayAnimation(AzureDragonGrab,false);
        Claw->SetPlayRate(0.f); // Only the sword's published source time advances the gesture.
        Claw->bEnableUpdateRateOptimizations=false;
        Claw->SetForcedLOD(1); // Preserve all three deforming joints of each finger.
        Claw->SetBoundsScale(1.8f); // Hooked fingers extend below the straight source bounds.
        Claw->SetComponentTickEnabled(false); // Gesture is sampled on the same clock as opacity and sweep.
        // Unseen opaque follower: writes this claw into custom depth so the glass keeps only its
        // front-most surface. Same pose (leader), same transform (attached), never in the main pass.
        auto* Depth=NewObject<USkeletalMeshComponent>(Character.Get());
        Depth->SetSkeletalMesh(AzureDragonMesh);
        Depth->SetupAttachment(Claw);
        Depth->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Depth->SetGenerateOverlapEvents(false);
        Depth->SetCanEverAffectNavigation(false);
        Depth->SetCastShadow(false);
        Depth->SetOnlyOwnerSee(bOwnerView);
        Depth->bVisibleInRayTracing=false;
        Depth->SetRenderInMainPass(false);
        // Custom depth ONLY: left in the depth prepass (engine default) it occluded the sky dome, so the
        // uncleared scene colour (black + the editor sky warning text) showed through the thin glass.
        Depth->SetRenderInDepthPass(false);
        Depth->SetRenderCustomDepth(true);
        Depth->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
        Depth->SetCustomDepthStencilValue(ClawDepthStencil);
        // Loaded with the claw batch (held by AzureDragonLoad); the engine default is one-sided.
        UMaterialInterface* Solid=Cast<UMaterialInterface>(DepthMaterialPath.ResolveObject());
        if(!Solid)Solid=UMaterial::GetDefaultMaterial(MD_Surface);
        for(int32 Slot=0;Slot<FMath::Max(1,AzureDragonMesh->GetMaterials().Num());++Slot)Depth->SetMaterial(Slot,Solid);
        Depth->SetForcedLOD(1);
        Depth->SetBoundsScale(1.8f);
        // Never in the main pass, so it is never "recently rendered": refresh from the leader anyway.
        Depth->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Depth->SetLeaderPoseComponent(Claw);
        Depth->RegisterComponent();
        Depth->SetVisibility(false);
        AzureDragonClaws.Add(Claw);AzureDragonMIDs.Add(MID);AzureDragonClawDepth.Add(Depth);
    }
}

void URuneSwordComponent::StopAzureDragon()
{
    // Runs every tick while the enchantment is idle: once everything is hidden and reset, do nothing.
    if(!bAzureDragonShown)return;
    bAzureDragonShown=false;
    AzureDragonClawMode[0]=AzureDragonClawMode[1]=0u;AzureDragonStrikeEntry=-1.f;
    for(int32 I=0;I<AzureDragonClaws.Num();++I)
    {AzureDragonClaws[I]->SetVisibility(false,true);AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),0.f);}
    for(const auto& Rift:AzureDragonRiftMeshes)if(Rift)Rift->SetVisibility(false);
    if(AzureDragonFlames)AzureDragonFlames->SetVisibility(false);
    if(AzureDragonDust)AzureDragonDust->SetVisibility(false);
    AzureDragonMoteSeed=-1000.f;
    for(FAzureDragonRift& Rift:AzureDragonRifts)Rift=FAzureDragonRift();
    AzureDragonRiftCutting=INDEX_NONE;
    bAzureDragonAnchored=false; // the next summon starts at the body, not where it was left
    AzureDragonIdleStart[0]=AzureDragonIdleStart[1]=-1.f;
}

void URuneSwordComponent::DestroyAzureDragon()
{
    ClearAzureDragonEnergy();
    if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->DestroyComponent();AzureDragonEnergyDisplay=nullptr;
    AzureDragonHealth.Reset();
    StopAzureDragon();
    if(AzureDragonLoad)AzureDragonLoad->CancelHandle();AzureDragonLoad.Reset();
    for(const auto& Depth:AzureDragonClawDepth)if(Depth)Depth->DestroyComponent();
    for(const auto& Claw:AzureDragonClaws)if(Claw)Claw->DestroyComponent();
    AzureDragonClawDepth.Reset();
    AzureDragonClaws.Reset();AzureDragonMIDs.Reset();AzureDragonMesh=nullptr;AzureDragonMaterial=nullptr;AzureDragonGrab=nullptr;
    for(const auto& Rift:AzureDragonRiftMeshes)if(Rift)Rift->DestroyComponent();
    AzureDragonRiftMeshes.Reset();AzureDragonRiftMIDs.Reset();AzureDragonTrailMaterial=nullptr;
    if(AzureDragonFlames)AzureDragonFlames->DestroyComponent();
    AzureDragonFlames=nullptr;AzureDragonFlameMID=nullptr;AzureDragonFlameMaterial=nullptr;
}
