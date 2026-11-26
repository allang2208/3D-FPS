#pragma once
#include "CoreMinimal.h"
#include "AzureDragonReach.h"
namespace AzureDragonPresentation
{
// The library Fab Dragon Claw (V10.2+); ClawV10 keeps the original claw for recovery.
inline const FSoftObjectPath ClawPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Meshes/SK_AzureDragonClawFabV10.SK_AzureDragonClawFabV10"));
inline const FSoftObjectPath GrabPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Animations/A_AzureDragonClawFabRakeV10.A_AzureDragonClawFabRakeV10"));
inline const FSoftObjectPath AzureDragonMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawFabV10.M_AzureDragonClawFabV10"));
// V10.8: the five talon traces are rift scars after the game's Rift Slash (裂空) look, not flames.
inline const FSoftObjectPath TrailMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawRiftV10.M_AzureDragonClawRiftV10"));
inline const FSoftObjectPath FlameMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawFlameV10.M_AzureDragonClawFlameV10"));
// Two-sided opaque material for the unseen custom-depth follower (nearest face wins, no holes).
inline const FSoftObjectPath DepthMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawDepthV10.M_AzureDragonClawDepthV10"));
// All five talon points (pinky, ring, middle, index, thumb).
inline constexpr int32 RiftTalons=5;
inline const FName TipBones[RiftTalons]={TEXT("digit_01_tip"),TEXT("digit_02_tip"),TEXT("digit_03_tip"),TEXT("digit_04_tip"),TEXT("digit_05_tip")};
// Each rake leaves one scar per talon spanning its whole sweep path, widest in the middle and pointed at
// both ends; it holds after the rake, then erodes away. V10.9: wider and lingering longer.
inline constexpr int32 TrailSamples=32,RiftPathCap=128;
// V10.10: linger halved (hold .45 -> .225 s, dissolve .6 -> .3 s).
inline constexpr float RiftWidth=15.f,RiftHold=.225f,RiftDissolve=.3f; // cm per unit claw scale; seconds
// One big realistic flame per arm end: a rolling mass card and a rising-tongue card.
inline constexpr int32 FlameCards=2;
inline constexpr int32 ClawDepthStencil=214;             // custom-depth tag read by the claw glass
// V10.5 (2026-10-06): the claws live in WORLD space in front of the body (eye position + yaw,
// followed with inertia), so distance and height are real: looking up/down or turning shows
// where they are. They are built big instead: 5x the Fab claw (~4.6 m hand, ~6.3 m with arm).
// V10.7: 12 m out (was 8 m) and the palms ~5.9 m either side (was ~3.9 m): yaw 26 deg at 12 m.
// V10.11: scale and farthest station are shared with the gameplay reach (AzureDragonReach.h).
inline constexpr float ClawWorldScale=AzureDragonReach::ClawWorldScale;
inline constexpr float ClawIdleDistance=1200.f,ClawIdleYaw=26.f,ClawIdleHeight=-90.f; // cm / deg from the eye
// V10.10: negative = toe-out. V10.8's +20 deg (talons in, arms splayed) read as an inverted 八; now
// the forearms converge toward the player and the talons fan outward, a 八 opening ahead.
inline constexpr float ClawIdleToeIn=-20.f;
inline constexpr float AnchorFollowRate=8.f,AnchorTurnRate=9.f;                      // inertia (1/s)
inline const FVector ClawPalmLocal(8.,0.,0.);            // palm centre: the claws are placed by the palm
// V10.10: the gesture asset is the 0.6 s rake (frames 0-36) followed by a seamless 4 s idle loop.
inline constexpr float ClawGestureSeconds=.6f,ClawIdleLoopSeconds=4.f,ClawIdleDesync=1.7f;
// V10.12: ease over this long whenever a claw changes what it is doing; a heavy charge held past the
// tap window draws the claw back into its windup.
inline constexpr float ClawBlendSeconds=.18f,ClawChargeDelay=.2f;
// Own claws are hidden only by geometry this close (the material default); other players' copies by
// anything in front.
inline constexpr float NearOcclusionCM=350.f;
// V10.14 expiry: the claws erode along a wind-biased front over FrontSeconds (material Disintegrate
// = -FrontLead + FrontSpan * age / FrontSeconds) and blow away as motes born where the front passes.
// Budget: own claws 512 motes each, other players' 256 and none beyond 60 m; ~2.4 s, then hidden.
inline const FSoftObjectPath DustMaterialPath(TEXT("/Game/Weapons/AzureDragon20261004/ClawFab/Materials/M_AzureDragonClawDustV10.M_AzureDragonClawDustV10"));
inline constexpr int32 MotesPerClaw=512,RemoteMotesPerClaw=256;
inline constexpr float DissolveSeconds=2.4f,FrontSeconds=1.2f,FrontLead=.1f,FrontSpan=1.25f,RemoteMoteRangeCM=6000.f;
inline constexpr float WindSpeedCM=520.f,MoteTurbulence=420.f;
// V10.15: death plays the same dissolve faster so it finishes before the respawn replaces the pawn
// (UFPSCombatHealthComponent's 2 s respawn timer; keep in step if that changes).
inline constexpr float PlayerRespawnSeconds=2.f;
inline constexpr float DeathDissolveRate=FMath::Max(1.f,DissolveSeconds/(PlayerRespawnSeconds-.2f));
inline float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
// Horizontal sweep stations around the player for the RIGHT claw (the left mirrors the yaw):
// yaw from the body forward toward the claw's own side (deg), distance (cm), height (cm).
// Windup out wide and high, rake across the front, follow through low on the far side.
struct FSweepKey{float Yaw,Distance,Height;};
inline constexpr FSweepKey SweepKeys[4]={{50.f,1050.f,-10.f},{32.f,1185.f,-60.f},{-12.f,1200.f,-130.f},{-46.f,1095.f,-180.f}};
// V10.12: vertical strokes (overhead chop; uppercut / rising finisher use the heights reversed) rake
// through the forward line their hits cover, crossing it near the impact.
inline constexpr FSweepKey VerticalKeys[4]={{16.f,1000.f,420.f},{8.f,1170.f,260.f},{1.f,1200.f,-40.f},{-5.f,1120.f,-200.f}};
// The claw reach used for hit detection must cover the farthest palm station.
inline constexpr bool StationsWithinReach(const FSweepKey (&Keys)[4])
{for(const FSweepKey& Key:Keys)if(Key.Distance>AzureDragonReach::ClawStationMaxCM)return false;return true;}
static_assert(ClawIdleDistance<=AzureDragonReach::ClawStationMaxCM&&StationsWithinReach(SweepKeys)&&StationsWithinReach(VerticalKeys),
    "Azure Dragon claw station beyond the gameplay reach");
inline FVector Bezier2(const FVector& A,const FVector& B,const FVector& C,float T)
{const float U=1.f-T;return A*(U*U)+B*(2.f*U*T)+C*(T*T);}
inline FVector Bezier3(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
{const float U=1.f-T;return A*(U*U*U)+B*(3.f*U*U*T)+C*(3.f*U*T*T)+D*(T*T*T);}
inline FVector Bezier3Tangent(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
{const float U=1.f-T;return (B-A)*(3.f*U*U)+(C-B)*(6.f*U*T)+(D-C)*(3.f*T*T);}
}
