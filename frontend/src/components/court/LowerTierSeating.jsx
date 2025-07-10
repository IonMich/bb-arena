import React from 'react';

const LowerTierSeating = ({ 
  courtLength, // Already in pixels (court length)
  courtWidth,  // Already in pixels (court width)
  scale,       // Conversion factor: feet to pixels (8 pixels per foot)
  bufferSize = 0, // Already in pixels
  luxuryBoxExpansion = 0, // Additional expansion for luxury boxes alignment
  seatsPerSection = 500, // Base seats per section
  remainingSeats = 0 // Additional seats to distribute
}) => {
  const sectionDepth = 20 * scale; // 20 feet converted to pixels (increased from 8 feet)
  
  // Function to calculate seats for each section
  const getSectionSeats = (sectionIndex) => {
    // Distribute remaining seats among the first sections
    return seatsPerSection + (sectionIndex < remainingSeats ? 1 : 0);
  };
  
  const renderTrapezoidalSection = (
    innerStartX, innerStartY, innerEndX, innerEndY,
    outerStartX, outerStartY, outerEndX, outerEndY,
    sectionNumber, sideIndex, sectionSeats
  ) => {
    // Create path for trapezoidal section
    const pathData = `
      M ${innerStartX},${innerStartY}
      L ${innerEndX},${innerEndY}
      L ${outerEndX},${outerEndY}
      L ${outerStartX},${outerStartY}
      Z
    `;
    
    // Calculate section center for text placement
    const centerX = (innerStartX + innerEndX + outerStartX + outerEndX) / 4;
    const centerY = (innerStartY + innerEndY + outerStartY + outerEndY) / 4;
    
    return (
      <g key={`section-${sideIndex}-${sectionNumber}`} className="lower-tier-section">
        <path
          d={pathData}
          fill="#4A5568"
          stroke="#2D3748"
          strokeWidth={1}
          className="section-area"
          data-section={`${sideIndex}-${sectionNumber}`}
          data-seats={sectionSeats}
        />
        {/* Section number */}
        <text
          x={centerX}
          y={centerY - 5}
          fontSize="12"
          fill="white"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-number"
          fontWeight="bold"
        >
          {sectionNumber}
        </text>
        {/* Seat count */}
        <text
          x={centerX}
          y={centerY + 8}
          fontSize="8"
          fill="#CBD5E0"
          textAnchor="middle"
          dominantBaseline="middle"
          className="section-capacity"
        >
          {sectionSeats} seats
        </text>
      </g>
    );
  };

  const renderSideSections = () => {
    const sections = [];
    const seatingDepth = 10 * scale; // 10 feet courtside seating depth in pixels
    const courtsideSeatingDepth = 10 * scale; // Courtside seating is 10 feet deep
    const totalAreaWidth = courtLength + (2 * bufferSize); // Buffer zone width
    const totalAreaHeight = courtWidth + (2 * bufferSize); // Total height of court+buffer area
    
    let sectionIndex = 0; // Track section index for seat distribution
    
    // North sections (101-105) - Split into 5 sections with proportional outer edge
    // Use original expansion or luxury box expansion to match the outer edge width with luxury boxes
    const northSouthExpansion = luxuryBoxExpansion || (12 * scale); // Use luxury box expansion or default 12 feet
    const northSectionsCount = 5;
    const northSectionWidth = totalAreaWidth / northSectionsCount; // Divide inner edge into 5 sections
    const outerTotalWidth = totalAreaWidth + (2 * northSouthExpansion); // Total outer edge width
    const outerSectionWidth = outerTotalWidth / northSectionsCount; // Divide outer edge proportionally
    
    for (let i = 0; i < northSectionsCount; i++) {
      // Inner edge (shorter) - equal divisions
      const north_innerStartX = seatingDepth + (i * northSectionWidth);
      const north_innerStartY = 0; // At the top edge of lower-tier area
      const north_innerEndX = seatingDepth + ((i + 1) * northSectionWidth);
      const north_innerEndY = 0;

      // Outer edge (longer) - proportional divisions to match the longer width
      const north_outerStartX = seatingDepth - northSouthExpansion + (i * outerSectionWidth);
      const north_outerStartY = 0 - sectionDepth;
      const north_outerEndX = seatingDepth - northSouthExpansion + ((i + 1) * outerSectionWidth);
      const north_outerEndY = 0 - sectionDepth;

      sections.push(
        renderTrapezoidalSection(
          north_innerStartX, north_innerStartY, north_innerEndX, north_innerEndY,
          north_outerStartX, north_outerStartY, north_outerEndX, north_outerEndY,
          101 + i, // Section numbers 101-105
          0, // North side
          getSectionSeats(sectionIndex++)
        )
      );
    }

    // South sections (201-205) - Split into 5 sections with proportional outer edge
    // Calculate position relative to the court area, accounting for courtside seating
    const courtAndBufferHeight = courtWidth + (2 * bufferSize); // Total height of court+buffer area (using courtWidth for height)
    const southSectionsCount = 5;
    const southSectionWidth = totalAreaWidth / southSectionsCount; // Divide inner edge into 5 sections
    const southOuterTotalWidth = totalAreaWidth + (2 * northSouthExpansion); // Use same expansion as north
    const southOuterSectionWidth = southOuterTotalWidth / southSectionsCount; // Divide outer edge proportionally
    
    for (let i = 0; i < southSectionsCount; i++) {
      // Inner edge (shorter) - equal divisions
      const south_innerStartX = seatingDepth + (i * southSectionWidth);
      const south_innerStartY = seatingDepth + courtAndBufferHeight + courtsideSeatingDepth; // Below the courtside area
      const south_innerEndX = seatingDepth + ((i + 1) * southSectionWidth);
      const south_innerEndY = south_innerStartY;

      // Outer edge (longer) - proportional divisions to match the longer width
      const south_outerStartX = seatingDepth - northSouthExpansion + (i * southOuterSectionWidth);
      const south_outerStartY = seatingDepth + courtAndBufferHeight + courtsideSeatingDepth + sectionDepth;
      const south_outerEndX = seatingDepth - northSouthExpansion + ((i + 1) * southOuterSectionWidth);
      const south_outerEndY = south_outerStartY;

      sections.push(
        renderTrapezoidalSection(
          south_innerStartX, south_innerStartY, south_innerEndX, south_innerEndY,
          south_outerStartX, south_outerStartY, south_outerEndX, south_outerEndY,
          201 + i, // Section numbers 201-205
          1, // South side
          getSectionSeats(sectionIndex++)
        )
      );
    }

    // West sections (301-303) - Split into 3 sections with proportional outer edge
    // Calculate position relative to the court area, accounting for courtside seating
    const eastWestExpansion = 10 * scale; // 10 feet expansion for east/west sections (increased from 8 feet)
    const eastWestInnerExpansion = 6 * scale; // 6 feet expansion for inner edges to make them much wider
    const westSectionsCount = 3;
    
    // Calculate heights for proportional division
    const innerTotalHeight = totalAreaHeight + (2 * eastWestInnerExpansion); // Inner edge total height
    const outerTotalHeight = totalAreaHeight + (2 * eastWestExpansion); // Outer edge total height
    const innerSectionHeight = innerTotalHeight / westSectionsCount; // Divide inner edge into 3 sections
    const outerSectionHeight = outerTotalHeight / westSectionsCount; // Divide outer edge proportionally
    
    for (let i = 0; i < westSectionsCount; i++) {
      // Inner edge (shorter) - equal divisions
      const west_innerStartX = 0; // At the left edge of lower-tier area
      const west_innerStartY = seatingDepth - eastWestInnerExpansion + (i * innerSectionHeight);
      const west_innerEndX = 0;
      const west_innerEndY = seatingDepth - eastWestInnerExpansion + ((i + 1) * innerSectionHeight);

      // Outer edge (longer) - proportional divisions
      const west_outerStartX = 0 - sectionDepth;
      const west_outerStartY = seatingDepth - eastWestExpansion + (i * outerSectionHeight);
      const west_outerEndX = 0 - sectionDepth;
      const west_outerEndY = seatingDepth - eastWestExpansion + ((i + 1) * outerSectionHeight);

      sections.push(
        renderTrapezoidalSection(
          west_innerStartX, west_innerStartY, west_innerEndX, west_innerEndY,
          west_outerStartX, west_outerStartY, west_outerEndX, west_outerEndY,
          301 + i, // Section numbers 301-303
          2, // West side
          getSectionSeats(sectionIndex++)
        )
      );
    }

    // East sections (401-403) - Split into 3 sections with proportional outer edge
    // Calculate position relative to the court area, accounting for courtside seating
    const eastSectionsCount = 3;
    
    for (let i = 0; i < eastSectionsCount; i++) {
      // Inner edge (shorter) - equal divisions
      const east_innerStartX = seatingDepth + totalAreaWidth + courtsideSeatingDepth; // Right of courtside area
      const east_innerStartY = seatingDepth - eastWestInnerExpansion + (i * innerSectionHeight);
      const east_innerEndX = east_innerStartX;
      const east_innerEndY = seatingDepth - eastWestInnerExpansion + ((i + 1) * innerSectionHeight);

      // Outer edge (longer) - proportional divisions
      const east_outerStartX = seatingDepth + totalAreaWidth + courtsideSeatingDepth + sectionDepth;
      const east_outerStartY = seatingDepth - eastWestExpansion + (i * outerSectionHeight);
      const east_outerEndX = east_outerStartX;
      const east_outerEndY = seatingDepth - eastWestExpansion + ((i + 1) * outerSectionHeight);

      sections.push(
        renderTrapezoidalSection(
          east_innerStartX, east_innerStartY, east_innerEndX, east_innerEndY,
          east_outerStartX, east_outerStartY, east_outerEndX, east_outerEndY,
          401 + i, // Section numbers 401-403
          3, // East side
          getSectionSeats(sectionIndex++)
        )
      );
    }

    return sections;
  };

  return (
    <g className="lower-tier-seating">
      {renderSideSections()}
    </g>
  );
};

export default LowerTierSeating;
