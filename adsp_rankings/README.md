# ADSP Rankings Dashboard

A static web dashboard that displays global rankings with both absolute values and per capita analysis.

## Features

- **Dual View Modes**: Switch between raw rankings and per capita rankings
- **Interactive Search**: Filter countries by name in real-time
- **Sortable Data**: Toggle between ascending and descending order
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Clean, professional interface with smooth animations
- **Real-time Stats**: Display total countries, total value, and average value
- **Population Integration**: Automatically fetches current population data from REST Countries API

## How It Works

1. **Raw Rankings**: Shows countries ranked by their absolute values from the original data
2. **Per Capita Rankings**: Calculates and displays rankings based on values per million population
3. **Population Data**: Fetches current population data from the REST Countries API
4. **Smart Matching**: Handles different country naming conventions automatically

## Files Structure

```
├── index.html          # Main HTML dashboard
├── styles.css          # CSS styling and responsive design
├── script.js           # JavaScript functionality and data processing
├── raw_rankings.txt    # Original rankings data
└── README.md           # This documentation
```

## Usage

### Running Locally

1. **Simple HTTP Server** (recommended):
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Python 2
   python -m SimpleHTTPServer 8000
   
   # Node.js (if you have http-server installed)
   npx http-server
   ```

2. **Open in browser**: Navigate to `http://localhost:8000`

### Direct File Opening

You can also open `index.html` directly in your browser, but some features may not work due to CORS restrictions when fetching the population data API.

## Dashboard Features

### View Modes
- **Raw Rankings**: Shows absolute values and percentages
- **Per Capita Rankings**: Shows values per million population plus actual population

### Controls
- **Search Bar**: Type to filter countries by name
- **Sort Toggle**: Switch between descending and ascending order
- **View Toggle**: Switch between raw and per capita views

### Statistics Cards
- **Total Countries**: Number of countries displayed (updates with search)
- **Total Value**: Sum of all values for displayed countries
- **Average Value**: Mean value across displayed countries

## Data Processing

The dashboard processes the raw rankings data and:
1. Parses the 4-line format (flag, country, percentage, value)
2. Fetches population data from REST Countries API
3. Calculates per capita values (per million population)
4. Handles country name variations and special cases
5. Provides fallback values for countries not found in the API

## Browser Compatibility

- Chrome/Chromium 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## Deployment

This is a static site that can be deployed to any web hosting service:

- **GitHub Pages**: Push to a repository and enable Pages
- **Netlify**: Drag and drop the folder or connect to Git
- **Vercel**: Deploy with a single command
- **Any web server**: Upload files to public directory

## Customization

### Styling
Edit `styles.css` to customize:
- Color scheme (CSS variables at the top)
- Layout and spacing
- Typography
- Responsive breakpoints

### Functionality
Edit `script.js` to modify:
- Data processing logic
- Search and filter behavior
- Sort algorithms
- API endpoints

### Data Format
The dashboard expects `raw_rankings.txt` in the format:
```
🇺🇸
United States
36 %
367,041
🇩🇪
Germany
8 %
81,253
...
```

## Troubleshooting

### Population Data Not Loading
- Check internet connection
- REST Countries API might be temporarily unavailable
- Browser may be blocking the API request (try running via HTTP server)

### Styling Issues
- Clear browser cache
- Ensure all CSS files are loaded
- Check for JavaScript errors in browser console

### Search Not Working
- Ensure JavaScript is enabled
- Check for any console errors
- Try refreshing the page

## License

This project is open source and available under the MIT License.
