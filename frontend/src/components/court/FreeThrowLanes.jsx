import React from 'react';

const FreeThrowLanes = ({ 
  courtLength, 
  courtWidth, 
  freeThrowLaneWidth, 
  freeThrowLaneLength, 
  freeThrowCircleRadius, 
  scale, 
  lineThickness 
}) => {
  return (
    <g>
      {/* Left lane */}
      <rect
        x={lineThickness / 2}
        y={(courtWidth - freeThrowLaneWidth * scale) / 2}
        width={freeThrowLaneLength * scale}
        height={freeThrowLaneWidth * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right lane */}
      <rect
        x={courtLength - freeThrowLaneLength * scale - lineThickness / 2}
        y={(courtWidth - freeThrowLaneWidth * scale) / 2}
        width={freeThrowLaneLength * scale}
        height={freeThrowLaneWidth * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Left free throw circle */}
      <circle
        cx={freeThrowLaneLength * scale}
        cy={courtWidth / 2}
        r={freeThrowCircleRadius * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right free throw circle */}
      <circle
        cx={courtLength - freeThrowLaneLength * scale}
        cy={courtWidth / 2}
        r={freeThrowCircleRadius * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
    </g>
  );
};

export default FreeThrowLanes;
