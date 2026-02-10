/**
 * SportsTotalBot Dashboard - Simplified
 * =====================================
 * Real data only - displays today's picks from the API
 *
 * Features:
 * - API call to /api/picks for real data
 * - Picks table with EV badges, win probability bars
 * - Auto-refresh every 60 seconds
 * - Loading/error states
 */

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
    API_BASE_URL: window.location.origin,
    REFRESH_INTERVAL: 60000, // 60 seconds
    EV_THRESHOLDS: {
        HIGH: 8,   // percent
        MEDIUM: 4, // percent
    },
};

// =============================================================================
// Application State
// =============================================================================

const AppState = {
    picks: [],
    lastUpdated: null,
    isLoading: false,
    error: null,
    refreshTimer: null,
};

// =============================================================================
// API Client
// =============================================================================

/**
 * Fetch today's picks from API
 * @returns {Promise<Object>} Response with picks data
 */
async function fetchPicks() {
    showLoading();
    clearError();

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/picks`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();

        if (data.success) {
            AppState.picks = data.picks || [];
            AppState.lastUpdated = data.last_updated || new Date().toISOString();
            renderPicksTable(AppState.picks);
            updateLastUpdated();
            updateDataStatus(true);
        } else {
            throw new Error(data.error || 'Failed to fetch picks');
        }
    } catch (error) {
        console.error('Error fetching picks:', error);
        showError(`Failed to load picks: ${error.message}`);
        updateDataStatus(false);
    } finally {
        hideLoading();
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format a date string in Eastern Time
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted time (e.g., "7:30 PM")
 */
function formatETTime(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
        });
    } catch (error) {
        return '--:--';
    }
}

/**
 * Get EV badge color class based on EV percentage
 * @param {number} ev - Expected Value percentage
 * @returns {string} CSS class name
 */
function getEVColorClass(ev) {
    if (ev >= CONFIG.EV_THRESHOLDS.HIGH) {
        return 'ev-high';
    } else if (ev >= CONFIG.EV_THRESHOLDS.MEDIUM) {
        return 'ev-medium';
    } else if (ev > 0) {
        return 'ev-low';
    } else {
        return 'ev-negative';
    }
}

/**
 * Get win probability color class
 * @param {number} winProb - Win probability percentage
 * @returns {string} CSS class name
 */
function getWinProbColorClass(winProb) {
    if (winProb >= 60) {
        return 'prob-high';
    } else if (winProb >= 52) {
        return 'prob-medium';
    } else {
        return 'prob-low';
    }
}

/**
 * Format team name for display (shortens common team names)
 * @param {string} teamName - Full team name
 * @returns {string} Formatted team name
 */
function formatTeamName(teamName) {
    const shortNames = {
        'Los Angeles Lakers': 'Lakers',
        'Los Angeles Clippers': 'Clippers',
        'Golden State Warriors': 'Warriors',
        'New York Knicks': 'Knicks',
        'Brooklyn Nets': 'Nets',
        'Boston Celtics': 'Celtics',
        'Philadelphia 76ers': '76ers',
        'Toronto Raptors': 'Raptors',
        'Chicago Bulls': 'Bulls',
        'Miami Heat': 'Heat',
        'Dallas Mavericks': 'Mavericks',
        'San Antonio Spurs': 'Spurs',
        'Houston Rockets': 'Rockets',
        'Phoenix Suns': 'Suns',
        'Denver Nuggets': 'Nuggets',
        'Utah Jazz': 'Jazz',
        'Oklahoma City Thunder': 'Thunder',
        'Minnesota Timberwolves': 'Timberwolves',
        'Portland Trail Blazers': 'Blazers',
        'Sacramento Kings': 'Kings',
        'Memphis Grizzlies': 'Grizzlies',
        'New Orleans Pelicans': 'Pelicans',
        'Indiana Pacers': 'Pacers',
        'Detroit Pistons': 'Pistons',
        'Cleveland Cavaliers': 'Cavaliers',
        'Milwaukee Bucks': 'Bucks',
        'Atlanta Hawks': 'Hawks',
        'Charlotte Hornets': 'Hornets',
        'Washington Wizards': 'Wizards',
        'Orlando Magic': 'Magic',
    };
    return shortNames[teamName] || teamName;
}

/**
 * Format American odds
 * @param {number} odds - American odds
 * @returns {string} Formatted odds
 */
function formatOdds(odds) {
    if (odds > 0) {
        return `+${odds}`;
    }
    return odds.toString();
}

// =============================================================================
// UI Functions
// =============================================================================

/**
 * Show loading state
 */
function showLoading() {
    AppState.isLoading = true;
    const tbody = document.getElementById('picksTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px;">
                    <div class="loading-spinner">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Loading picks...</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

/**
 * Hide loading state
 */
function hideLoading() {
    AppState.isLoading = false;
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showError(message) {
    AppState.error = message;
    const errorContainer = document.getElementById('errorContainer');
    if (errorContainer) {
        errorContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
        errorContainer.style.display = 'block';
    }
}

/**
 * Clear error message
 */
function clearError() {
    AppState.error = null;
    const errorContainer = document.getElementById('errorContainer');
    if (errorContainer) {
        errorContainer.innerHTML = '';
        errorContainer.style.display = 'none';
    }
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated() {
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (lastUpdateEl && AppState.lastUpdated) {
        const timeStr = new Date(AppState.lastUpdated).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
        lastUpdateEl.textContent = timeStr;
    }
}

/**
 * Update data connection status indicator
 * @param {boolean} connected - Connection status
 */
function updateDataStatus(connected) {
    const dataStatus = document.getElementById('dataStatus');
    if (dataStatus) {
        if (connected) {
            dataStatus.innerHTML = '<i class="fas fa-check-circle" style="color: var(--accent-green);"></i> Connected';
        } else {
            dataStatus.innerHTML = '<i class="fas fa-exclamation-circle" style="color: var(--accent-red);"></i> Error';
        }
    }
}

// =============================================================================
// Picks Table Rendering
// =============================================================================

/**
 * Render picks table
 * @param {Array} picks - Array of pick objects
 */
function renderPicksTable(picks) {
    const tbody = document.getElementById('picksTableBody');
    if (!tbody) return;

    // Clear existing content
    tbody.innerHTML = '';

    if (!picks || picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px;">
                    <div class="empty-state">
                        <i class="fas fa-calendar-day"></i>
                        <p>No picks available for today</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Render each row
    picks.forEach(pick => {
        const row = createPickRow(pick);
        tbody.appendChild(row);
    });
}

/**
 * Create a table row for a pick
 * @param {Object} pick - Pick object
 * @returns {HTMLElement} Table row element
 */
function createPickRow(pick) {
    const row = document.createElement('tr');
    row.className = 'pick-row';
    row.dataset.gameId = pick.game_id;

    const awayTeam = formatTeamName(pick.away_team || '');
    const homeTeam = formatTeamName(pick.home_team || '');
    const evClass = getEVColorClass(pick.ev || 0);
    const winProbClass = getWinProbColorClass(pick.win_probability || 0);

    row.innerHTML = `
        <td>
            <div class="time-cell">${formatETTime(pick.game_time)}</div>
        </td>
        <td>
            <div class="matchup-cell">
                <div class="away-team">${awayTeam}</div>
                <div class="vs">@</div>
                <div class="home-team">${homeTeam}</div>
            </div>
        </td>
        <td>
            <span class="bet-type-badge">${pick.bet_type || 'N/A'}</span>
        </td>
        <td>
            <div class="pick-details">
                <div class="pick-side">${pick.side || 'N/A'}</div>
                <div class="pick-line">${pick.line || 'N/A'}</div>
            </div>
        </td>
        <td>
            <span class="odds-badge">${formatOdds(pick.odds || 0)}</span>
        </td>
        <td>
            <span class="ev-badge ${evClass}">
                ${pick.ev > 0 ? '+' : ''}${(pick.ev || 0).toFixed(2)}%
            </span>
        </td>
        <td>
            <div class="win-prob-container">
                <div class="win-prob-label">${(pick.win_probability || 0).toFixed(1)}%</div>
                <div class="win-prob-bar">
                    <div class="win-prob-fill ${winProbClass}" style="width: ${pick.win_probability || 0}%"></div>
                </div>
            </div>
        </td>
    `;

    return row;
}

// =============================================================================
// Auto-Refresh
// =============================================================================

/**
 * Initialize auto-refresh
 */
function initAutoRefresh() {
    // Clear existing timer
    if (AppState.refreshTimer) {
        clearInterval(AppState.refreshTimer);
    }

    // Set new timer
    AppState.refreshTimer = setInterval(() => {
        fetchPicks();
    }, CONFIG.REFRESH_INTERVAL);
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
    if (AppState.refreshTimer) {
        clearInterval(AppState.refreshTimer);
        AppState.refreshTimer = null;
    }
}

// =============================================================================
// Event Handlers
// =============================================================================

/**
 * Initialize event listeners
 */
function initEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetchPicks();
        });
    }
}

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the application
 */
async function initApp() {
    console.log('Initializing SportsTotalBot Dashboard...');

    // Initialize event listeners
    initEventListeners();

    // Fetch initial data
    await fetchPicks();

    // Start auto-refresh
    initAutoRefresh();

    console.log('SportsTotalBot Dashboard initialized');
}

/**
 * Cleanup on page unload
 */
function cleanup() {
    stopAutoRefresh();
}

// =============================================================================
// Bootstrap
// =============================================================================

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);

// =============================================================================
// End of app.js
// =============================================================================
