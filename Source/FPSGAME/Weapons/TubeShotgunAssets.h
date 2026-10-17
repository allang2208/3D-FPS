#pragma once
#include "Super90WeaponAssets.h"
#include "M870WeaponAssets.h"

// The existing per-shell authority/receipt protocol is shared; each weapon
// keeps its own mesh, animation, mechanical clock and attachment definitions.
namespace TubeShotgunAssets
{
inline bool Supports(const FString& Definition)
{return Definition==Super90WeaponAssets::Definition||Definition==M870WeaponAssets::Definition;}
inline bool Supports(FName Definition)
{return Definition==FName(Super90WeaponAssets::Definition)||Definition==FName(M870WeaponAssets::Definition);}
inline bool MatchesMesh(const FString& Path)
{return Path==Super90WeaponAssets::MeshPath||Path==M870WeaponAssets::MeshPath;}
inline double MinimumInterval(const FString& Definition)
{return Definition==M870WeaponAssets::Definition?M870WeaponAssets::MinimumAttackInterval:Super90WeaponAssets::MinimumAttackInterval;}
}
