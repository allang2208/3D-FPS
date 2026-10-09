#include "WeaponActionCameraComponent.h"
#include "Camera/CameraComponent.h"
#include "HAL/IConsoleManager.h"

// Live strength dial for the reload/equip camera layer. The pose keys below stay
// the authored source motion; this only scales the offsets handed to the camera.
// Shot feedback has its own dial (fps.Camera.Shake).
static TAutoConsoleVariable<float> ActionShakeScale(TEXT("fps.Camera.ActionShake"),1.f,
    TEXT("Multiplier on the reload/equip camera shake. 1 = authored base."));

namespace WeaponActionCamera
{
struct FPose
{
    FVector Angles = FVector::ZeroVector; // Pitch, yaw, roll in degrees.
    FVector Position = FVector::ZeroVector; // Forward, right, up in centimetres.
};

struct FKey
{
    float Time;
    FVector Angles;
    FVector Position;
};

template <SIZE_T N>
FPose Curve(const FKey (&Keys)[N], float Time)
{
    for (SIZE_T I = 1; I < N; ++I)
    {
        if (Time <= Keys[I].Time)
        {
            const float Alpha = FMath::SmoothStep(Keys[I - 1].Time, Keys[I].Time, Time);
            return {FMath::Lerp(Keys[I - 1].Angles, Keys[I].Angles, Alpha),
                FMath::Lerp(Keys[I - 1].Position, Keys[I].Position, Alpha)};
        }
    }
    return {Keys[N - 1].Angles, Keys[N - 1].Position};
}

void Impact(FPose& Pose, float Time, float Contact, float Duration,
    const FVector& Angles, const FVector& Position)
{
    const float Age = (Time - Contact) / Duration;
    if (Age <= 0.f || Age >= 1.f) return;
    // Give the contact time to register: push, briefly hold its weight, then
    // counter-swing and settle. Sample the source clock without accumulating.
    const float Times[] = {0.f, .23f, .37f, .72f, 1.f};
    const float Values[] = {0.f, 1.f, .82f, -.24f, 0.f};
    float Wave = 0.f;
    for (int32 I = 1; I < UE_ARRAY_COUNT(Times); ++I)
        if (Age <= Times[I])
        {
            Wave = FMath::Lerp(Values[I - 1], Values[I], FMath::SmoothStep(Times[I - 1], Times[I], Age));
            break;
        }
    Pose.Angles += Angles * Wave;
    Pose.Position += Position * Wave;
}

void Reload(float Time, float End, TConstArrayView<float> Contacts,
    bool bEmpty, bool bDrum, bool bAsh12, FPose& Follow, FPose& Impacts)
{
    if (Contacts.Num() < (bEmpty ? (bAsh12 ? 5 : 4) : 3)) return;
    // These are the same source seconds that trigger mechanical audio. The
    // caller has already applied the drum's nonlinear source-time mapping.
    const float Out = Contacts[0], Insert = Contacts[1], Seat = Contacts[2];
    const float Lift = bDrum ? .7f : 1.f;
    if (bAsh12)
    {
        // Reference: the receiver rolls independently of the background.
        // Keep reload roll at zero; show weight through pitch and short travel.
        // These source values still pass through the project's shared gains.
        if (bEmpty)
        {
            const float Pull = Contacts[3], Release = Contacts[4];
            const FKey Keys[] = {
                {0.f, {}, {}},
                {Out - .12f, {.25f, .05f, 0.f}, {-.10f, 0.f, -.10f}},
                {Out + .08f, {-.20f, -.12f, 0.f}, {.10f, -.12f, -.20f}},
                {Out + .38f, {}, {}},
                {Insert - .16f, {.14f, .08f, 0.f}, {-.08f, .05f, -.08f}},
                {Insert + .05f, {-.18f, .04f, 0.f}, {-.10f, .05f, .10f}},
                {Seat + .15f, {.60f, .10f, 0.f}, {-.12f, 0.f, .10f}},
                // The reference raises the view as the right hand reaches
                // over the receiver, then settles after letting go of the handle.
                {Pull - .06f, {1.90f, .20f, 0.f}, {-.24f, -.10f, .12f}},
                {Release, {2.10f, .12f, 0.f}, {-.30f, -.08f, .15f}},
                {Release + .18f, {.45f, -.08f, 0.f}, {.05f, .02f, -.05f}},
                {FMath::Min(Release + .44f, End - .02f), {}, {}},
                {End, {}, {}}
            };
            Follow = Curve(Keys, Time);
            Impact(Impacts, Time, Pull, Release - Pull,
                {.35f, -.06f, 0.f}, {-.18f, .02f, .04f});
            Impact(Impacts, Time, Release, FMath::Min(.34f, End - Release),
                {-1.25f, .14f, 0.f}, {.25f, .03f, -.16f});
        }
        else
        {
            // Same magazine beats, then a direct return without the charge lift.
            const FKey Keys[] = {
                {0.f, {}, {}},
                {Out - .12f, {.25f, .05f, 0.f}, {-.10f, 0.f, -.10f}},
                {Out + .08f, {-.20f, -.12f, 0.f}, {.10f, -.12f, -.20f}},
                {Out + .38f, {}, {}},
                {Insert - .16f, {.14f, .08f, 0.f}, {-.08f, .05f, -.08f}},
                {Insert + .05f, {-.18f, .04f, 0.f}, {-.10f, .05f, .10f}},
                {Seat + .08f, {.20f, -.06f, 0.f}, {-.10f, 0.f, .08f}},
                {FMath::Min(Seat + .35f, End - .02f), {}, {}},
                {End, {}, {}}
            };
            Follow = Curve(Keys, Time);
        }
        // Let each contact recover before the next. The magazine retrieval
        // interval is quiet; seating and bolt release have separate rebounds.
        Impact(Impacts, Time, Out, .34f, {-.55f, .12f, 0.f}, {.12f, -.10f, -.10f});
        Impact(Impacts, Time, Insert, .20f, {-.35f, -.08f, 0.f}, {-.10f, .04f, .16f});
        Impact(Impacts, Time, Seat, FMath::Min(.32f, End - Seat), {1.10f, .06f, 0.f}, {-.24f, 0.f, .20f});
        return;
    }
    if (bEmpty)
    {
        const float Bolt = Contacts[3];
        const FKey Keys[] = {
            {0.f, {}, {}},
            {Out - .12f, {-.45f, -.20f, -.75f}, {-.18f, -.10f, -.12f}},
            {Out + .14f, {-.90f, .55f, 2.60f * Lift}, {.30f, -.45f, -.28f}},
            {Out + .40f, {-.32f, .30f, .85f}, {-.12f, -.20f, -.14f}},
            {Insert - .10f, {-.65f, -.20f, -.70f}, {-.22f, .12f, -.24f}},
            {Insert + .07f, {-.28f, .18f, .85f}, {-.30f, .14f, .18f}},
            {Seat + .12f, {.70f, .12f, -.65f}, {-.38f, 0.f, .32f}},
            {Bolt - .24f, {.85f, -.40f, -1.10f}, {-.40f, .16f, .22f}},
            {Bolt + .12f, {-.85f, .30f, .90f}, {.14f, -.12f, -.20f}},
            {FMath::Min(Bolt + .34f, End - .02f), {-.16f, .06f, .20f}, {}},
            {End, {}, {}}
        };
        Follow = Curve(Keys, Time);
        Impact(Impacts, Time, Bolt, FMath::Min(.48f, End - Bolt), {-2.30f, .40f, 1.40f}, {-.70f, .10f, -.30f});
    }
    else
    {
        const FKey Keys[] = {
            {0.f, {}, {}},
            {Out - .12f, {-.45f, -.20f, -.75f}, {-.18f, -.10f, -.12f}},
            {Out + .14f, {-.90f, .55f, 2.60f * Lift}, {.30f, -.45f, -.28f}},
            {Out + .40f, {-.32f, .30f, .85f}, {-.12f, -.20f, -.14f}},
            {Insert - .10f, {-.65f, -.20f, -.70f}, {-.22f, .12f, -.24f}},
            {Insert + .07f, {-.28f, .18f, .85f}, {-.30f, .14f, .18f}},
            {Seat + .12f, {.70f, .12f, -.65f}, {-.38f, 0.f, .32f}},
            {Seat + .36f, {-.14f, .04f, .14f}, {}},
            {End, {}, {}}
        };
        Follow = Curve(Keys, Time);
    }
    Impact(Impacts, Time, Out, bDrum ? .65f : .55f,
        {-1.f, .55f, bDrum ? 2.20f : 2.80f}, {.30f, -.45f, -.25f});
    Impact(Impacts, Time, Insert, .36f, {-.70f, -.24f, -1.f}, {-.35f, .14f, .50f});
    Impact(Impacts, Time, Seat, FMath::Min(.48f, End - Seat),
        {bDrum ? 2.40f : 2.f, .15f, -1.25f}, {-.65f, 0.f, .55f});
}

void ReloadPKM(float Time, float End, TConstArrayView<float> Contacts,
    bool bEmpty, FPose& Follow, FPose& Impacts, bool bChargeTail = true)
{
    // The 201 cloth box shares this belt-box profile without a charging tail:
    // {open, [belt lift,] box out, box insert, belt seat, cover close}.
    if (Contacts.Num() < (bEmpty ? (bChargeTail ? 9 : 5) : 6)) return;
    // PKM's audio queue omits the old-belt lift when empty. Consume its source
    // seconds directly so Reload16's cut and gameplay reload speed stay shared.
    const int32 BoxIndex = bEmpty ? 1 : 2;
    const float Open = Contacts[0], Out = Contacts[BoxIndex];
    const float Insert = Contacts[BoxIndex + 1], BeltSeat = Contacts[BoxIndex + 2];
    const float Close = Contacts[BoxIndex + 3];
    // Reuse M4's actual normal-reload follow and impulses at full strength:
    // magazine out -> box out, insert -> box insert, seat -> cover latch.
    // Empty PKM adds its own two-contact charge below, not M4's bolt slap.
    const float M4Contacts[] = {Out, Insert, Close};
    Reload(Time, End, MakeArrayView(M4Contacts), false, false, false, Follow, Impacts);
    Impact(Impacts, Time, Open, .34f, {.55f, -.12f, 0.f}, {-.12f, -.10f, .10f});
    if (!bEmpty)
        Impact(Impacts, Time, Contacts[1], .26f, {.35f, -.08f, 0.f}, {0.f, -.10f, .08f});
    Impact(Impacts, Time, BeltSeat, .20f, {-.35f, .08f, 0.f}, {.10f, .04f, -.16f});
    if (bEmpty && bChargeTail)
    {
        const float Pull = Contacts[5], Rear = Contacts[6];
        const float Push = Contacts[7], Front = Contacts[8];
        const FKey ChargeKeys[] = {
            {0.f, {}, {}},
            {Pull - .20f, {}, {}},
            {Pull, {.35f, .04f, 0.f}, {-.05f, -.02f, .03f}},
            {Rear, {2.10f, .12f, 0.f}, {-.30f, -.08f, .15f}},
            {Push, {2.10f, .12f, 0.f}, {-.30f, -.08f, .15f}},
            {Front, {-.75f, -.08f, 0.f}, {.16f, .03f, -.08f}},
            {Front + .18f, {.15f, .02f, 0.f}, {-.03f, 0.f, .02f}},
            {FMath::Min(Front + .44f, End - .02f), {}, {}},
            {End, {}, {}}
        };
        const FPose Charge = Curve(ChargeKeys, Time);
        Follow.Angles += Charge.Angles;
        Follow.Position += Charge.Position;
        // Keep the ASH-12-sized feedback, but follow Charge34's two deliberate
        // directions: rear stop, held push forward, then the front-stop click.
        Impact(Impacts, Time, Rear, Push - Rear,
            {.35f, -.06f, 0.f}, {-.18f, .02f, .04f});
        Impact(Impacts, Time, Front, FMath::Min(.34f, End - Front),
            {-1.25f, .14f, 0.f}, {.25f, .03f, -.16f});
    }
}

void EquipPKM(float Time, float End, FPose& Follow, FPose& Impacts)
{
    // EquipCharge31: open left hand catches at .39 s; the .90 s clip lowers
    // into support at .64 s and settles by .86 s. Map M4's equip amplitudes
    // and contact responses to these beats; there is no PKM equip bolt pull.
    const float ClockScale = End / .90f;
    const FKey Keys[] = {
        {0.f, {}, {}},
        {.16f * ClockScale, {-.32f, -.18f, -.55f}, {-.12f, 0.f, -.10f}},
        {.30f * ClockScale, {.65f, -.32f, -.90f}, {-.35f, .08f, .18f}},
        {.39f * ClockScale, {1.25f, -.40f, -1.10f}, {-.65f, .12f, .28f}},
        {.64f * ClockScale, {-.75f, .24f, .65f}, {.10f, -.08f, -.12f}},
        {.77f * ClockScale, {-.14f, .04f, .14f}, {}},
        {.86f * ClockScale, {}, {}},
        {End, {}, {}}
    };
    Follow = Curve(Keys, Time);
    Impact(Impacts, Time, .39f * ClockScale, .22f * ClockScale,
        {1.20f, -.30f, -.85f}, {-.48f, 0.f, .12f});
    Impact(Impacts, Time, .64f * ClockScale, .26f * ClockScale,
        {-2.25f, .32f, 1.20f}, {.38f, 0.f, -.38f});
}

void ReloadRSH12(float Time, float End, TConstArrayView<float> Contacts,
    bool bEmpty, FPose& Follow, FPose& Impacts)
{
    if (Contacts.Num() < 3) return;
    const float Open = Contacts[0], Eject = Contacts[1], Close = Contacts[2];
    // BV1vh4HejEUF opening flick: anticipate, sharp lateral/downward kick,
    // counter-swing, then settle. Keep the native 715 arms untouched. These
    // small camera offsets pass through the shared follow/impact gains below.
    const FKey Keys[] = {
        {0.f, {}, {}},
        {Open - .16f, {.03f, -.015f, -.03f}, {-.02f, .02f, .015f}},
        {Open - .035f, {.09f, -.03f, -.07f}, {-.04f, .04f, .025f}},
        {Open + .05f, {-.08f, .04f, .10f}, {.015f, -.035f, -.025f}},
        {Open + .28f, {}, {}},
        {Close - .10f, {-.03f, .02f, .03f}, {}},
        {Close + .10f, {.04f, -.02f, -.04f}, {}},
        {End, {}, {}}
    };
    Follow = Curve(Keys, Time);
    Impact(Impacts, Time, Open - .02f, .24f,
        {-.17f, .08f, .21f}, {.04f, -.065f, -.045f});
    if (bEmpty)
        Impact(Impacts, Time, Eject, .18f,
            {-.065f, -.018f, -.035f}, {-.025f, .015f, -.03f});
    Impact(Impacts, Time, Close, FMath::Min(.23f, End - Close),
        {.105f, -.035f, -.13f}, {-.025f, .025f, .035f});
}

void Equip(float Time, float End, FPose& Follow, FPose& Impacts)
{
    // Current M4WrapGrip source: handle begins moving at frame 15, reaches its
    // rear stop at 18 and returns closed at 22 (60 fps, 38-frame source clip).
    const FKey Keys[] = {
        {0.f, {}, {}},
        {9.f / 60.f, {-.32f, -.18f, -.55f}, {-.12f, 0.f, -.10f}},
        {15.f / 60.f, {.65f, -.32f, -.90f}, {-.35f, .08f, .18f}},
        {18.f / 60.f, {1.25f, -.40f, -1.10f}, {-.65f, .12f, .28f}},
        {22.f / 60.f, {-.75f, .24f, .65f}, {.10f, -.08f, -.12f}},
        {31.f / 60.f, {-.14f, .04f, .14f}, {}},
        {End, {}, {}}
    };
    Follow = Curve(Keys, Time);
    Impact(Impacts, Time, 18.f / 60.f, .22f, {1.20f, -.30f, -.85f}, {-.48f, 0.f, .12f});
    Impact(Impacts, Time, 22.f / 60.f, .26f, {-2.25f, .32f, 1.20f}, {.38f, 0.f, -.38f});
}

void Super90Loader(float Time, float End, TConstArrayView<float> Contacts,
    bool bEmpty, bool bCycle, FPose& Follow, FPose& Impacts)
{
    if (Contacts.Num() < 3) return;
    const float Dock = Contacts[0], LastShell = Contacts[1], Bolt = Contacts[2];
    // The whole supported gun already carries the authored pressure movement.
    // The head follows lightly; contacts add one short response, not a shake
    // for every cartridge or an impulse selected by the sound queue index.
    if (!bCycle)
    {
        const float Return = LastShell + (bEmpty ? 49.f : 2.f) / 60.f;
        const float Lift = FMath::SmoothStep(5.f / 60.f, 30.f / 60.f, Time)
            * (1.f - FMath::SmoothStep(Return, End, Time));
        const float Pressure = FMath::SmoothStep(Dock, 114.f / 60.f, Time)
            * (1.f - FMath::SmoothStep(LastShell, LastShell + 7.f / 60.f, Time));
        Follow.Angles = FVector(-.025f, -.015f, .085f) * Lift
            + FVector(.025f, 0.f, -.02f) * Pressure;
        Follow.Position = FVector(-.018f, -.012f, -.008f) * Lift;
        Impact(Impacts, Time, Dock, .14f,
            {-.025f, .006f, -.035f}, {-.009f, .003f, .006f});
        Impact(Impacts, Time, LastShell, .16f,
            {.045f, -.008f, .025f}, {-.012f, 0.f, .009f});
    }
    if (bEmpty)
        Impact(Impacts, Time, Bolt, FMath::Min(.18f, End - Bolt),
            {-.07f, .008f, .035f}, {.014f, .003f, -.008f});
}
}

UWeaponActionCameraComponent::UWeaponActionCameraComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UWeaponActionCameraComponent::ResetSprint()
{
    SprintBlend = SprintPhase = 0.f;
}

void UWeaponActionCameraComponent::UpdateSprint(float DeltaSeconds, bool bEnabled,
    bool bRequested, float StridePhase, float MovementWeight)
{
    if (!bEnabled)
    {
        ResetSprint();
        return;
    }
    const float Target = bRequested ? FMath::Clamp(MovementWeight, 0.f, 1.f) : 0.f;
    const float Rate = Target > SprintBlend ? 9.f : 6.f;
    SprintBlend = FMath::Lerp(SprintBlend, Target,
        1.f - FMath::Exp(-Rate * FMath::Max(DeltaSeconds, 0.f)));
    // The footstep clock continues through walk/run reversals. Fade amplitude
    // without restarting the wave when sprint is pressed or released.
    SprintPhase = StridePhase;
}

void UWeaponActionCameraComponent::Apply(UCameraComponent& Camera, EM4CameraAction Action,
    float SourceSeconds, float SourceDuration, TConstArrayView<float> ContactSeconds,
    float CameraMotionWeight) const
{
    // Rebuild this layer once per camera update; never add onto last frame.
    // No other FPSGAME system currently owns CameraComponent's additive offset.
    Camera.ClearAdditiveOffset();
    const float Weight = FMath::Clamp(Strength, 0.f, 4.f) * FMath::Max(0.f, CameraMotionWeight)
        * FMath::Max(0.f, ActionShakeScale.GetValueOnGameThread());
    if (CameraMotionWeight <= 0.f) return;

    WeaponActionCamera::FPose Follow, Impacts;
    if (Action != EM4CameraAction::None && Weight > 0.f && SourceDuration > 0.f)
    {
        const float Time = FMath::Clamp(SourceSeconds, 0.f, SourceDuration);
        if (Action == EM4CameraAction::Super90Loader || Action == EM4CameraAction::Super90LoaderEmpty
            || Action == EM4CameraAction::Super90LoaderCycle)
            WeaponActionCamera::Super90Loader(Time, SourceDuration, ContactSeconds,
                Action != EM4CameraAction::Super90Loader, Action == EM4CameraAction::Super90LoaderCycle,
                Follow, Impacts);
        else if (Action == EM4CameraAction::RSH12Reload || Action == EM4CameraAction::RSH12ReloadEmpty)
            WeaponActionCamera::ReloadRSH12(Time, SourceDuration, ContactSeconds,
                Action == EM4CameraAction::RSH12ReloadEmpty, Follow, Impacts);
        else if (Action == EM4CameraAction::PKMEquip)
            WeaponActionCamera::EquipPKM(Time, SourceDuration, Follow, Impacts);
        else if (Action == EM4CameraAction::PKMReload || Action == EM4CameraAction::PKMReloadEmpty)
            WeaponActionCamera::ReloadPKM(Time, SourceDuration, ContactSeconds,
                Action == EM4CameraAction::PKMReloadEmpty, Follow, Impacts);
        else if (Action == EM4CameraAction::LMG201ClothReload || Action == EM4CameraAction::LMG201ClothReloadEmpty)
            WeaponActionCamera::ReloadPKM(Time, SourceDuration, ContactSeconds,
                Action == EM4CameraAction::LMG201ClothReloadEmpty, Follow, Impacts, false);
        else if (Action == EM4CameraAction::EquipCharge)
            WeaponActionCamera::Equip(Time, SourceDuration, Follow, Impacts);
        else
            WeaponActionCamera::Reload(Time, SourceDuration, ContactSeconds,
                Action == EM4CameraAction::ReloadEmpty || Action == EM4CameraAction::DrumReloadEmpty
                    || Action == EM4CameraAction::Ash12ReloadEmpty,
                Action == EM4CameraAction::DrumReload || Action == EM4CameraAction::DrumReloadEmpty,
                Action == EM4CameraAction::Ash12Reload || Action == EM4CameraAction::Ash12ReloadEmpty,
                Follow, Impacts);
    }

    const float FollowScale = FMath::Clamp(FollowStrength, 0.f, 2.f);
    const float ImpactScale = FMath::Clamp(ImpactStrength, 0.f, 2.f);
    FVector Angles = (Follow.Angles * FollowScale + Impacts.Angles * ImpactScale) * Weight;
    FVector Position = (Follow.Position * FollowScale + Impacts.Position * ImpactScale) * Weight;
    const float RunWeight = SprintBlend * FMath::Clamp(SprintStrength, 0.f, 3.f) * CameraMotionWeight;
    const float Side = FMath::Cos(SprintPhase);
    const float Step = FMath::Cos(2.f * SprintPhase);
    // A broad stride plus a rounded footfall pulse, with its mean removed so
    // repeated steps do not bias camera height or pitch.
    const float Contact = FMath::Pow(FMath::Max(0.f, Step), 3.f) - 2.f / (3.f * PI);
    Angles += FVector(-SprintAnglesDegrees.X * (Step + .28f * Contact),
        SprintAnglesDegrees.Y * FMath::Sin(SprintPhase), SprintAnglesDegrees.Z * Side) * RunWeight;
    Position += FVector(-SprintTravelCM.X * Step, SprintTravelCM.Y * Side,
        -SprintTravelCM.Z * (Step + .25f * Contact)) * RunWeight;
    const FRotator Rotation(Angles.X, Angles.Y, Angles.Z);
    // GetCameraView applies this after reading the component transform, leaving
    // ControlRotation, sight sockets and shot traces untouched by this layer.
    Camera.AddAdditiveOffset(FTransform(Rotation.Quaternion(), Position), 0.f);
}
