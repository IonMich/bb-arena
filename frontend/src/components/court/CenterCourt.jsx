import React from 'react';

const CenterCourt = ({ courtLength, courtWidth, centerCircleRadius, scale, lineThickness }) => {
  return (
    <g>
      {/* Center court line */}
      <line
        x1={courtLength / 2}
        y1={lineThickness / 2}
        x2={courtLength / 2}
        y2={courtWidth - lineThickness / 2}
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Center circle */}
      <circle
        cx={courtLength / 2}
        cy={courtWidth / 2}
        r={centerCircleRadius * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Inner center circle */}
      <circle
        cx={courtLength / 2}
        cy={courtWidth / 2}
        r={2 * scale}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
    </g>
  );
};

export default CenterCourt;
