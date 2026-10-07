#include "RuneSwordComponent.h"
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
// The library Fab Dragon Claw (V10.2+); ClawV10 keeps the original claw for recovery.
const FSoftObjectPath ClawPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Meshes/SK_AzureDragonClawFabV10.SK_AzureDragonClawFabV10"));
const FSoftObjectPath GrabPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Animations/A_AzureDragonClawFabRakeV10.A_AzureDragonClawFabRakeV10"));
const FSoftObjectPath AzureDragonMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawFabV10.M_AzureDragonClawFabV10"));
// V10.8: the five talon traces are rift scars after the game's Rift Slash (裂空) look, not flames.
const FSoftObjectPath TrailMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawRiftV10.M_AzureDragonClawRiftV10"));
const FSoftObjectPath FlameMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawFlameV10.M_AzureDragonClawFlameV10"));
// Two-sided opaque material for the unseen custom-depth follower (nearest face wins, no holes).
const FSoftObjectPath DepthMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawDepthV10.M_AzureDragonClawDepthV10"));
// All five talon points (pinky, ring, middle, index, thumb).
constexpr int32 RiftTalons=5;
const FName TipBones[RiftTalons]={TEXT("digit_01_tip"),TEXT("digit_02_tip"),TEXT("digit_03_tip"),TEXT("digit_04_tip"),TEXT("digit_05_tip")};
// Each rake leaves one scar per talon spanning its whole sweep path, widest in the middle and pointed at
// both ends; it holds after the rake, then erodes away. V10.9: wider and lingering longer.
constexpr int32 TrailSamples=32,RiftPathCap=128;
// V10.10: linger halved (hold .45 -> .225 s, dissolve .6 -> .3 s).
constexpr float RiftWidth=15.f,RiftHold=.225f,RiftDissolve=.3f; // cm per unit claw scale; seconds
// One big realistic flame per arm end: a rolling mass card and a rising-tongue card.
constexpr int32 FlameCards=2;
constexpr int32 ClawDepthStencil=214;             // custom-depth tag read by the claw glass
// V10.5 (2026-10-06): the claws live in WORLD space in front of the body (eye position + yaw,
// followed with inertia), so distance and height are real: looking up/down or turning shows
// where they are. They are built big instead: 5x the Fab claw (~4.6 m hand, ~6.3 m with arm).
// V10.7: 12 m out (was 8 m) and the palms ~5.9 m either side (was ~3.9 m): yaw 26 deg at 12 m.
// V10.11: scale and farthest station are shared with the gameplay reach (AzureDragonReach.h).
constexpr float ClawWorldScale=AzureDragonReach::ClawWorldScale;
constexpr float ClawIdleDistance=1200.f,ClawIdleYaw=26.f,ClawIdleHeight=-90.f; // cm / deg from the eye
// V10.10: negative = toe-out. V10.8's +20 deg (talons in, arms splayed) read as an inverted 八; now
// the forearms converge toward the player and the talons fan outward, a 八 opening ahead.
constexpr float ClawIdleToeIn=-20.f;
constexpr float AnchorFollowRate=8.f,AnchorTurnRate=9.f;                      // inertia (1/s)
const FVector ClawPalmLocal(8.,0.,0.);            // palm centre: the claws are placed by the palm
// V10.10: the gesture asset is the 0.6 s rake (frames 0-36) followed by a seamless 4 s idle loop.
constexpr float ClawGestureSeconds=.6f,ClawIdleLoopSeconds=4.f,ClawIdleDesync=1.7f;
// V10.12: ease over this long whenever a claw changes what it is doing; a heavy charge held past the
// tap window draws the claw back into its windup.
constexpr float ClawBlendSeconds=.18f,ClawChargeDelay=.2f;
// Own claws are hidden only by geometry this close (the material default); other players' copies by
// anything in front.
constexpr float NearOcclusionCM=350.f;
// V10.14 expiry: the claws erode along a wind-biased front over FrontSeconds (material Disintegrate
// = -FrontLead + FrontSpan * age / FrontSeconds) and blow away as motes born where the front passes.
// Budget: own claws 512 motes each, other players' 256 and none beyond 60 m; ~2.4 s, then hidden.
const FSoftObjectPath DustMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawDustV10.M_AzureDragonClawDustV10"));
constexpr int32 MotesPerClaw=512,RemoteMotesPerClaw=256;
constexpr float DissolveSeconds=2.4f,FrontSeconds=1.2f,FrontLead=.1f,FrontSpan=1.25f,RemoteMoteRangeCM=6000.f;
constexpr float WindSpeedCM=520.f,MoteTurbulence=420.f;
// V10.15: death plays the same dissolve faster so it finishes before the respawn replaces the pawn
// (UFPSCombatHealthComponent's 2 s respawn timer; keep in step if that changes).
constexpr float PlayerRespawnSeconds=2.f;
constexpr float DeathDissolveRate=FMath::Max(1.f,DissolveSeconds/(PlayerRespawnSeconds-.2f));
float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
// Horizontal sweep stations around the player for the RIGHT claw (the left mirrors the yaw):
// yaw from the body forward toward the claw's own side (deg), distance (cm), height (cm).
// Windup out wide and high, rake across the front, follow through low on the far side.
struct FSweepKey{float Yaw,Distance,Height;};
constexpr FSweepKey SweepKeys[4]={{50.f,1050.f,-10.f},{32.f,1185.f,-60.f},{-12.f,1200.f,-130.f},{-46.f,1095.f,-180.f}};
// V10.12: vertical strokes (overhead chop; uppercut / rising finisher use the heights reversed) rake
// through the forward line their hits cover, crossing it near the impact.
constexpr FSweepKey VerticalKeys[4]={{16.f,1000.f,420.f},{8.f,1170.f,260.f},{1.f,1200.f,-40.f},{-5.f,1120.f,-200.f}};
// The claw reach used for hit detection must cover the farthest palm station.
constexpr bool StationsWithinReach(const FSweepKey (&Keys)[4])
{for(const FSweepKey& Key:Keys)if(Key.Distance>AzureDragonReach::ClawStationMaxCM)return false;return true;}
static_assert(ClawIdleDistance<=AzureDragonReach::ClawStationMaxCM&&StationsWithinReach(SweepKeys)&&StationsWithinReach(VerticalKeys),
    "Azure Dragon claw station beyond the gameplay reach");
FVector Bezier2(const FVector& A,const FVector& B,const FVector& C,float T)
{const float U=1.f-T;return A*(U*U)+B*(2.f*U*T)+C*(T*T);}
FVector Bezier3(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
{const float U=1.f-T;return A*(U*U*U)+B*(3.f*U*U*T)+C*(3.f*U*T*T)+D*(T*T*T);}
FVector Bezier3Tangent(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
{const float U=1.f-T;return (B-A)*(3.f*U*U)+(C-B)*(6.f*U*T)+(D-C)*(3.f*T*T);}
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

void URuneSwordComponent::TickAzureDragon(float Delta)
{
    if(AzureDragonHealth.IsValid()&&AzureDragonHealth->IsDead())
    {BeginAzureDragonDissolve(DeathDissolveRate);ClearAzureDragonEnergy();bSwingAzureDragon=false;return;}
    if(AzureDragonActiveUntil>0.f&&GetWorld())
    {
        const float Remaining=FMath::Max(0.f,AzureDragonActiveUntil-GetWorld()->GetTimeSeconds());
        if(AzureDragonEnergyDisplay)AzureDragonEnergyDisplay->SetEnergy(Remaining/AzureDragonSeconds,false,false);
        if(Remaining<=0.f){BeginAzureDragonDissolve(1.f);AzureDragonActiveUntil=0.f;} // natural expiry
    }
}

bool URuneSwordComponent::LocalAzureDragonFrame(FAzureDragonFrame& Out) const
{
    // The owner's claws, sampled from this sword's final source time and attack state.
    Out=FAzureDragonFrame();
    if(!Character.IsValid()||!GetWorld())return false;
    const float Now=GetWorld()->GetTimeSeconds();
    // V10.15: shown while the enchanted sword is held and the window is open, also through menus,
    // vaulting or building (no longer cut there); a dissolve that has begun plays on without the sword.
    const bool bLive=bAzureDragonEquipped&&AzureDragonInstance==InstanceId;
    Out.bActive=bLive&&Now<AzureDragonActiveUntil;
    // V10.12: the claws strike only on attacks whose hits reach them (slashes, heavy, overhead,
    // uppercut, rising finisher); thrust, dash, whirlwind and quick combat leave them idling. A heavy
    // charge held past the tap window draws the coming claw back into its windup.
    Out.bStriking=bLive&&AzureDragonClawSwing()&&(bAttacking||bUppercut);
    Out.Held=bLive&&bCharging&&!bAttacking?float(GetWorld()->GetTimeSeconds()-ChargeStartedAt):0.f;
    Out.bCharging=Out.bActive&&!Out.bStriking&&Out.Held>ClawChargeDelay;
    Out.DissolveStart=AzureDragonDissolveStart;Out.DissolveRate=AzureDragonDissolveRate;
    Out.DissolveAge=(Now-AzureDragonDissolveStart)*AzureDragonDissolveRate;
    Out.bDissolving=!Out.bActive&&AzureDragonDissolveStart>=0.f&&Out.DissolveAge<DissolveSeconds;
    Out.MoteBudget=MotesPerClaw;
    if(!Out.bActive&&!Out.bStriking&&!Out.bDissolving)return false;
    // Horizontal strokes sweep across the front (heavy descends); vertical ones rake down (overhead)
    // or up (uppercut, rising finisher) through the forward line their hits cover.
    Out.bVertical=Out.bStriking&&(bOverheadAttack||bUppercut||IsRisingDragonFinisher());
    Out.bRising=Out.bStriking&&(bUppercut||IsRisingDragonFinisher());
    Out.bHeavy=Out.bStriking&&bHeavyAttack;
    // The charge winds up the claw its heavy release will use (measured side once known).
    const int8* HeavySide=AzureDragonClipSide.Find(TEXT("HeavyRelease"));
    Out.Claw=Out.bCharging?(HeavySide&&*HeavySide!=0?uint8(*HeavySide>0?1:0):AzureDragonNextClaw):SwingAzureDragonClaw;
    Out.Source=Elapsed;Out.HitStart=ContactStart;Out.HitEnd=ContactEnd;Out.Rate=SwingRate;
    Out.Entry=AzureDragonStrikeEntry>=0.f?AzureDragonStrikeEntry:Elapsed;
    Out.SummonAge=FMath::Max(0.f,Now-AzureDragonSummonedAt); // keeps running through the dissolve
    return true;
}

void URuneSwordComponent::SampleAzureDragonNet(uint8& Flags,float& SourceLength,float& Entry,float& ChargeStart,float ServerNow) const
{
    // V10.13: the cosmetic part other players need, carried in the owner's body presentation.
    Flags=0;SourceLength=Entry=ChargeStart=0.f;
    FAzureDragonFrame Frame;
    if(!LocalAzureDragonFrame(Frame))return;
    const uint8 Stroke=Frame.bRising?3:(Frame.bVertical?2:(Frame.bHeavy?1:0));
    Flags=uint8((Frame.bActive?1:0)|(Frame.bStriking?2:0)|(Frame.Claw?4:0)|(Stroke<<3)|(Frame.bCharging?32:0)
        |(Frame.bDissolving?64:0)|(Frame.bDissolving&&Frame.DissolveRate>1.f?128:0));
    if(Frame.bStriking){SourceLength=CurrentAnimation?CurrentAnimation->GetPlayLength():0.f;Entry=FMath::Max(0.f,Frame.Entry);}
    if(Frame.bCharging)ChargeStart=ServerNow-Frame.Held;
}

void URuneSwordComponent::PresentAzureDragonRemote(uint8 Flags,float Source,float StrikeContactStart,float StrikeContactEnd,float Entry,float Held)
{
    // V10.13: another player's claws on this machine, rebuilt from their replicated body state and
    // anchored on their pawn; the viewing camera is the local player's.
    if(!Character.IsValid()||Character->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer)return;
    const float Now=GetWorld()->GetTimeSeconds();
    FAzureDragonFrame Frame;
    Frame.bActive=(Flags&1)!=0;Frame.bStriking=(Flags&2)!=0;Frame.bCharging=Frame.bActive&&(Flags&32)!=0;
    if(Frame.bActive&&!bAzureDragonRemoteActive)AzureDragonRemoteSummonAt=Now;
    bAzureDragonRemoteActive=Frame.bActive;
    // A new stroke (source time restarting) is a new swing for the claw blend.
    if(Frame.bStriking&&(!bAzureDragonRemoteStriking||Source+.05f<AzureDragonRemoteLastSource))++AzureDragonSwingSerial;
    bAzureDragonRemoteStriking=Frame.bStriking;AzureDragonRemoteLastSource=Source;
    // The owner flags its dissolve (bit6, bit7 = faster death dissolve); this machine plays the full
    // dissolve from when it first saw it.
    const bool bDissolveFlag=(Flags&64)!=0;
    if(bDissolveFlag&&!bAzureDragonRemoteDissolving)
    {AzureDragonRemoteDissolveAt=Now;AzureDragonRemoteDissolveRate=(Flags&128)?DeathDissolveRate:1.f;}
    if(Frame.bActive)AzureDragonRemoteDissolveAt=-100.f;
    bAzureDragonRemoteDissolving=bDissolveFlag;
    Frame.DissolveStart=AzureDragonRemoteDissolveAt;Frame.DissolveRate=AzureDragonRemoteDissolveRate;
    Frame.DissolveAge=(Now-AzureDragonRemoteDissolveAt)*AzureDragonRemoteDissolveRate;
    Frame.bDissolving=!Frame.bActive&&AzureDragonRemoteDissolveAt>=0.f&&Frame.DissolveAge<DissolveSeconds;
    auto* Viewer=GetWorld()->GetFirstPlayerController();
    if((!Frame.bActive&&!Frame.bStriking&&!Frame.bDissolving)||!Viewer){StopAzureDragon();return;}
    bAzureDragonRemote=true;
    if(AzureDragonClaws.Num()!=2){PrepareAzureDragon();return;}
    const uint8 Stroke=(Flags>>3)&3;
    Frame.Claw=(Flags&4)?1:0;
    Frame.bVertical=Frame.bStriking&&Stroke>=2;Frame.bRising=Frame.bStriking&&Stroke==3;Frame.bHeavy=Frame.bStriking&&Stroke==1;
    Frame.Source=Source;Frame.HitStart=StrikeContactStart;Frame.HitEnd=FMath::Max(StrikeContactStart,StrikeContactEnd);
    Frame.Entry=Entry;Frame.Held=Held;Frame.SummonAge=Now-AzureDragonRemoteSummonAt;
    Frame.Eye=Character->GetPawnViewLocation();Frame.Yaw=Character->GetActorRotation().Yaw;
    Viewer->GetPlayerViewPoint(Frame.ViewEye,Frame.View);
    // Other players' dust: half the motes, none when far away (the erosion itself still plays).
    Frame.MoteBudget=FVector::DistSquared(Frame.ViewEye,Frame.Eye)<FMath::Square(RemoteMoteRangeCM)?RemoteMotesPerClaw:0;
    PresentAzureDragon(Frame);
}

void URuneSwordComponent::UpdateAzureDragonPose()
{
    // Called after the sword has published its final source time and bone pose. Thus low FPS,
    // accelerated attacks and retimed windups never advance the dragon on an independent clock or
    // leave it a frame late. Other players' copies are driven by PresentAzureDragonRemote.
    if(Character.IsValid()&&!Character->IsLocallyControlled())return;
    auto* PC=Character.IsValid()?Cast<APlayerController>(Character->GetController()):nullptr;
    FAzureDragonFrame Frame;
    if(!PC||!LocalAzureDragonFrame(Frame)){StopAzureDragon();return;}
    if(Frame.bStriking&&AzureDragonStrikeEntry<0.f)AzureDragonStrikeEntry=Frame.Entry=Elapsed;
    PC->GetPlayerViewPoint(Frame.ViewEye,Frame.View);
    Frame.Eye=Frame.ViewEye;Frame.Yaw=Frame.View.Yaw;Frame.ShakePC=PC;
    PresentAzureDragon(Frame);
}

void URuneSwordComponent::PresentAzureDragon(const FAzureDragonFrame& Frame)
{
    if(AzureDragonClaws.Num()!=2||!AzureDragonGrab){StopAzureDragon();return;}
    const float Now=GetWorld()->GetTimeSeconds();
    const bool Active=Frame.bActive,Striking=Frame.bStriking,Charging=Frame.bCharging;
    const auto Pose=Striking?AzureDragonStrikeClock::Sweep(Frame.Source,Frame.HitStart,Frame.HitEnd,Frame.Entry)
        :(Charging?AzureDragonStrikeClock::Windup(Frame.Held-ClawChargeDelay):AzureDragonStrikeClock::Pose());
    const bool ContactPose=(Striking||Charging)&&Pose.Visible;
    if(!Active&&!ContactPose&&!Frame.bDissolving){StopAzureDragon();return;}
    const float Impact=Pose.Impact; // where the sweep crosses the target (later for late entries)
    // V10.14 expiry: erosion front progress; the claws stop rendering once it has passed everything.
    const float DissolveT=Frame.bDissolving?Frame.DissolveAge:0.f;
    const float Disintegrate=Frame.bDissolving?-FrontLead+FrontSpan*DissolveT/FrontSeconds:-1.f;
    const float Eroded=FMath::Clamp(DissolveT/FrontSeconds,0.f,1.f);
    const bool bClawsGone=Frame.bDissolving&&DissolveT>FrontSeconds*1.06f;
    const bool bVertical=Frame.bVertical,bRising=Frame.bRising;
    const bool bDescending=(Frame.bHeavy&&!bVertical)||Charging;
    bAzureDragonShown=true;
    const FVector Eye=Frame.ViewEye;
    const FQuat ViewRotation=Frame.View.Quaternion();
    const FVector Forward=ViewRotation.GetAxisX(),Right=ViewRotation.GetAxisY(),Up=ViewRotation.GetAxisZ();
    // World-space body anchor: the claws' owner's eye position and yaw only (not pitch), chased with
    // inertia, so the claws keep their place in front of the body while the view looks around them.
    const float Dt=GetWorld()->GetDeltaSeconds();
    const float YawGap=FMath::FindDeltaAngleDegrees(AzureDragonAnchorYaw,Frame.Yaw);
    if(!bAzureDragonAnchored||FVector::DistSquared(AzureDragonAnchor,Frame.Eye)>FMath::Square(800.f)||FMath::Abs(YawGap)>120.f)
    {AzureDragonAnchor=Frame.Eye;AzureDragonAnchorYaw=Frame.Yaw;bAzureDragonAnchored=true;}
    else
    {
        AzureDragonAnchor=FMath::VInterpTo(AzureDragonAnchor,Frame.Eye,Dt,AnchorFollowRate);
        AzureDragonAnchorYaw=FRotator::NormalizeAxis(AzureDragonAnchorYaw+YawGap*(1.f-FMath::Exp(-Dt*AnchorTurnRate)));
    }
    const FQuat BodyRotation=FRotator(0.f,AzureDragonAnchorYaw,0.f).Quaternion();
    const FVector BodyForward=BodyRotation.GetAxisX(),BodyRight=BodyRotation.GetAxisY(),WorldUp=FVector::UpVector;
    auto Station=[&](float YawDeg,float Distance,float Height)
    {
        const float A=FMath::DegreesToRadians(AzureDragonAnchorYaw+YawDeg);
        return AzureDragonAnchor+FVector(FMath::Cos(A),FMath::Sin(A),0.f)*Distance+WorldUp*Height;
    };
    const float SummonAge=Frame.SummonAge;
    const uint8 AttackingClaw=Frame.Claw;
    const float Entry=Active?FMath::SmoothStep(0.f,.22f,SummonAge):1.f;
    const bool Shown=Active||Frame.bDissolving;
    // The expiry wind: across the view from the owner's left, a little back and rising.
    const FVector Wind=(BodyRight*.8f-BodyForward*.2f+WorldUp*.3f).GetSafeNormal();
    FVector DisCenter[2]={FVector::ZeroVector,FVector::ZeroVector},DisAxis[2]={FVector::ZeroVector,FVector::ZeroVector};
    // Key light for the claw glass: from above-left of the viewer, so the sculpt is always shaded.
    const FVector KeyDir=(Up*.80f-Right*.45f-Forward*.40f).GetSafeNormal();
    int32 TrailClaw=INDEX_NONE;float TrailStrength=0.f,TrailSize=1.f;
    float FlameStrength[2]={0.f,0.f};
    for(int32 I=0;I<AzureDragonClaws.Num();++I)
    {
        const bool ClawStriking=ContactPose&&I==AttackingClaw;
        const bool Visible=(Shown||ClawStriking)&&!bClawsGone;
        if(!Visible)
        {
            AzureDragonClaws[I]->SetVisibility(false,true);AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),0.f);
            AzureDragonClawMode[I]=0u;
            continue;
        }
        const float Side=I==0?-1.f:1.f;
        const float Bob=14.f*FMath::Sin(SummonAge*(I==0?1.6f:1.83f)+I*2.1f);
        // Idle (V10.10): two great arms either side of the view line forming a "八" that opens ahead:
        // talons forward and fanned outward (slight lift), forearms angled in toward the player,
        // palms facing inward toward each other, thumbs up.
        const FVector IdlePalm=Station(Side*ClawIdleYaw,ClawIdleDistance,ClawIdleHeight+Bob);
        const float ToeIn=FMath::DegreesToRadians(ClawIdleToeIn);
        const FVector IdleFinger=(BodyForward*FMath::Cos(ToeIn)-BodyRight*(Side*FMath::Sin(ToeIn))+WorldUp*.12f).GetSafeNormal();
        const FVector IdleBack=BodyRight*(Side*FMath::Cos(ToeIn))+BodyForward*FMath::Sin(ToeIn);
        const FQuat IdleRotation=FRotationMatrix::MakeFromXZ(IdleFinger,IdleBack).ToQuat();
        FVector Palm=IdlePalm;
        FQuat Rotation=IdleRotation;
        float Scale=ClawWorldScale;
        FVector Stretch(1.f,1.f,1.f);
        float AnimPhase=0.f; // gesture thirds; the talon snap (frame 18) is pinned to the impact
        if(ClawStriking)
        {
            // ~0.6 s stroke on the sword clock. Lead: draw back and hold. Sweep: ease into the target,
            // quickest where it crosses, then carry through. Recovery: swoop back to the station.
            const float H0=bDescending?70.f:0.f,H3=bDescending?-110.f:0.f;
            FVector P[4];
            for(int32 K=0;K<4;++K)
                P[K]=bVertical?Station(Side*VerticalKeys[K].Yaw,VerticalKeys[K].Distance,VerticalKeys[bRising?3-K:K].Height)
                    :Station(Side*SweepKeys[K].Yaw,SweepKeys[K].Distance,SweepKeys[K].Height+FMath::Lerp(H0,H3,K/3.f));
            const float G=Pose.Phase;
            const float T=FMath::Clamp(G-1.f,0.f,1.f);
            float S=0.f;
            if(G>=1.f)
            {
                if(T<Impact)S=.5f*FMath::Pow(T/Impact,1.6f);
                else S=.5f+.5f*(1.f-FMath::Pow(1.f-(T-Impact)/(1.f-Impact),2.2f));
            }
            AnimPhase=G<1.f||G>2.f?G:1.f+(T<Impact?.5f*T/Impact:.5f+.5f*(T-Impact)/(1.f-Impact));
            const float SR=G<1.f?0.f:(G<=2.f?S:1.f);
            // Talons reach out from the body, raised in the windup and raking down through the target
            // (a rising stroke ends talons-up); the palm leads the direction of travel.
            const FVector SweepPalm=Bezier3(P[0],P[1],P[2],P[3],SR);
            const FVector Radial=(SweepPalm-AzureDragonAnchor).GetSafeNormal2D();
            const float Lift=bRising?-.35f+.75f*SR:.40f-.75f*SR;
            const FVector Finger=(Radial*.85f+WorldUp*Lift).GetSafeNormal();
            const FVector Travel=Bezier3Tangent(P[0],P[1],P[2],P[3],FMath::Clamp(SR,.02f,.98f));
            FVector Back=-(Travel-Finger*FVector::DotProduct(Travel,Finger)).GetSafeNormal();
            if(Back.IsNearlyZero())Back=BodyRight*Side;
            // Wrist: talons trail while the sweep builds, whip through at impact, settle; the
            // forearm rolls over across the sweep.
            float Whip=0.f,Roll=0.f;
            if(G<1.f){const float A=Ease(G/.8f);Whip=18.f*A;Roll=-18.f*A;}
            else if(G<=2.f)
            {
                Whip=T<Impact?18.f*(1.f-FMath::Square(T/Impact)):-14.f*FMath::Sin(PI*(T-Impact)/(1.f-Impact));
                Roll=-18.f+36.f*SR;
            }
            else Roll=18.f*(1.f-Ease(G-2.f));
            if(bVertical)Roll*=.4f; // a chop or uppercut keeps the forearm square
            const FQuat SweepRotation=FRotationMatrix::MakeFromXZ(Finger,Back).ToQuat()*FRotator(Whip,0.f,Side*Roll).Quaternion();
            if(G<1.f)
            {
                // Reach the windup at 80% of the lead and hang there until the sweep releases.
                const float A=Ease(G/.8f);
                const FVector Mid=(IdlePalm+P[0])*.5f+WorldUp*60.f-BodyForward*60.f;
                Palm=Bezier2(IdlePalm,Mid,P[0],A);
                Rotation=FQuat::Slerp(IdleRotation,SweepRotation,A);
            }
            else if(G<=2.f){Palm=SweepPalm;Rotation=SweepRotation;}
            else
            {
                const float E=Ease(G-2.f);
                const FVector Mid=(P[3]+IdlePalm)*.5f-WorldUp*(bRising?-120.f:140.f)-BodyForward*80.f;
                Palm=Bezier2(P[3],Mid,IdlePalm,E);
                Rotation=FQuat::Slerp(SweepRotation,IdleRotation,E);
            }
            Rotation.Normalize();
            // Impact: a short swell along the talons as the sweep crosses the target.
            const float Punch=G>=1.f&&G<=2.f?FMath::Exp(-FMath::Square((T-Impact)/.10f)):0.f;
            Scale=ClawWorldScale*(1.f+.10f*Punch);
            Stretch=FVector(1.f+.06f*Punch,1.f,1.f-.03f*Punch);
            if(G>=1.f+Impact&&G<=2.f&&!bAzureDragonImpactFired)
            {
                bAzureDragonImpactFired=true;AzureDragonImpactTime=Now;
                if(Frame.ShakePC&&Frame.ShakePC->PlayerCameraManager) // the owner's camera only
                    Frame.ShakePC->PlayerCameraManager->StartCameraShake(UAzureDragonClawShake::StaticClass(),1.f);
            }
            if(G<1.f)bAzureDragonImpactFired=false;
            // Rift scars are cut only while the talons actually rake (late windup to follow-through);
            // a held heavy windup cuts nothing.
            if(Striking)
            {
                TrailClaw=I;TrailSize=Scale;
                TrailStrength=Entry*FMath::SmoothStep(.85f,1.08f,G)*(1.f-FMath::SmoothStep(2.f,2.35f,G));
            }
        }
        // While eroding, the wind carries what is left of the claw downwind.
        Palm+=Wind*(140.f*Eroded*Eroded);
        // Whenever this claw changes what it is doing (strike start, cancel, combo hand-over, charge
        // release), ease from where it was last shown instead of snapping.
        const uint32 Mode=ClawStriking?(Striking?2u+AzureDragonSwingSerial:1u):0u;
        const bool bWasShown=AzureDragonClaws[I]->IsVisible();
        if(Mode!=AzureDragonClawMode[I])
        {
            AzureDragonClawMode[I]=Mode;
            if(bWasShown)
            {
                AzureDragonBlendStart[I]=Now;
                AzureDragonBlendPalm[I]=AzureDragonShownPalm[I];AzureDragonBlendRotation[I]=AzureDragonShownRotation[I];
            }
        }
        const float Blend=bWasShown?Ease((Now-AzureDragonBlendStart[I])/ClawBlendSeconds):1.f;
        if(Blend<1.f)
        {
            Palm=FMath::Lerp(AzureDragonBlendPalm[I],Palm,Blend);
            Rotation=FQuat::Slerp(AzureDragonBlendRotation[I],Rotation,Blend).GetNormalized();
        }
        AzureDragonShownPalm[I]=Palm;AzureDragonShownRotation[I]=Rotation;
        // One original rig and gesture, with a mirrored left counterpart, placed by its palm.
        const FVector ClawScale(Scale*Stretch.X,Side*Scale*Stretch.Y,Scale*Stretch.Z);
        AzureDragonClaws[I]->SetWorldTransform(FTransform(Rotation,Palm-Rotation.RotateVector(ClawPalmLocal*ClawScale),ClawScale));
        AzureDragonClaws[I]->SetVisibility(true,true);
        // Between rakes each claw breathes through the idle loop on its own clock, restarted when its
        // rake ends (frame 36 = loop start) so the two flow together without a pop.
        float AnimTime=AnimPhase/3.f*ClawGestureSeconds;
        if(ClawStriking||AzureDragonIdleStart[I]<0.f)AzureDragonIdleStart[I]=Now-(ClawStriking?0.f:I*ClawIdleDesync);
        if(!ClawStriking&&AzureDragonGrab->GetPlayLength()>ClawGestureSeconds+1.f)
            AnimTime=ClawGestureSeconds+FMath::Fmod(Now-AzureDragonIdleStart[I],ClawIdleLoopSeconds);
        AzureDragonClaws[I]->SetPosition(AnimTime,false);
        AzureDragonClaws[I]->TickAnimation(0.f,false);
        AzureDragonClaws[I]->RefreshBoneTransforms();
        if(AzureDragonClawDepth.IsValidIndex(I))AzureDragonClawDepth[I]->MarkRenderDynamicDataDirty(); // follow this pose now
        // Idle claws stay nearly solid (was 0.65) so their structure reads.
        const float Reveal=Entry*(Shown?(ClawStriking?.9f+.1f*Pose.Reveal:.9f):Pose.Reveal);
        // Expiry erosion front: tips and the windward side go first (camera-relative like WorldPos,
        // the axis pre-divided by the claw's span); the motes are born on the same front.
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Disintegrate"),Disintegrate);
        if(Frame.bDissolving)
        {
            const float Span=.75f*float(2.*AzureDragonMesh->GetBounds().BoxExtent.X)*Scale;
            DisCenter[I]=AzureDragonClaws[I]->Bounds.Origin;
            DisAxis[I]=(Wind*.35f-Rotation.GetAxisX()*.65f).GetSafeNormal()/FMath::Max(1.f,Span);
            const FVector Relative=DisCenter[I]-Eye;
            AzureDragonMIDs[I]->SetVectorParameterValue(TEXT("DisintegrateCenter"),FLinearColor(Relative.X,Relative.Y,Relative.Z,0.f));
            AzureDragonMIDs[I]->SetVectorParameterValue(TEXT("DisintegrateAxis"),FLinearColor(DisAxis[I].X,DisAxis[I].Y,DisAxis[I].Z,0.f));
        }
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),Reveal);
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Age"),ClawStriking?Frame.Source/FMath::Max(.1f,Frame.Rate):SummonAge);
        AzureDragonMIDs[I]->SetScalarParameterValue(TEXT("Impact"),ClawStriking?FMath::Exp(-FMath::Max(0.f,Now-AzureDragonImpactTime)*11.f):0.f);
        AzureDragonMIDs[I]->SetVectorParameterValue(TEXT("KeyDir"),FLinearColor(KeyDir.X,KeyDir.Y,KeyDir.Z,0.f));
        if(I<2)FlameStrength[I]=Reveal*(1.f-Ease(Eroded/.7f)); // the arm fire dies with the claw
    }
    if(!ContactPose)bAzureDragonImpactFired=false;
    UpdateAzureDragonTrail(AzureDragonAnchor,BodyRotation,Eye,TrailClaw,TrailStrength,TrailSize);
    UpdateAzureDragonFlames(Eye,ViewRotation,FlameStrength);
    UpdateAzureDragonDust(Frame,Wind,DisCenter,DisAxis);
}

void URuneSwordComponent::UpdateAzureDragonFlames(const FVector& Eye,const FQuat& View,const float* ClawStrength)
{
    if(!AzureDragonFlames||!AzureDragonFlameMID)return;
    bool bAny=false;
    for(int32 I=0;I<2;++I)bAny|=ClawStrength[I]>.01f&&AzureDragonClaws.IsValidIndex(I);
    if(!bAny){AzureDragonFlames->SetVisibility(false);return;}
    // One big flame burns where each forearm dissolves: a rolling fire mass with a taller layer of
    // rising tongues just in front, camera-facing, standing on the arm end and rising along world up.
    const FVector3f WorldUp(View.UnrotateVector(FVector::UpVector));
    AzureDragonFlames->SetWorldTransform(FTransform(View,Eye));
    AzureDragonFlames->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        for(int32 I=0;I<2;++I)
        {
            const bool bLive=ClawStrength[I]>.01f&&AzureDragonClaws.IsValidIndex(I);
            const FTransform Claw=bLive?AzureDragonClaws[I]->GetComponentTransform():FTransform::Identity;
            const float Unit=bLive?float(FMath::Abs(Claw.GetScale3D().X))*ClawStrength[I]:0.f;
            const FVector3f Base(View.UnrotateVector(Claw.TransformPosition(FVector(-30.f,0.f,-2.f))-Eye));
            for(int32 Layer=0;Layer<FlameCards;++Layer)
            {
                const float Height=(Layer?74.f:56.f)*Unit,Width=(Layer?40.f:52.f)*Unit;
                const FVector3f Dir=Base.GetSafeNormal();
                const FVector3f Center=Base+WorldUp*(Height*(Layer?.40f:.32f))-Dir*(Layer?6.f*Unit:0.f);
                FVector3f Across=FVector3f::CrossProduct(WorldUp,Dir);
                Across=Across.SizeSquared()>1.e-6f?Across.GetUnsafeNormal():FVector3f(0.f,1.f,0.f);
                const FVector3f Rise=FVector3f::CrossProduct(Dir,Across);
                const int32 V=(I*FlameCards+Layer)*4;
                for(int32 Corner=0;Corner<4;++Corner)
                    Mesh.SetVertex(V+Corner,FVector3d(Center+Across*(((Corner&1)-.5f)*Width)+Rise*(((Corner>>1)-.5f)*Height)));
            }
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    AzureDragonFlameMID->SetScalarParameterValue(TEXT("Age"),FMath::Fmod(GetWorld()->GetTimeSeconds(),600.f));
    AzureDragonFlames->SetVisibility(true);
}

void URuneSwordComponent::UpdateAzureDragonDust(const FAzureDragonFrame& Frame,const FVector& Wind,const FVector* Center,const FVector* Axis)
{
    if(!AzureDragonDust||!AzureDragonDustMID||AzureDragonClaws.Num()!=2)return;
    const int32 Budget=FMath::Min(Frame.MoteBudget,MotesPerClaw);
    if(!Frame.bDissolving||Budget<=0)
    {
        if(AzureDragonDust->IsVisible())AzureDragonDust->SetVisibility(false);
        AzureDragonMoteSeed=-1000.f;
        return;
    }
    const float Age=Frame.DissolveAge,Dt=FMath::Min(GetWorld()->GetDeltaSeconds(),.05f)*Frame.DissolveRate;
    const FVector Eye=Frame.ViewEye;const FQuat View=Frame.View.Quaternion();
    const FTransform Claws[2]={AzureDragonClaws[0]->GetComponentTransform(),AzureDragonClaws[1]->GetComponentTransform()};
    const bool bSeed=AzureDragonMoteSeed!=Frame.DissolveStart;
    if(bSeed)
    {
        // Once per dissolve: a bounded random set of the claws' skinned vertices (CPU copy, kept by
        // the engine for skeletal meshes; bone segments if absent). Each mote is stored in its claw's
        // space and born when the erosion front reaches it, wherever the claw has drifted by then.
        AzureDragonMoteSeed=Frame.DissolveStart;
        AzureDragonMotes.SetNum(2*MotesPerClaw);
        FRandomStream Random(int32(Frame.DissolveStart*997.f)^int32(GetUniqueID()));
        for(int32 I=0;I<2;++I)
        {
            USkeletalMeshComponent* Claw=AzureDragonClaws[I];
            const FSkeletalMeshRenderData* Render=Claw->GetSkeletalMeshRenderData();
            const FSkeletalMeshLODRenderData* LOD=Render&&Render->LODRenderData.Num()>0?&Render->LODRenderData[0]:nullptr;
            FSkinWeightVertexBuffer* Weights=LOD?Claw->GetSkinWeightBuffer(0):nullptr;
            const int32 Vertices=LOD?int32(LOD->StaticVertexBuffers.PositionVertexBuffer.GetNumVertices()):0;
            const bool bSkinned=Weights&&Vertices>0&&LOD->StaticVertexBuffers.PositionVertexBuffer.GetAllocatedSize()>0
                &&Weights->GetVertexDataSize()>0&&Weights->GetNumVertices()==uint32(Vertices);
            TArray<FMatrix44f> RefToLocals;
            if(bSkinned)Claw->CacheRefToLocalMatrices(RefToLocals);
            const FReferenceSkeleton& Ref=Claw->GetSkeletalMeshAsset()->GetRefSkeleton();
            const float Scale=float(FMath::Abs(Claws[I].GetScale3D().X));
            for(int32 K=0;K<MotesPerClaw;++K)
            {
                FAzureDragonMote& Mote=AzureDragonMotes[I*MotesPerClaw+K];
                FVector World;
                if(bSkinned)
                    World=Claws[I].TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(
                        Claw,Random.RandRange(0,Vertices-1),*LOD,*Weights,RefToLocals)));
                else
                {
                    const int32 Bone=Random.RandRange(1,FMath::Max(1,Ref.GetNum()-1));
                    World=FMath::Lerp(Claw->GetBoneTransform(Bone).GetLocation(),
                        Claw->GetBoneTransform(FMath::Max(0,Ref.GetParentIndex(Bone))).GetLocation(),double(Random.FRand()))
                        +Random.GetUnitVector()*(Random.FRand()*2.5f*Scale);
                }
                Mote=FAzureDragonMote();
                Mote.Local=Claws[I].InverseTransformPosition(World);
                const float G=float(FVector::DotProduct(World-Center[I],Axis[I]))+.5f+Random.FRandRange(-.09f,.09f);
                Mote.Birth=FMath::Clamp((G+FrontLead)/FrontSpan,0.f,1.f)*FrontSeconds;
                Mote.Life=Random.FRandRange(.75f,1.15f);
                Mote.Size=Random.FRandRange(12.f,30.f)*Scale/ClawWorldScale; // cm at the standard claw scale
                Mote.Phase=Random.FRand()*2.f*PI;
                // Kick off the surface, mostly downwind and up; the wind then takes over.
                Mote.Velocity=Wind*(WindSpeedCM*Random.FRandRange(.15f,.45f))+Random.GetUnitVector()*Random.FRandRange(40.f,140.f)
                    +FVector::UpVector*Random.FRandRange(20.f,90.f);
            }
        }
    }
    const FVector Up=FVector::UpVector,Across=FVector::CrossProduct(Wind,Up).GetSafeNormal();
    AzureDragonDust->SetWorldTransform(FTransform(View,Eye));
    AzureDragonDust->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        // Camera-local quads (X ahead, Y right, Z up). Unborn and dead motes are collapsed and left
        // alone, so each frame only moves the motes that are actually flying.
        const auto Quad=[&](int32 Index,const FVector& Position,float Size)
        {
            const FVector3d C(View.UnrotateVector(Position-Eye));const double H=.5*Size;
            const int32 V=Index*4;
            Mesh.SetVertex(V,C+FVector3d(0.,-H,-H));Mesh.SetVertex(V+1,C+FVector3d(0.,H,-H));
            Mesh.SetVertex(V+2,C+FVector3d(0.,-H,H));Mesh.SetVertex(V+3,C+FVector3d(0.,H,H));
        };
        for(int32 I=0;I<2;++I)
            for(int32 K=0;K<MotesPerClaw;++K)
            {
                const int32 Index=I*MotesPerClaw+K;
                FAzureDragonMote& Mote=AzureDragonMotes[Index];
                if(bSeed){Mote.bDead=K>=Budget;Quad(Index,Claws[I].TransformPosition(Mote.Local),0.f);}
                if(Mote.bDead||Age<Mote.Birth)continue;
                if(!Mote.bBorn){Mote.bBorn=true;Mote.Position=Claws[I].TransformPosition(Mote.Local);}
                const float A=Age-Mote.Birth,U=A/Mote.Life;
                if(U>=1.f){Mote.bDead=true;Quad(Index,Mote.Position,0.f);continue;}
                const float Gust=FMath::Sin(A*4.1f+Mote.Phase),Swirl=FMath::Cos(A*3.3f+Mote.Phase*1.7f);
                Mote.Velocity+=(Wind*WindSpeedCM-Mote.Velocity)*(1.f-FMath::Exp(-Dt*1.6f))
                    +(Across*Gust+Up*(.55f+.45f*Swirl))*(MoteTurbulence*Dt);
                Mote.Position+=Mote.Velocity*Dt;
                Quad(Index,Mote.Position,Mote.Size*FMath::Min(1.f,U*8.f)*FMath::Pow(1.f-U,.8f));
            }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    AzureDragonDustMID->SetScalarParameterValue(TEXT("Age"),Age);
    AzureDragonDustMID->SetScalarParameterValue(TEXT("Fade"),1.f-FMath::SmoothStep(DissolveSeconds-.35f,DissolveSeconds,Age));
    if(!AzureDragonDust->IsVisible())AzureDragonDust->SetVisibility(true);
}

void URuneSwordComponent::UpdateAzureDragonTrail(const FVector& Origin,const FQuat& Frame,const FVector& Eye,int32 Claw,float Strength,float Size)
{
    if(AzureDragonRiftMeshes.Num()!=2||AzureDragonRiftMIDs.Num()!=2)return;
    const float Now=GetWorld()->GetTimeSeconds();
    if(Claw!=INDEX_NONE&&Strength>.05f&&AzureDragonClaws.IsValidIndex(Claw))
    {
        // A new rake (or the whirlwind handing over to the other claw) cuts into the older scar set;
        // the other set keeps holding and dissolving.
        if(AzureDragonRiftCutting==INDEX_NONE||AzureDragonRifts[AzureDragonRiftCutting].Claw!=uint8(Claw))
        {
            AzureDragonRiftCutting=AzureDragonRiftCutting!=INDEX_NONE?1-AzureDragonRiftCutting
                :(AzureDragonRifts[0].LastCut<=AzureDragonRifts[1].LastCut?0:1);
            FAzureDragonRift& Fresh=AzureDragonRifts[AzureDragonRiftCutting];
            Fresh.Path.Reset();Fresh.Width=0.f;Fresh.Claw=uint8(Claw);
        }
        FAzureDragonRift& Rift=AzureDragonRifts[AzureDragonRiftCutting];
        TArray<FAzureDragonTrailSample>& Path=Rift.Path;
        // Sampled after this frame's pose refresh, in the body frame so the scars travel with the body.
        FAzureDragonTrailSample Sample;Sample.Time=Now;
        for(int32 K=0;K<RiftTalons;++K)
            Sample.Tips[K]=FVector3f(Frame.UnrotateVector(AzureDragonClaws[Claw]->GetBoneLocation(TipBones[K])-Origin));
        if(!Path.IsEmpty()&&Now-Path.Last().Time<1.e-4f)Path.Last()=Sample;else Path.Add(Sample);
        if(Path.Num()>RiftPathCap)
        {
            // Keep the whole path at half resolution rather than dropping where it began.
            int32 W=0;
            for(int32 R=0;R<Path.Num();R+=2)Path[W++]=Path[R];
            if(Path[W-1].Time<Now)Path[W++]=Sample;
            Path.SetNum(W,EAllowShrinking::No);
        }
        Rift.LastCut=Now;
        Rift.Width=FMath::Max(Rift.Width,RiftWidth*Size*Strength);
    }
    else AzureDragonRiftCutting=INDEX_NONE;
    const FVector3f CameraLocal(Frame.UnrotateVector(Eye-Origin));
    for(int32 Slot=0;Slot<2;++Slot)
    {
        FAzureDragonRift& Rift=AzureDragonRifts[Slot];
        UDynamicMeshComponent* Mesh=AzureDragonRiftMeshes[Slot];
        const TArray<FAzureDragonTrailSample>& Path=Rift.Path;
        const bool bCutting=Slot==AzureDragonRiftCutting;
        const float Since=Now-Rift.LastCut;
        if(Path.Num()<2||(!bCutting&&Since>RiftHold+RiftDissolve))
        {
            if(!bCutting){Rift.Path.Reset();Rift.Claw=255;}
            Mesh->SetVisibility(false);
            continue;
        }
        // Resample each talon's path by arc length: UV.x runs from where the cut began to the talon.
        FVector3f Centers[RiftTalons][TrailSamples];
        float Run[RiftPathCap+2];
        for(int32 K=0;K<RiftTalons;++K)
        {
            Run[0]=0.f;
            for(int32 I=1;I<Path.Num();++I)Run[I]=Run[I-1]+(Path[I].Tips[K]-Path[I-1].Tips[K]).Size();
            const float Total=Run[Path.Num()-1];
            int32 J=1;
            for(int32 S=0;S<TrailSamples;++S)
            {
                const float L=Total*S/(TrailSamples-1);
                while(J<Path.Num()-1&&Run[J]<L)++J;
                const float A=FMath::Clamp((L-Run[J-1])/FMath::Max(1.e-3f,Run[J]-Run[J-1]),0.f,1.f);
                Centers[K][S]=FMath::Lerp(Path[J-1].Tips[K],Path[J].Tips[K],A);
            }
        }
        Mesh->SetWorldTransform(FTransform(Frame,Origin));
        Mesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Edit)
        {
            for(int32 K=0;K<RiftTalons;++K)
                for(int32 I=0;I<TrailSamples;++I)
                {
                    const FVector3f& C=Centers[K][I];
                    const FVector3f D=Centers[K][FMath::Min(I+1,TrailSamples-1)]-Centers[K][FMath::Max(I-1,0)];
                    FVector3f Across=FVector3f::CrossProduct(D,(C-CameraLocal).GetSafeNormal()); // face the camera
                    Across=Across.SizeSquared()>1.e-6f?Across.GetUnsafeNormal():FVector3f(0.f,0.f,1.f);
                    // Slit outline: widest mid-path, pointed at both ends; pinky and thumb scars slimmer.
                    const float Profile=FMath::Pow(FMath::Sin(PI*I/(TrailSamples-1)),.6f);
                    const FVector3f Half=Across*(.5f*Rift.Width*Profile*(K==0?.8f:(K==4?.7f:1.f)));
                    const int32 V=(K*TrailSamples+I)*2;
                    Edit.SetVertex(V,FVector3d(C+Half));Edit.SetVertex(V+1,FVector3d(C-Half));
                }
        },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
        AzureDragonRiftMIDs[Slot]->SetScalarParameterValue(TEXT("Age"),FMath::Fmod(Now+Slot*7.f,600.f));
        AzureDragonRiftMIDs[Slot]->SetScalarParameterValue(TEXT("Dissolve"),bCutting?0.f:FMath::Clamp((Since-RiftHold)/RiftDissolve,0.f,1.f));
        Mesh->SetVisibility(true);
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
