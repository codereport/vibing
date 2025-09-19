// Global variables
let rawData = [];
let populationData = {};
let currentView = 'raw';
let filteredData = [];

// DOM elements
const rawViewBtn = document.getElementById('rawView');
const perCapitaViewBtn = document.getElementById('perCapitaView');
const searchInput = document.getElementById('searchInput');
const tableBody = document.getElementById('rankingsTableBody');
const tableTitle = document.getElementById('tableTitle');
const tableSubtitle = document.getElementById('tableSubtitle');
const loadingElement = document.getElementById('loading');
const rankingsContainer = document.getElementById('rankingsContainer');
const errorMessage = document.getElementById('errorMessage');

// Stats elements
const totalCountriesElement = document.getElementById('totalCountries');
const totalDownloadsElement = document.getElementById('totalDownloads');
const avgDownloadsElement = document.getElementById('avgDownloads');

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    await loadRawData();
    await loadPopulationData();
    initializeEventListeners();
    renderTable();
    updateStats();
});

// Load raw rankings data
async function loadRawData() {
    try {
        const response = await fetch('raw_rankings.txt');
        const text = await response.text();
        const lines = text.trim().split('\n');

        for (let i = 0; i < lines.length; i += 4) {
            if (i + 3 < lines.length) {
                const flag = lines[i].trim();
                const country = lines[i + 1].trim();
                const percentage = lines[i + 2].trim(); // Skip this line but keep for data integrity
                const downloads = parseInt(lines[i + 3].replace(/,/g, ''));

                rawData.push({
                    flag,
                    country,
                    downloads,
                    originalRank: (i / 4) + 1
                });
            }
        }

        // Sort by downloads initially
        rawData.sort((a, b) => b.downloads - a.downloads);
        filteredData = [...rawData];

    } catch (error) {
        console.error('Error loading raw data:', error);
    }
}

// Load population data from REST Countries API
async function loadPopulationData() {
    try {
        const response = await fetch('https://restcountries.com/v3.1/all?fields=name,population');
        const countries = await response.json();

        // Create a mapping of country names to population
        countries.forEach(country => {
            const commonName = country.name.common;
            const officialName = country.name.official;
            const population = country.population;

            // Store both common and official names
            populationData[commonName] = population;
            populationData[officialName] = population;
        });

        // Manual mappings for countries with different naming conventions
        const manualMappings = {
            'United States': populationData['United States of America'] || 331900000,
            'United Kingdom': populationData['United Kingdom of Great Britain and Northern Ireland'] || 67500000,
            'Russia': populationData['Russian Federation'] || 146000000,
            'Russian Federation': populationData['Russian Federation'] || 146000000,
            'South Korea': populationData['Korea (Republic of)'] || populationData['South Korea'] || 51780000,
            'North Korea': populationData['Korea (Democratic People\'s Republic of)'] || 25780000,
            'Taiwan': 23570000, // Taiwan not in REST countries
            'Palestine, State of': 5200000,
            'Kosovo': 1900000,
            'Türkiye': populationData['Turkey'] || 84340000,
            'Congo, The Democratic Republic of the': populationData['Congo (Democratic Republic of the)'] || 95900000,
            'Lao People\'s Democratic Republic': populationData['Laos'] || 7320000,
            'Syrian Arab Republic': populationData['Syria'] || 18270000,
            'Virgin Islands, U.S.': populationData['United States Virgin Islands'] || 106000,
            'Virgin Islands, British': populationData['British Virgin Islands'] || 30000,
            'Cabo Verde': populationData['Cape Verde'] || 560000,
            'Saint Martin (French part)': populationData['Saint Martin'] || 38000,
            'Sint Maarten (Dutch part)': populationData['Sint Maarten'] || 41000,
            'Bonaire, Sint Eustatius and Saba': 26000,
            'Åland Islands': 30000
        };

        // Apply manual mappings
        Object.assign(populationData, manualMappings);

        // Calculate per capita values
        rawData.forEach(item => {
            const population = getPopulation(item.country);
            if (population > 0) {
                item.population = population;
                item.perCapita = (item.downloads / population) * 1000000; // Per million
            } else {
                item.population = 0;
                item.perCapita = 0;
            }
        });

        hideLoading();

    } catch (error) {
        console.error('Error loading population data:', error);
        showError();
        hideLoading();
    }
}

// Get population for a country with fuzzy matching
function getPopulation(countryName) {
    // Direct match
    if (populationData[countryName]) {
        return populationData[countryName];
    }

    // Try to find a partial match
    const keys = Object.keys(populationData);
    const match = keys.find(key =>
        key.toLowerCase().includes(countryName.toLowerCase()) ||
        countryName.toLowerCase().includes(key.toLowerCase())
    );

    return match ? populationData[match] : 0;
}

// Initialize event listeners
function initializeEventListeners() {
    rawViewBtn.addEventListener('click', () => switchView('raw'));
    perCapitaViewBtn.addEventListener('click', () => switchView('perCapita'));
    searchInput.addEventListener('input', handleSearch);
}

// Switch between raw and per capita views
function switchView(view) {
    currentView = view;

    // Update button states
    rawViewBtn.classList.toggle('active', view === 'raw');
    perCapitaViewBtn.classList.toggle('active', view === 'perCapita');

    // Update table headers and visibility
    const rawColumns = document.querySelectorAll('.raw-column');
    const perCapitaColumns = document.querySelectorAll('.per-capita-column');

    if (view === 'raw') {
        rawColumns.forEach(col => col.style.display = '');
        perCapitaColumns.forEach(col => col.style.display = 'none');
        tableTitle.textContent = 'Download Rankings';
        tableSubtitle.textContent = 'Sorted by absolute downloads';
    } else {
        rawColumns.forEach(col => col.style.display = 'none');
        perCapitaColumns.forEach(col => col.style.display = '');
        tableTitle.textContent = 'Per Capita Download Rankings';
        tableSubtitle.textContent = 'Sorted by per capita downloads (per million)';
    }

    renderTable();
}

// Handle search functionality
function handleSearch() {
    const searchTerm = searchInput.value.toLowerCase();

    if (searchTerm === '') {
        filteredData = [...rawData];
    } else {
        filteredData = rawData.filter(item =>
            item.country.toLowerCase().includes(searchTerm)
        );
    }

    renderTable();
    updateStats();
}


// Render the rankings table
function renderTable() {
    // Sort data based on current view (always descending)
    const sortedData = [...filteredData].sort((a, b) => {
        if (currentView === 'raw') {
            return b.downloads - a.downloads;
        } else {
            return b.perCapita - a.perCapita;
        }
    });

    // Create separate sorted arrays for ranking calculations
    const rawSorted = [...filteredData].sort((a, b) => b.downloads - a.downloads);
    const perCapitaSorted = [...filteredData].sort((a, b) => b.perCapita - a.perCapita);

    // Create rank mappings
    const rawRanks = {};
    const perCapitaRanks = {};

    rawSorted.forEach((item, index) => {
        rawRanks[item.country] = index + 1;
    });

    perCapitaSorted.forEach((item, index) => {
        perCapitaRanks[item.country] = index + 1;
    });

    // Clear existing rows
    tableBody.innerHTML = '';

    // Render rows
    sortedData.forEach((item, index) => {
        const row = document.createElement('tr');

        // Rank column (always shows the rank for current view)
        const rankCell = document.createElement('td');
        rankCell.className = 'rank-cell';
        rankCell.textContent = index + 1; // Current position in sorted list

        const countryCell = document.createElement('td');
        countryCell.className = 'country-cell';
        countryCell.innerHTML = `
            <span class="country-flag">${item.flag}</span>
            <span class="country-name">${item.country}</span>
        `;

        const downloadsCell = document.createElement('td');
        downloadsCell.className = 'downloads-cell raw-column';
        downloadsCell.textContent = item.downloads.toLocaleString();
        if (currentView === 'perCapita') downloadsCell.style.display = 'none';

        // Per capita rank column (shown in raw view as cross-reference)
        const perCapitaCrossRankCell = document.createElement('td');
        perCapitaCrossRankCell.className = 'rank-cell raw-column';
        perCapitaCrossRankCell.textContent = perCapitaRanks[item.country] || 'N/A';
        if (currentView === 'perCapita') perCapitaCrossRankCell.style.display = 'none';

        const perCapitaCell = document.createElement('td');
        perCapitaCell.className = 'per-capita-cell per-capita-column';
        perCapitaCell.textContent = item.perCapita ? item.perCapita.toFixed(2) : 'N/A';
        if (currentView === 'raw') perCapitaCell.style.display = 'none';

        // Download rank column (shown in per capita view as cross-reference)
        const downloadCrossRankCell = document.createElement('td');
        downloadCrossRankCell.className = 'rank-cell per-capita-column';
        downloadCrossRankCell.textContent = rawRanks[item.country];
        if (currentView === 'raw') downloadCrossRankCell.style.display = 'none';

        const populationCell = document.createElement('td');
        populationCell.className = 'population-cell per-capita-column';
        populationCell.textContent = item.population ? item.population.toLocaleString() : 'N/A';
        if (currentView === 'raw') populationCell.style.display = 'none';

        row.appendChild(rankCell);
        row.appendChild(countryCell);
        row.appendChild(downloadsCell);
        row.appendChild(perCapitaCrossRankCell);
        row.appendChild(perCapitaCell);
        row.appendChild(downloadCrossRankCell);
        row.appendChild(populationCell);

        tableBody.appendChild(row);
    });
}

// Update statistics
function updateStats() {
    const totalCountries = filteredData.length;
    const totalDownloads = filteredData.reduce((sum, item) => sum + item.downloads, 0);
    const avgDownloads = totalCountries > 0 ? Math.round(totalDownloads / totalCountries) : 0;

    totalCountriesElement.textContent = totalCountries.toLocaleString();
    totalDownloadsElement.textContent = totalDownloads.toLocaleString();
    avgDownloadsElement.textContent = avgDownloads.toLocaleString();
}

// Hide loading spinner
function hideLoading() {
    loadingElement.style.display = 'none';
    rankingsContainer.style.display = 'block';
}

// Show error message
function showError() {
    errorMessage.style.display = 'block';
}
