import React from 'react';

const LuxuryBoxes = ({ 
  courtLength, // Already in pixels (court length)
  courtWidth,  // Already in pixels (court width)
  scale,       // Conversion factor: feet to pixels (8 pixels per foot)
  bufferSize = 0 // Already in pixels
}) => {
  const boxDepth = 4 * scale; // 4 feet deep luxury boxes (reduced from 8 feet)
  const seatingDepth = 10 * scale; // 10 feet courtside seating depth
  const lowerTierDepth = 20 * scale; // 20 feet lower tier depth
  const northSouthExpansion = 12 * scale; // Matching the lower tier expansion
  const gapFromLowerTier = 4 * scale; // 4 feet gap between lower-tier and luxury boxes
  
  // Calculate total area dimensions
  const totalAreaWidth = courtLength + (2 * bufferSize);
  
  // Force exactly 25 boxes per row and calculate the required width to match lower-tier outer edge
  const maxBoxesPerRow = 25; // Exactly 25 boxes per row (50 total)
  const lowerTierOuterWidth = totalAreaWidth + (2 * northSouthExpansion); // Match lower-tier outer edge
  const boxWidth = lowerTierOuterWidth / maxBoxesPerRow; // Calculate exact box width to fit 25 boxes
  const boxesPerRow = maxBoxesPerRow; // Always 25 boxes
  const startOffset = 0; // No offset needed since we're using the full width

  const renderLuxuryBoxRow = (yPosition, rowName, startBoxNumber) => {
    const boxes = [];
    
    for (let i = 0; i < boxesPerRow; i++) {
      const boxX = seatingDepth - northSouthExpansion + startOffset + (i * boxWidth);
      const boxY = yPosition;
      
      // Box rectangle
      boxes.push(
        <g key={`luxury-box-${rowName}-${i}`} className="luxury-box">
          <rect
            x={boxX}
            y={boxY}
            width={boxWidth}
            height={boxDepth}
            fill="#1A202C"
            stroke="#2D3748"
            strokeWidth={2}
            className="luxury-box-area"
            data-box={`${startBoxNumber + i}`}
            data-ticket="1"
          />
          
          {/* Box divider lines */}
          {i > 0 && (
            <line
              x1={boxX}
              y1={boxY}
              x2={boxX}
              y2={boxY + boxDepth}
              stroke="#4A5568"
              strokeWidth={1}
            />
          )}
          
          {/* Box number */}
          <text
            x={boxX + (boxWidth / 2)}
            y={boxY + (boxDepth / 2)}
            fontSize="10"
            fill="#F7FAFC"
            textAnchor="middle"
            dominantBaseline="middle"
            className="box-number"
            fontWeight="bold"
          >
            {String(startBoxNumber + i).padStart(3, '0')}
          </text>
        </g>
      );
    }
    
    return boxes;
  };

  // Calculate positions for luxury box rows
  const courtAndBufferHeight = courtWidth + (2 * bufferSize);
  
  // North luxury boxes - positioned above the north lower-tier seating with gap
  const northBoxesY = 0 - lowerTierDepth - gapFromLowerTier - boxDepth;
  
  // South luxury boxes - positioned below the south lower-tier seating with gap
  const southBoxesY = seatingDepth + courtAndBufferHeight + seatingDepth + lowerTierDepth + gapFromLowerTier;

  return (
    <g className="luxury-boxes">
      {/* North luxury boxes row */}
      {renderLuxuryBoxRow(northBoxesY, 'north', 1)}
      
      {/* South luxury boxes row */}
      {renderLuxuryBoxRow(southBoxesY, 'south', boxesPerRow + 1)}
    </g>
  );
};

export default LuxuryBoxes;
