import React from 'react';
import './BasketballCourt.css';
import CourtOutline from './court/CourtOutline';
import CenterCourt from './court/CenterCourt';
import FreeThrowLanes from './court/FreeThrowLanes';
import BasketAndBackboard from './court/BasketAndBackboard';
import ThreePointLine from './court/ThreePointLine';

const BasketballCourt = () => {
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
  
  // Scale factor to make it fit nicely on screen (1 foot = 8 pixels)
  const SCALE = 8;
  const LINE_THICKNESS = 2; // 2 inches thick lines
  
  // Calculated dimensions
  const courtLength = NBA_LENGTH * SCALE;
  const courtWidth = NBA_WIDTH * SCALE;
  const bufferSize = BUFFER_ZONE * SCALE;
  
  // Total SVG dimensions including buffer
  const totalWidth = courtLength + (2 * bufferSize);
  const totalHeight = courtWidth + (2 * bufferSize);

  return (
    <div className="basketball-court-container">
      <h2>Basketball Arena - Top View</h2>
      <div className="court-wrapper">
        <svg 
          width={totalWidth} 
          height={totalHeight}
          viewBox={`0 0 ${totalWidth} ${totalHeight}`}
          className="basketball-court"
        >
          {/* Buffer zone background */}
          <rect
            x={0}
            y={0}
            width={totalWidth}
            height={totalHeight}
            fill="#f5f5f5"
            stroke="#ccc"
            strokeWidth={1}
          />
          
          {/* Playing court background */}
          <rect
            x={bufferSize}
            y={bufferSize}
            width={courtLength}
            height={courtWidth}
            fill="#d2b48c"
            stroke="none"
          />
          
          {/* All court components are offset by the buffer size */}
          <g transform={`translate(${bufferSize}, ${bufferSize})`}>
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
      
      <div className="court-info">
        <p>Court Dimensions: {NBA_LENGTH}' × {NBA_WIDTH}' (NBA Standard)</p>
        <p>Buffer Zone: {BUFFER_ZONE}' around court</p>
        <p>Scale: 1 foot = {SCALE} pixels</p>
        <p>Line Thickness: 2 inches</p>
      </div>
    </div>
  );
};

export default BasketballCourt;
