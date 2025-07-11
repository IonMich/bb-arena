import React from 'react';

const LuxuryBoxes = ({ 
  courtLength, // Already in pixels (court length)
  courtWidth,  // Already in pixels (court width)
  scale,       // Conversion factor: feet to pixels (8 pixels per foot)
  bufferSize = 0, // Already in pixels
  totalBoxes = 50, // Total number of luxury boxes (10-50)
  attendanceData = null // Attendance data for coloring
}) => {
  const boxDepth = 4 * scale; // 4 feet deep luxury boxes (reduced from 8 feet)
  const seatingDepth = 10 * scale; // 10 feet courtside seating depth
  const lowerTierDepth = 20 * scale; // 20 feet lower tier depth
  const northSouthExpansion = 12 * scale; // Matching the lower tier expansion
  const gapFromLowerTier = 4 * scale; // 4 feet gap between lower-tier and luxury boxes
  
  // Function to get attendance-based color for luxury boxes
  const getAttendanceColor = () => {
    if (!attendanceData?.luxury_boxes) {
      return "#1A202C"; // Default color
    }
    
    const totalCapacity = totalBoxes;
    const totalAttendance = attendanceData.luxury_boxes;
    const utilizationRate = Math.min(totalAttendance / totalCapacity, 1); // Cap at 100%
    
    // Color interpolation between grey (empty) and blue (full)
    const greyColor = { r: 128, g: 128, b: 128 }; // #808080
    const blueColor = { r: 30, g: 144, b: 255 }; // #1E90FF
    
    const r = Math.round(greyColor.r + (blueColor.r - greyColor.r) * utilizationRate);
    const g = Math.round(greyColor.g + (blueColor.g - greyColor.g) * utilizationRate);
    const b = Math.round(greyColor.b + (blueColor.b - greyColor.b) * utilizationRate);
    
    return `rgb(${r}, ${g}, ${b})`;
  };
  
  // Function to get attendance display text
  const getAttendanceDisplay = () => {
    if (!attendanceData?.luxury_boxes) {
      return null;
    }
    const utilizationRate = (attendanceData.luxury_boxes / totalBoxes * 100).toFixed(1);
    return `${attendanceData.luxury_boxes}/${totalBoxes} (${utilizationRate}%)`;
  };
  
  const boxColor = getAttendanceColor();
  const attendanceDisplay = getAttendanceDisplay();
  
  // Calculate total area dimensions
  const totalAreaWidth = courtLength + (2 * bufferSize);
  
  // Calculate box distribution - distribute totalBoxes across north and south rows
  const northBoxCount = Math.ceil(totalBoxes / 2);
  const southBoxCount = Math.floor(totalBoxes / 2);
  const maxBoxesPerRow = Math.max(northBoxCount, southBoxCount);
  
  // Calculate box width based on the row with more boxes
  const lowerTierOuterWidth = totalAreaWidth + (2 * northSouthExpansion); // Match lower-tier outer edge
  const boxWidth = lowerTierOuterWidth / maxBoxesPerRow; // Calculate box width to fit the larger row
  const startOffset = 0; // No offset needed since we're using the full width

  const renderLuxuryBoxRow = (yPosition, rowName, startBoxNumber, boxCount) => {
    const boxes = [];
    
    for (let i = 0; i < boxCount; i++) {
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
            fill={boxColor}
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
            y={boxY + (boxDepth / 2) - 5}
            fontSize="10"
            fill="#F7FAFC"
            textAnchor="middle"
            dominantBaseline="middle"
            className="box-number"
            fontWeight="bold"
          >
            {String(startBoxNumber + i).padStart(3, '0')}
          </text>
          
          {/* Attendance display */}
          {attendanceDisplay && (
            <text
              x={boxX + (boxWidth / 2)}
              y={boxY + (boxDepth / 2) + 8}
              fontSize="6"
              fill="#CBD5E0"
              textAnchor="middle"
              dominantBaseline="middle"
              className="box-attendance"
            >
              {attendanceDisplay}
            </text>
          )}
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
      {renderLuxuryBoxRow(northBoxesY, 'north', 1, northBoxCount)}
      
      {/* South luxury boxes row */}
      {renderLuxuryBoxRow(southBoxesY, 'south', northBoxCount + 1, southBoxCount)}
    </g>
  );
};

export default LuxuryBoxes;
