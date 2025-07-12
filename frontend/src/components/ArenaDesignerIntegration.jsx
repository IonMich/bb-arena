import React from 'react';
import ArenaDesigner from './ArenaDesigner';

/**
 * ArenaDesignerIntegration - Archived component for future use
 * 
 * This component was temporarily removed from ArenaDetailView but preserved here
 * for potential future integration. It shows how ArenaDesigner was embedded
 * with readonly mode, attendance data, and known capacities.
 */
const ArenaDesignerIntegration = ({ 
  selectedSnapshot, 
  selectedGame, 
  getEffectiveCapacities 
}) => {
  if (!selectedSnapshot) return null;

  return (
    <div className="arena-designer-integration">
      <h3>Arena Designer (Archived)</h3>
      <ArenaDesigner 
        initialSeatCounts={{
          courtside: selectedSnapshot.courtside_capacity,
          lowerTierTotal: selectedSnapshot.lower_tier_capacity,
          luxuryBoxCount: selectedSnapshot.luxury_boxes_capacity,
        }}
        readonly={true}
        attendanceData={selectedGame?.attendance}
        knownCapacities={selectedGame ? getEffectiveCapacities() : null}
      />
    </div>
  );
};

export default ArenaDesignerIntegration;
