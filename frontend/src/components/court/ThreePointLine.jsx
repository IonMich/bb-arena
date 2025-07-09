import React from 'react';

const ThreePointLine = ({ 
  courtLength, 
  courtWidth, 
  basketDistanceFromBaseline, 
  scale, 
  lineThickness 
}) => {
  // NBA three-point line specifications
  const THREE_POINT_ARC_RADIUS = 23.75; // 23 feet 9 inches = 23.75 feet
  
  // Calculate positions
  const leftBasketX = basketDistanceFromBaseline * scale;
  const rightBasketX = courtLength - basketDistanceFromBaseline * scale;
  const basketY = courtWidth / 2;
  
  // Calculate arc radius for the path
  const arcRadius = THREE_POINT_ARC_RADIUS * scale;
  
  // Calculate intersection points where horizontal lines would meet the arc
  const horizontalY1 = 3 * scale; // 3 feet from top sideline
  const horizontalY2 = courtWidth - (3 * scale); // 3 feet from bottom sideline
  
  // Calculate actual intersection points using geometry
  // For a circle centered at (basketX, basketY) with radius arcRadius
  // and horizontal lines at y = horizontalY1 and y = horizontalY2
  
  // Distance from basket center to horizontal lines
  const distanceToTopLine = Math.abs(basketY - horizontalY1);
  const distanceToBottomLine = Math.abs(basketY - horizontalY2);
  
  // Use Pythagorean theorem: x = sqrt(r² - y²)
  // Each horizontal line intersects each arc at TWO points (left and right of center)
  const deltaXTop = Math.sqrt(arcRadius * arcRadius - distanceToTopLine * distanceToTopLine);
  const deltaXBottom = Math.sqrt(arcRadius * arcRadius - distanceToBottomLine * distanceToBottomLine);
  
  // Left arc intersection points (only need the ones we use)
  const leftTopIntersectionX2 = leftBasketX + deltaXTop; // Right side of arc
  const leftBottomIntersectionX2 = leftBasketX + deltaXBottom;
  
  // Right arc intersection points (only need the ones we use)
  const rightTopIntersectionX1 = rightBasketX - deltaXTop; // Left side of arc
  const rightBottomIntersectionX1 = rightBasketX - deltaXBottom;

  return (
    <g>
      {/* Left three-point arc - clipped between intersection points */}
      <path
        d={`M ${leftTopIntersectionX2} ${horizontalY1} 
            A ${arcRadius} ${arcRadius} 0 0 1 ${leftBottomIntersectionX2} ${horizontalY2}`}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right three-point arc - clipped between intersection points */}
      <path
        d={`M ${rightTopIntersectionX1} ${horizontalY1} 
            A ${arcRadius} ${arcRadius} 0 0 0 ${rightBottomIntersectionX1} ${horizontalY2}`}
        fill="none"
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Left horizontal segments - clipped at intersection points */}
      {/* Left top horizontal line */}
      <line
        x1={0}
        y1={horizontalY1}
        x2={leftTopIntersectionX2}
        y2={horizontalY1}
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Left bottom horizontal line */}
      <line
        x1={0}
        y1={horizontalY2}
        x2={leftBottomIntersectionX2}
        y2={horizontalY2}
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right horizontal segments - clipped at intersection points */}
      {/* Right top horizontal line */}
      <line
        x1={rightTopIntersectionX1}
        y1={horizontalY1}
        x2={courtLength}
        y2={horizontalY1}
        stroke="#000"
        strokeWidth={lineThickness}
      />
      
      {/* Right bottom horizontal line */}
      <line
        x1={rightBottomIntersectionX1}
        y1={horizontalY2}
        x2={courtLength}
        y2={horizontalY2}
        stroke="#000"
        strokeWidth={lineThickness}
      />
    </g>
  );
}

export default ThreePointLine;
