import React from 'react';

const CourtOutline = ({ courtLength, courtWidth, lineThickness }) => {
  return (
    <rect
      x={lineThickness / 2}
      y={lineThickness / 2}
      width={courtLength - lineThickness}
      height={courtWidth - lineThickness}
      fill="#d2691e"
      stroke="#000"
      strokeWidth={lineThickness}
    />
  );
};

export default CourtOutline;
