#pragma once
#include "CoreMinimal.h"

namespace FacilityHallPreparation
{
constexpr int32 MaxInstances = 16;
constexpr uint64 MaxEstimatedBytes = 256ull * 1024ull * 1024ull;
constexpr uint64 ReserveBytes = 1024ull * 1024ull * 1024ull;
// Admission stays conservative. Existing reservations have a separate reclaim
// band so small budget fluctuations do not destroy actors about to be activated.
constexpr uint64 ReclaimBelowBytes = 512ull * 1024ull * 1024ull;
constexpr uint64 ReclaimRecoveryBytes = 768ull * 1024ull * 1024ull;
constexpr uint64 CriticalReserveBytes = 128ull * 1024ull * 1024ull;
}
