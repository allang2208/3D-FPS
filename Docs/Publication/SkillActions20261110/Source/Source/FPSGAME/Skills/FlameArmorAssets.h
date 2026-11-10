#pragma once
#include "CoreMinimal.h"

namespace FlameArmorAssets
{
inline constexpr const TCHAR* Body=TEXT("/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmorBodyV2.NS_FlameArmorBodyV2");
inline constexpr const TCHAR* Weapon=TEXT("/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon.NS_FlameArmorWeapon");
inline constexpr const TCHAR* Hammer=TEXT("/Game/Skills/FlameArmor20261109/HammerSurfaceV13/NS_FlameArmorHammer.NS_FlameArmorHammer");
// The warm donor keeps the original charge structure; the fitted copy follows
// each installed blade's measured width/curvature, including narrow swords.
inline constexpr const TCHAR* Sword=Weapon;
inline constexpr const TCHAR* Arrow=Weapon;
}
