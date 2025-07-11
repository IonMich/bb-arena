import React, { useState } from 'react';
import './ArenaDesigner.css';
import CourtOutline from './court/CourtOutline';
import CenterCourt from './court/CenterCourt';
import FreeThrowLanes from './court/FreeThrowLanes';
import BasketAndBackboard from './court/BasketAndBackboard';
import ThreePointLine from './court/ThreePointLine';
import CourtsideSeating from './court/CourtsideSeating';
import LowerTierSeating from './court/LowerTierSeating';
import LuxuryBoxes from './court/LuxuryBoxes';

const ArenaDesigner = ({ 
  initialSeatCounts, 
  readonly = false, 
  attendanceData = null, 
  knownCapacities = null 
}) => {
  // State for seat counts
  const [seatCounts, setSeatCounts] = useState(
    initialSeatCounts || {
      courtside: 500, // total courtside seats (50-500)
      lowerTierTotal: 1920, // total seats across all 16 sections
      luxuryBoxCount: 50, // number of luxury boxes (10-50)
    }
  );

  // Functions to update seat counts
  const updateSeatCount = (section, value) => {
    setSeatCounts(prev => ({
      ...prev,
      [section]: Math.max(1, parseInt(value) || 1)
    }));
  };

  // Calculate seat distribution
  const seatsPerLowerTierSection = Math.floor(seatCounts.lowerTierTotal / 16);
  const remainingSeats = seatCounts.lowerTierTotal % 16;
  // NBA court dimensions in feet
  const NBA_LENGTH = 94;
  const NBA_WIDTH = 50;
  const FREE_THROW_LANE_WIDTH = 16;
  const FREE_THROW_LANE_LENGTH = 19;
  const CENTER_CIRCLE_RADIUS = 6;
  const FREE_THROW_CIRCLE_RADIUS = 6;
  const BASKET_INNER_DIAMETER = 18; // inches
  const BACKBOARD_WIDTH = 72; // inches
  const BACKBOARD_DISTANCE_FROM_BASELINE = 4; // feet
  const BASKET_DISTANCE_FROM_BASELINE = BACKBOARD_DISTANCE_FROM_BASELINE + BASKET_INNER_DIAMETER / 12 / 2; // feet
  const BUFFER_ZONE = 4; // 4 feet buffer around the court
  const COURTSIDE_SEATING_WIDTH = 10; // 10 feet wide seating area
  const LOWER_TIER_SEATING_WIDTH = 30; // 30 feet wide lower tier seating area
  const LUXURY_BOX_DEPTH = 4; // 4 feet deep luxury boxes (reduced from 8 feet)
  const LUXURY_BOX_GAP = 4; // 4 feet gap between lower-tier and luxury boxes
  const COURTSIDE_ROWS = 5;
  const ROW_DEPTH = 2; // 2 feet per row
  
  // Scale factor to make it fit nicely on screen (1 foot = 8 pixels)
  const SCALE = 4;
  const LINE_THICKNESS = 2; // 2 inches thick lines
  
  // Calculated dimensions
  const courtLength = NBA_LENGTH * SCALE;
  const courtWidth = NBA_WIDTH * SCALE;
  const bufferSize = BUFFER_ZONE * SCALE;
  const seatingDepth = COURTSIDE_SEATING_WIDTH * SCALE;
  const lowerTierDepth = LOWER_TIER_SEATING_WIDTH * SCALE;
  const luxuryBoxDepth = LUXURY_BOX_DEPTH * SCALE;
  const luxuryBoxGap = LUXURY_BOX_GAP * SCALE;
  
  // Total SVG dimensions including buffer, courtside seating, lower tier seating, luxury boxes, and gaps
  const totalWidth = courtLength + (2 * bufferSize) + (2 * seatingDepth) + (2 * lowerTierDepth);
  const totalHeight = courtWidth + (2 * bufferSize) + (2 * seatingDepth) + (2 * lowerTierDepth) + (2 * luxuryBoxDepth) + (2 * luxuryBoxGap);

  // Calculate total seats and capacity
  const totalLuxuryTickets = seatCounts.luxuryBoxCount; // 1 ticket per box
  const totalCapacity = seatCounts.courtside + seatCounts.lowerTierTotal + totalLuxuryTickets;
  
  return (
    <div className="arena-designer-container">
      <div className="arena-layout">
        {/* Seat Configuration Sidebar - only show if not readonly */}
        {!readonly && (
          <div className="seat-config-sidebar">
            <h3>Seat Configuration</h3>
            <div className="config-controls">
              <div className="config-group">
                <label htmlFor="courtside-seats">
                  Courtside Seating (Total):
                  <input
                    id="courtside-seats"
                    type="number"
                    min="1"
                    max="2000"
                    value={seatCounts.courtside}
                    onChange={(e) => updateSeatCount('courtside', e.target.value)}
                  />
                </label>
              </div>
              
              <div className="config-group">
                <label htmlFor="lower-tier-total">
                  Lower Tier (Total Seats):
                  <input
                    id="lower-tier-total"
                    type="number"
                    min="1000"
                    max="20000"
                    value={seatCounts.lowerTierTotal}
                    onChange={(e) => updateSeatCount('lowerTierTotal', e.target.value)}
                  />
                </label>
                <span className="section-info">Distributed across 16 sections (~{seatsPerLowerTierSection} per section)</span>
              </div>
              
              <div className="config-group">
                <label htmlFor="luxury-box-count">
                  Number of Luxury Boxes:
                  <input
                    id="luxury-box-count"
                    type="number"
                    min="10"
                    max="50"
                    value={seatCounts.luxuryBoxCount}
                    onChange={(e) => updateSeatCount('luxuryBoxCount', e.target.value)}
                  />
                </label>
                <span className="section-info">1 ticket per box = {totalLuxuryTickets} total tickets</span>
              </div>
              
              <div className="total-capacity">
                <strong>Total Arena Capacity: {totalCapacity.toLocaleString()}</strong>
              </div>
            </div>
          </div>
        )}

        {/* Main Court Area */}
        <div className={`court-main ${readonly ? 'full-width' : ''}`}>
          <div className="court-wrapper">
            <svg 
              width={totalWidth} 
              height={totalHeight}
              viewBox={`0 0 ${totalWidth} ${totalHeight}`}
              className="arena-court"
            >
          {/* Arena background including seating areas */}
          <rect
            x={0}
            y={0}
            width={totalWidth}
            height={totalHeight}
            fill="#6a6a6a"
            stroke="#888"
            strokeWidth={1}
          />
          
          {/* Buffer zone background */}
          <rect
            x={seatingDepth + lowerTierDepth}
            y={seatingDepth + lowerTierDepth + luxuryBoxDepth + luxuryBoxGap}
            width={courtLength + (2 * bufferSize)}
            height={courtWidth + (2 * bufferSize)}
            fill="#f5f5f5"
            stroke="#ccc"
            strokeWidth={1}
          />
          
          {/* Playing court background */}
          <rect
            x={seatingDepth + lowerTierDepth + bufferSize}
            y={seatingDepth + lowerTierDepth + luxuryBoxDepth + luxuryBoxGap + bufferSize}
            width={courtLength}
            height={courtWidth}
            fill="#d2b48c"
            stroke="none"
          />
          
          {/* Luxury boxes positioned above north and below south lower-tier seating */}
          <g transform={`translate(${lowerTierDepth}, ${lowerTierDepth + luxuryBoxDepth + luxuryBoxGap})`}>
            <LuxuryBoxes 
              courtLength={courtLength}
              courtWidth={courtWidth}
              scale={SCALE}
              bufferSize={bufferSize}
              totalBoxes={seatCounts.luxuryBoxCount}
              attendanceData={attendanceData}
            />
          </g>
          
          {/* Lower-tier seating positioned around the courtside area */}
          <g transform={`translate(${lowerTierDepth}, ${lowerTierDepth + luxuryBoxDepth + luxuryBoxGap})`}>
            <LowerTierSeating 
              courtLength={courtLength}
              courtWidth={courtWidth}
              scale={SCALE}
              bufferSize={bufferSize}
              luxuryBoxExpansion={0}
              seatsPerSection={seatsPerLowerTierSection}
              remainingSeats={remainingSeats}
              attendanceData={attendanceData}
            />
          </g>
          
          {/* Courtside seating positioned directly around the court (outside buffer zone) */}
          <g transform={`translate(${seatingDepth + lowerTierDepth}, ${seatingDepth + lowerTierDepth + luxuryBoxDepth + luxuryBoxGap})`}>
            <CourtsideSeating 
              courtLength={courtLength}
              courtWidth={courtWidth}
              scale={SCALE}
              bufferSize={bufferSize}
              maxSeats={seatCounts.courtside}
              attendanceData={attendanceData}
              knownCapacity={knownCapacities?.courtside}
            />
          </g>
          
          {/* All court components are offset by the seating depth, lower tier depth, luxury box depth, gap, and buffer size */}
          <g transform={`translate(${seatingDepth + lowerTierDepth + bufferSize}, ${seatingDepth + lowerTierDepth + luxuryBoxDepth + luxuryBoxGap + bufferSize})`}>
            <CourtOutline 
              courtLength={courtLength}
              courtWidth={courtWidth}
              lineThickness={LINE_THICKNESS}
            />            
            <CenterCourt 
              courtLength={courtLength}
              courtWidth={courtWidth}
              centerCircleRadius={CENTER_CIRCLE_RADIUS}
              scale={SCALE}
              lineThickness={LINE_THICKNESS}
            />
            
            <FreeThrowLanes 
              courtLength={courtLength}
              courtWidth={courtWidth}
              freeThrowLaneWidth={FREE_THROW_LANE_WIDTH}
              freeThrowLaneLength={FREE_THROW_LANE_LENGTH}
              freeThrowCircleRadius={FREE_THROW_CIRCLE_RADIUS}
              scale={SCALE}
              lineThickness={LINE_THICKNESS}
            />
            
            <ThreePointLine 
              courtLength={courtLength}
              courtWidth={courtWidth}
              basketDistanceFromBaseline={BASKET_DISTANCE_FROM_BASELINE}
              scale={SCALE}
              lineThickness={LINE_THICKNESS}
            />
            
            <BasketAndBackboard 
              courtLength={courtLength}
              courtWidth={courtWidth}
              basketInnerDiameter={BASKET_INNER_DIAMETER}
              backboardWidth={BACKBOARD_WIDTH}
              backboardDistanceFromBaseline={BACKBOARD_DISTANCE_FROM_BASELINE}
              scale={SCALE}
              lineThickness={LINE_THICKNESS}
            />
          </g>
        </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArenaDesigner;
