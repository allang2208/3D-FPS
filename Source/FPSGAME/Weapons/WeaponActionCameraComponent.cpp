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
    if (Contacts.Num() < (bEmpty ? 4 : 3)) return;
    // These are the same source seconds that trigger mechanical audio. The
    // caller has already applied the drum's nonlinear source-time mapping.
    const float Out = Contacts[0], Insert = Contacts[1], Seat = Contacts[2];
    const float Lift = bDrum ? .7f : 1.f;
    if (bAsh12)
    {
        // The bullpup choreography: the receiver rolls 36 degrees by frame 12,
        // holds 44-50 through the magazine swap, peaks 61 at the charge stroke
        // (frame 120) and settles by the end. The camera follows a slice of
        // that roll plus the tug toward the body, roughly twice the M4 layer,
        // because the ASH-12 never had any reload camera until now.
        if (bEmpty)
        {
            const float SwapMid = (Out + Insert) * .5f;
            const float ReachBolt = Seat + (Contacts[3] - Seat) * .30f;
            const FKey Keys[] = {
                {0.f, {}, {}},
                {.20f, {-.9f, .25f, -2.6f}, {.1f, -.5f, -.3f}},
                {Out + .05f, {-1.6f, .50f, -5.4f}, {.4f, -1.1f, -.7f}},
                {SwapMid, {-1.3f, .35f, -4.6f}, {.3f, -.9f, -1.0f}},
                {Insert + .05f, {-1.1f, -.2f, -4.9f}, {.2f, -.7f, -.8f}},
                {Seat + .10f, {.9f, .10f, -3.2f}, {-.2f, -.4f, .3f}},
                {ReachBolt, {-1.0f, .80f, -6.6f}, {.5f, -1.3f, -1.1f}},
                {Contacts[3] + .03f, {-1.5f, .55f, -6.0f}, {.7f, -1.1f, -.9f}},
                {FMath::Min(Contacts[3] + .30f, End - .02f), {.6f, -.15f, 1.6f}, {-.3f, .2f, .5f}},
                {End, {}, {}}
            };
            Follow = Curve(Keys, Time);
            Impact(Impacts, Time, Contacts[3], FMath::Min(.5f, End - Contacts[3]),
                {-3.4f, .60f, 2.2f}, {-1.05f, .15f, -.5f});
        }
        else
        {
            // Tactical: same roll, no charge stroke; the receiver is back
            // level shortly after the seat cue.
            const FKey Keys[] = {
                {0.f, {}, {}},
                {.30f, {-1.0f, .30f, -3.0f}, {.2f, -.7f, -.4f}},
                {Out + .05f, {-1.6f, .55f, -5.4f}, {.5f, -1.2f, -.8f}},
                {(Out + Insert) * .5f, {-1.3f, .40f, -4.8f}, {.4f, -1.0f, -1.0f}},
                {Insert + .05f, {-1.1f, -.2f, -4.9f}, {.3f, -.8f, -.8f}},
                {Seat + .10f, {.9f, .10f, -3.2f}, {-.2f, -.5f, .3f}},
                {FMath::Min(Seat + .40f, End - .02f), {-.3f, .05f, 1.0f}, {-.4f, 0.f, .4f}},
                {End, {}, {}}
            };
            Follow = Curve(Keys, Time);
        }
        // A 12.7 mm magazine and a heavy bullpup bolt hit harder than 5.56.
        // The swing durations stretch with the 2026-09-19 retimed (slower) beats.
        Impact(Impacts, Time, Out, .62f, {-1.4f, .70f, 3.4f}, {.45f, -.7f, -.35f});
        Impact(Impacts, Time, Insert, .44f, {-1.0f, -.35f, -1.5f}, {-.5f, .2f, .7f});
        Impact(Impacts, Time, Seat, FMath::Min(.55f, End - Seat), {3.2f, .20f, -1.8f}, {-.95f, 0.f, .8f});
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
        if (Action == EM4CameraAction::EquipCharge)
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
