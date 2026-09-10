#include "ColdSteelHUDWidget.h"

// The original shell audit now routes through the live inventory/progression acceptance.
void UColdSteelHUDWidget::RunUpgradeAudit()
{
    RunInventoryAudit();
}
