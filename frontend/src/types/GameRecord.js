/**
 * GameRecord type definition and validation
 * 
 * This matches the Python GameRecord dataclass structure.
 * When migrating to TypeScript, this can be auto-generated from OpenAPI.
 */

/**
 * @typedef {Object} GameRecord
 * @property {string} game_id - Game ID from BuzzerBeater API
 * @property {number|null} id - Database ID (auto-generated)
 * @property {number|null} home_team_id - Home team ID
 * @property {number|null} away_team_id - Away team ID  
 * @property {string|null} date - ISO datetime string
 * @property {string|null} game_type - Game type (e.g., 'league.rs', 'friendly')
 * @property {number|null} season - Season number
 * @property {string|null} division - Division (usually null from boxscore API)
 * @property {string|null} country - Country (usually null from boxscore API)
 * @property {string|null} cup_round - Cup round (usually null from boxscore API)
 * @property {number|null} score_home - Home team score
 * @property {number|null} score_away - Away team score
 * @property {number|null} bleachers_attendance - Bleachers attendance
 * @property {number|null} lower_tier_attendance - Lower tier attendance
 * @property {number|null} courtside_attendance - Courtside attendance
 * @property {number|null} luxury_boxes_attendance - Luxury boxes attendance
 * @property {number|null} total_attendance - Computed: sum of all section attendances
 * @property {boolean} neutral_arena - True if game played at neutral venue
 * @property {number|null} ticket_revenue - Ticket revenue (usually null from boxscore API)
 * @property {number|null} calculated_revenue - Calculated revenue (computed property)
 * @property {number|null} bleachers_price - Bleachers price (from arena API)
 * @property {number|null} lower_tier_price - Lower tier price (from arena API)
 * @property {number|null} courtside_price - Courtside price (from arena API)
 * @property {number|null} luxury_boxes_price - Luxury boxes price (from arena API)
 * @property {string|null} created_at - ISO datetime string
 * @property {string|null} updated_at - ISO datetime string
 */

/**
 * Validates that an object matches the GameRecord structure
 * @param {any} data - Data to validate
 * @returns {GameRecord} Validated GameRecord object
 * @throws {Error} If validation fails
 */
export function validateGameRecord(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('GameRecord validation failed: data must be an object');
  }

  if (typeof data.game_id !== 'string' || !data.game_id) {
    throw new Error('GameRecord validation failed: game_id must be a non-empty string');
  }

  // Validate numeric fields (can be null)
  const numericFields = [
    'id', 'home_team_id', 'away_team_id', 'season', 'score_home', 'score_away',
    'bleachers_attendance', 'lower_tier_attendance', 'courtside_attendance', 
    'luxury_boxes_attendance', 'total_attendance', 'ticket_revenue', 'calculated_revenue',
    'bleachers_price', 'lower_tier_price', 'courtside_price', 'luxury_boxes_price'
  ];

  for (const field of numericFields) {
    if (data[field] !== null && data[field] !== undefined && typeof data[field] !== 'number') {
      throw new Error(`GameRecord validation failed: ${field} must be a number or null`);
    }
  }

  // Validate string fields (can be null)
  const stringFields = [
    'date', 'game_type', 'division', 'country', 'cup_round', 'created_at', 'updated_at'
  ];

  for (const field of stringFields) {
    if (data[field] !== null && data[field] !== undefined && typeof data[field] !== 'string') {
      throw new Error(`GameRecord validation failed: ${field} must be a string or null`);
    }
  }

  // Validate boolean field
  if (typeof data.neutral_arena !== 'boolean') {
    throw new Error('GameRecord validation failed: neutral_arena must be a boolean');
  }

  return data;
}

/**
 * Creates a formatted display of key game information
 * @param {GameRecord} gameRecord 
 * @returns {string} Formatted string for display
 */
export function formatGameRecord(gameRecord) {
  const date = gameRecord.date ? new Date(gameRecord.date).toLocaleDateString() : 'Unknown date';
  const score = gameRecord.score_home !== null && gameRecord.score_away !== null 
    ? `${gameRecord.score_home} - ${gameRecord.score_away}`
    : 'No score';
  const attendance = gameRecord.total_attendance || 'No attendance data';
  
  return `Game ${gameRecord.game_id} (${date}): ${score}, Attendance: ${attendance}`;
}

/**
 * Checks if a GameRecord has complete attendance data
 * @param {GameRecord} gameRecord 
 * @returns {boolean} True if all attendance sections have data
 */
export function hasCompleteAttendanceData(gameRecord) {
  return gameRecord.bleachers_attendance !== null &&
         gameRecord.lower_tier_attendance !== null &&
         gameRecord.courtside_attendance !== null &&
         gameRecord.luxury_boxes_attendance !== null;
}

/**
 * Checks if a GameRecord has pricing data
 * @param {GameRecord} gameRecord 
 * @returns {boolean} True if any pricing data is available
 */
export function hasPricingData(gameRecord) {
  return gameRecord.bleachers_price !== null ||
         gameRecord.lower_tier_price !== null ||
         gameRecord.courtside_price !== null ||
         gameRecord.luxury_boxes_price !== null;
}