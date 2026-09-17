#pragma once

#include "CoreMinimal.h"

/**
 * Explosion-driven terrain destruction for the heightfield worlds.
 *
 * The temperate hills world is the only terrain backend in the project: it lowers the
 * generated height inside a footprint and rebuilds just the affected streaming cells.
 * Levels without that world (the hub arena) return false, so their behaviour is unchanged.
 */
namespace TerrainDestruction
{
    /**
     * Carve an impact crater. Contact/Normal come from the hit; the heightfield only needs
     * the XY of the contact, so the normal is accepted for call-site symmetry.
     */
    bool CarveCrater(const UObject* WorldContext, const FVector& Contact, const FVector& Normal, float EffectRadiusCm);
}
