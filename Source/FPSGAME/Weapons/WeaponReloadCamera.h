#pragma once
#include "CoreMinimal.h"

enum class EM4CameraAction : uint8;
enum class EReloadCameraContact : uint8
{
    MagazineOut,Insert,Seat,Pull,Release,CoverOpen,Belt,CoverClose,CylinderOpen,Eject,Round,CylinderClose
};
struct FReloadCameraContact
{
    float Time=0.f;
    EReloadCameraContact Kind=EReloadCameraContact::Insert;
};
struct FWeaponReloadCameraTrack
{
    float Time=0.f,End=0.f,Begin=0.f,FamilyScale=1.f;
    int32 Hand=0;
    EM4CameraAction FollowAction=static_cast<EM4CameraAction>(0);
    TArray<float,TInlineAllocator<12>> FollowContacts;
    TArray<FReloadCameraContact,TInlineAllocator<16>> Contacts;
    void Add(float At,EReloadCameraContact Kind)
    {if(At>=Begin-.0001f&&At<End)Contacts.Add({At,Kind});}
};
using FWeaponReloadCameraTracks=TArray<FWeaponReloadCameraTrack,TInlineAllocator<2>>;

namespace WeaponReloadCamera
{
    // Shared cm/degree contract before the player's existing CameraMotionScale.
    inline constexpr float PistolScale=.8f,RifleScale=1.f,HeavyScale=1.1f;
    inline constexpr float FollowScale=.35f,CancelSeconds=.10f;
    inline const FVector AngleLimit(3.f,1.5f,1.5f); // pitch/yaw/roll
    inline constexpr float TravelLimit=.85f;
    struct FBeat {FVector Angles,Position;float Seconds;};
    inline FBeat Beat(EReloadCameraContact Kind)
    {
        switch(Kind)
        {
        case EReloadCameraContact::MagazineOut:return {{-.65f,.12f,.35f},{.12f,-.12f,-.06f},.22f};
        case EReloadCameraContact::Insert:return {{-.75f,-.08f,-.22f},{-.12f,.04f,.12f},.18f};
        case EReloadCameraContact::Seat:return {{1.25f,.04f,-.28f},{-.22f,0.f,.18f},.24f};
        case EReloadCameraContact::Pull:return {{.65f,-.08f,0.f},{-.16f,.02f,.04f},.22f};
        case EReloadCameraContact::Release:return {{-1.65f,.12f,.20f},{.24f,.02f,-.16f},.22f};
        case EReloadCameraContact::CoverOpen:return {{.6f,-.12f,.15f},{-.12f,-.06f,.08f},.22f};
        case EReloadCameraContact::Belt:return {{-.45f,.08f,0.f},{.08f,.04f,-.08f},.18f};
        case EReloadCameraContact::CoverClose:return {{1.4f,.05f,-.3f},{-.22f,0.f,.18f},.24f};
        case EReloadCameraContact::CylinderOpen:return {{-.8f,.18f,.6f},{.06f,-.14f,-.10f},.22f};
        case EReloadCameraContact::Eject:return {{-.5f,-.06f,-.1f},{-.10f,.03f,-.08f},.18f};
        case EReloadCameraContact::Round:return {{.45f,.02f,-.08f},{-.07f,0.f,.06f},.16f};
        case EReloadCameraContact::CylinderClose:return {{1.1f,-.08f,-.45f},{-.12f,.06f,.12f},.22f};
        }
        return {{},{},.2f};
    }
}
