import React from 'react';

const BasketAndBackboard = ({ 
  courtLength, 
  courtWidth,
  basketInnerDiameter, 
  backboardWidth, 
  backboardDistanceFromBaseline, 
  scale, 
  lineThickness 
}) => {
    const basketDistanceFromBaseline = backboardDistanceFromBaseline + (basketInnerDiameter / 12) / 2; // feet
  return (
    <g>
      {/* Left backboard */}
      <line
        x1={backboardDistanceFromBaseline * scale}
        y1={(courtWidth - (backboardWidth / 12) * scale) / 2}
        x2={backboardDistanceFromBaseline * scale}
        y2={(courtWidth + (backboardWidth / 12) * scale) / 2}
        stroke="#000"
        strokeWidth={lineThickness * 2}
      />
      
      {/* Right backboard */}
      <line
        x1={courtLength - backboardDistanceFromBaseline * scale}
        y1={(courtWidth - (backboardWidth / 12) * scale) / 2}
        x2={courtLength - backboardDistanceFromBaseline * scale}
        y2={(courtWidth + (backboardWidth / 12) * scale) / 2}
        stroke="#000"
        strokeWidth={lineThickness * 2}
      />
      
      {/* Left basket */}
      <circle
        cx={basketDistanceFromBaseline * scale}
        cy={courtWidth / 2}
        r={(basketInnerDiameter / 12) * scale / 2}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right basket */}
      <circle
        cx={courtLength - basketDistanceFromBaseline * scale}
        cy={courtWidth / 2}
        r={(basketInnerDiameter / 12) * scale / 2}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
    </g>
  );
};

export default BasketAndBackboard;
