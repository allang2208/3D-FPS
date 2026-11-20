#pragma once

class AActor;

namespace HillsBakerySite
{
    void Apply(AActor& Site, bool bRepaired);
    bool IsOccupied(const AActor& Site);
}
