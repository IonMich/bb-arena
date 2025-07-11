import React from 'react';

const CourtsideSeating = ({ 
  courtLength, 
  courtWidth, 
  scale, 
  bufferSize = 0,
  maxSeats = 500,
  attendanceData = null
}) => {
  const seatingDepth = 10 * scale; // 10 feet deep courtside seating
  
  // Function to calculate attendance-based color
  const getAttendanceColor = () => {
    if (!attendanceData?.courtside) {
      return "#8B4513"; // Default brown color
    }
    
    const totalCapacity = maxSeats;
    const totalAttendance = attendanceData.courtside;
    const utilizationRate = Math.min(totalAttendance / totalCapacity, 1); // Cap at 100%
    
    // Color interpolation between grey (empty) and blue (full)
    const greyColor = { r: 128, g: 128, b: 128 }; // #808080
    const blueColor = { r: 30, g: 144, b: 255 }; // #1E90FF
    
    const r = Math.round(greyColor.r + (blueColor.r - greyColor.r) * utilizationRate);
    const g = Math.round(greyColor.g + (blueColor.g - greyColor.g) * utilizationRate);
    const b = Math.round(greyColor.b + (blueColor.b - greyColor.b) * utilizationRate);
    
    return `rgb(${r}, ${g}, ${b})`;
  };
  
  // Function to get attendance info for display
  const getAttendanceDisplay = () => {
    if (!attendanceData?.courtside) {
      return `${maxSeats} seats`;
    }
    const utilizationRate = (attendanceData.courtside / maxSeats * 100).toFixed(1);
    return `${attendanceData.courtside}/${maxSeats} (${utilizationRate}%)`;
  };
  
  const sectionColor = getAttendanceColor();
  const attendanceDisplay = getAttendanceDisplay();
  
  // Calculate seating areas for each side
  const courtsideGap = seatingDepth / 4; // Add a gap between buffer zone and courtside seating
  const courtsideExtension = seatingDepth / 2; // Extend courtside seating beyond court dimensions
  const southSeatingWidth = courtLength + (2 * courtsideExtension); // Extend beyond court length
  const southSeatingX = bufferSize - courtsideExtension; // Start before the buffer edge
  const southSeatingY = bufferSize + courtWidth + bufferSize + courtsideGap; // Add gap after buffer zone
  const southSeatingHeight = seatingDepth / 2; // Half the depth (short dimension)
  
  const eastSeatingX = bufferSize + courtLength + bufferSize + courtsideGap; // Position with gap after the buffer zone
  const eastSeatingY = bufferSize - courtsideExtension; // Start before the buffer edge
  const eastSeatingWidth = seatingDepth / 2; // Half the depth (short dimension)
  const eastSeatingHeight = courtWidth + (2 * courtsideExtension); // Extend beyond court width
  
  const westSeatingX = 0 - courtsideGap - seatingDepth / 2; // Position with gap from the left edge of buffer zone
  const westSeatingY = bufferSize - courtsideExtension; // Start before the buffer edge
  const westSeatingWidth = seatingDepth / 2; // Half the depth (short dimension)
  const westSeatingHeight = courtWidth + (2 * courtsideExtension); // Extend beyond court width
  
  // Calculate approximate seats per section (total 500 divided by 3 sides)
  const seatsPerSection = Math.floor(maxSeats / 3);
  const remainingSeats = maxSeats - (seatsPerSection * 3);
  
  return (
    <g className="courtside-seating">
      {/* South side seating rectangle */}
      <g className="south-courtside">
        <rect
          x={southSeatingX}
          y={southSeatingY}
          width={southSeatingWidth}
          height={southSeatingHeight}
          fill={sectionColor}
          stroke="#654321"
          strokeWidth={2}
          className="courtside-section"
          data-side="south"
          data-seats={seatsPerSection + Math.floor(remainingSeats / 2)}
        />
        <text
          x={southSeatingX + southSeatingWidth / 2}
          y={southSeatingY + southSeatingHeight / 2}
          fontSize="12"
          fill="white"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-label"
          fontWeight="bold"
        >
          Courtside South
        </text>
        <text
          x={southSeatingX + southSeatingWidth / 2}
          y={southSeatingY + southSeatingHeight / 2 + 15}
          fontSize="10"
          fill="#F4A460"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-capacity"
        >
          {attendanceDisplay}
        </text>
      </g>
      
      {/* East side seating rectangle */}
      <g className="east-courtside">
        <rect
          x={eastSeatingX}
          y={eastSeatingY}
          width={eastSeatingWidth}
          height={eastSeatingHeight}
          fill={sectionColor}
          stroke="#654321"
          strokeWidth={2}
          className="courtside-section"
          data-side="east"
          data-seats={seatsPerSection}
        />
        <text
          x={eastSeatingX + eastSeatingWidth / 2}
          y={eastSeatingY + eastSeatingHeight / 2}
          fontSize="9"
          fill="white"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-label"
          fontWeight="bold"
          transform={`rotate(90, ${eastSeatingX + eastSeatingWidth / 2}, ${eastSeatingY + eastSeatingHeight / 2})`}
        >
          Courtside East
        </text>
        <text
          x={eastSeatingX + eastSeatingWidth / 2}
          y={eastSeatingY + eastSeatingHeight / 2 + 35}
          fontSize="6"
          fill="#F4A460"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-capacity"
          transform={`rotate(90, ${eastSeatingX + eastSeatingWidth / 2}, ${eastSeatingY + eastSeatingHeight / 2 + 35})`}
        >
          {seatsPerSection} seats
        </text>
      </g>
      
      {/* West side seating rectangle */}
      <g className="west-courtside">
        <rect
          x={westSeatingX}
          y={westSeatingY}
          width={westSeatingWidth}
          height={westSeatingHeight}
          fill={sectionColor}
          stroke="#654321"
          strokeWidth={2}
          className="courtside-section"
          data-side="west"
          data-seats={seatsPerSection + (remainingSeats - Math.floor(remainingSeats / 2))}
        />
        <text
          x={westSeatingX + westSeatingWidth / 2}
          y={westSeatingY + westSeatingHeight / 2}
          fontSize="9"
          fill="white"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-label"
          fontWeight="bold"
          transform={`rotate(-90, ${westSeatingX + westSeatingWidth / 2}, ${westSeatingY + westSeatingHeight / 2})`}
        >
          Courtside West
        </text>
        <text
          x={westSeatingX + westSeatingWidth / 2}
          y={westSeatingY + westSeatingHeight / 2 + 35}
          fontSize="6"
          fill="#F4A460"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-capacity"
          transform={`rotate(-90, ${westSeatingX + westSeatingWidth / 2}, ${westSeatingY + westSeatingHeight / 2 + 35})`}
        >
          {seatsPerSection + (remainingSeats - Math.floor(remainingSeats / 2))} seats
        </text>
      </g>
    </g>
  );
};

export default CourtsideSeating;
