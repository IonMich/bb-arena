import React from 'react';

const CourtsideSeating = ({ 
  courtLength, 
  courtWidth, 
  scale, 
  bufferSize = 0
}) => {
  const rowDepth = 2 * scale; // 2 feet per row
  const seatSpacing = 1.5 * scale; // 1.5 feet between seats
  const maxSeats = 500; // Maximum courtside seats
  const seatsPerRow = Math.floor((courtLength - (2 * scale)) / seatSpacing); // Seats along the length
  const seatsPerSideRow = Math.floor((courtWidth - (2 * scale)) / seatSpacing); // Seats along the width
  
  // Calculate total seats per side and number of rows needed (using only 3 sides)
  const totalSeatsPerSide = seatsPerRow + seatsPerSideRow + seatsPerSideRow; // south + east + west (excluding north)
  const numberOfRows = Math.ceil(maxSeats / totalSeatsPerSide);
  
  const renderSeats = (startX, startY, numSeats, direction = 'horizontal', sideIndex = 0, rowIndex = 0) => {
    const seats = [];
    for (let i = 0; i < numSeats; i++) {
      let seatX, seatY;
      if (direction === 'horizontal') {
        seatX = startX + (i * seatSpacing);
        seatY = startY;
      } else {
        seatX = startX;
        seatY = startY + (i * seatSpacing * 1.1); // Add 10% extra spacing for vertical seats
      }
      
      // Calculate sequential seat number across all sides and rows
      // Numbers increase as seats get further from the court (closest seats have lowest numbers)
      // All Row 0 seats get lowest numbers, then all Row 1 seats, etc.
      let seatNumber;
      if (sideIndex === 0) { // South side
        seatNumber = (rowIndex * (seatsPerRow + seatsPerSideRow + seatsPerSideRow)) + i + 1;
      } else if (sideIndex === 1) { // East side
        seatNumber = (rowIndex * (seatsPerRow + seatsPerSideRow + seatsPerSideRow)) + seatsPerRow + i + 1;
      } else if (sideIndex === 2) { // West side
        seatNumber = (rowIndex * (seatsPerRow + seatsPerSideRow + seatsPerSideRow)) + seatsPerRow + seatsPerSideRow + i + 1;
      }
      
      // Don't render seats beyond the maximum
      if (seatNumber > maxSeats) {
        break;
      }
      
      seats.push(
        <g key={`${direction}-${rowIndex}-${i}`}>
          <rect
            x={seatX}
            y={seatY}
            width={direction === 'horizontal' ? seatSpacing * 0.8 : seatSpacing * 0.8}
            height={direction === 'horizontal' ? rowDepth * 0.8 : rowDepth * 0.6}
            fill="#8B4513"
            stroke="#654321"
            strokeWidth={0.5}
            className="courtside-seat"
            data-seat={seatNumber}
          />
          {/* Seat number text */}
          <text
            x={seatX + (seatSpacing * 0.4)}
            y={direction === 'horizontal' ? seatY + (rowDepth * 0.4) : seatY + (rowDepth * 0.3)}
            fontSize="6"
            fill="white"
            textAnchor="middle"
            dominantBaseline="middle"
            className="seat-number"
          >
            {seatNumber}
          </text>
        </g>
      );
    }
    return seats;
  };

  return (
    <g className="courtside-seating">
      {/* South side seating (below the court, outside buffer) */}
      {Array.from({ length: numberOfRows }, (_, rowIndex) => (
        <g key={`south-${rowIndex}`}>
          {renderSeats(
            bufferSize, // Start at the buffer zone edge
            bufferSize + courtWidth + bufferSize + (rowDepth * 0.5) + (rowIndex * rowDepth), // Position below buffer zone with consistent spacing
            seatsPerRow,
            'horizontal',
            0, // South side index
            rowIndex
          )}
        </g>
      ))}
      
      {/* East side seating (right of court, outside buffer) */}
      {Array.from({ length: numberOfRows }, (_, rowIndex) => (
        <g key={`east-${rowIndex}`}>
          {renderSeats(
            bufferSize + courtLength + bufferSize + (rowDepth * 0.5) + (rowIndex * rowDepth), // Position right of buffer zone with consistent spacing
            bufferSize, // Start at the buffer zone edge
            seatsPerSideRow,
            'vertical',
            1, // East side index
            rowIndex
          )}
        </g>
      ))}
      
      {/* West side seating (left of court, outside buffer) */}
      {Array.from({ length: numberOfRows }, (_, rowIndex) => (
        <g key={`west-${rowIndex}`}>
          {renderSeats(
            bufferSize - (rowIndex + 3) * rowDepth, // Position left with consistent spacing
            bufferSize, // Start at the buffer zone edge
            seatsPerSideRow,
            'vertical',
            2, // West side index
            rowIndex
          )}
        </g>
      ))}
    </g>
  );
};

export default CourtsideSeating;
