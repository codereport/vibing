# LeetGPU Vector Addition Runtime Scraper

This directory contains the complete LeetGPU scraping project that successfully collected runtime data for all framework/GPU combinations on the Vector Addition challenge.

## 🎯 Project Goal

Extract CUDA/Triton/PyTorch/Mojo/TinyGrad runtime results across different GPUs from the LeetGPU leaderboard by navigating combo boxes using Selenium.

## 🏆 Final Results

Successfully collected **25 runtime combinations** (5 frameworks × 5 GPUs) with **100% success rate** for dropdown navigation.

### Overall Fastest Runtime
**CUDA on NVIDIA TESLA T4: 0.002 ms**

### Complete Results Summary

| Framework    | NVIDIA TESLA T4 | NVIDIA A100-80GB | NVIDIA H100 | NVIDIA H200 | NVIDIA B200 |
| ------------ | --------------- | ---------------- | ----------- | ----------- | ----------- |
| **CUDA**     | 0.002 ms        | 0.1757 ms        | 0.0998 ms   | 0.0774 ms   | 0.048 ms    |
| **TRITON**   | 1.182 ms        | 0.2009 ms        | 0.1214 ms   | 0.0963 ms   | 0.0705 ms   |
| **PYTORCH**  | 1.2038 ms       | 0.1768 ms        | 0.1034 ms   | 0.078 ms    | 0.0488 ms   |
| **MOJO**     | 1.2245 ms       | 0.226 ms         | 0.162 ms    | No data     | No data     |
| **TINYGRAD** | 2.213 ms        | 1.2522 ms        | 0.8807 ms   | No data     | No data     |

## 📂 Key Files

### Final Working Scraper
- `final_25_combinations_scraper.py` - The successful scraper that collected all 25 combinations

### Results
- `final_25_combinations.json` - Complete results in JSON format
- `final_25_combinations.csv` - Results in CSV format for analysis

### Discovery Process
- `test_dropdown_click.py` - Tool that discovered the correct dropdown structure
- `dropdown_test/` - Screenshots and HTML files from dropdown discovery

### Development History
- `scrape_leetgpu.py` - Original scraper (basic functionality)
- `debug_screenshots/` - Debug captures during authentication testing
- `debug_output/` - Various debugging outputs
- `leetgpu_page_source.html` - Captured page source for analysis

## 🔧 Technical Implementation

### Key Challenges Solved
1. **React App Loading**: Required waiting for React components to fully load
2. **Authentication**: GitHub OAuth integration for leaderboard access
3. **Dropdown Navigation**: Discovered button-based dropdown structure using `cursor-pointer` class
4. **Dynamic Content**: Handled React state changes after selections

### Dropdown Structure Discovery
- **Framework options**: Direct text in divs with `cursor-pointer` class
- **GPU options**: Text inside `<span class="truncate">` within `cursor-pointer` divs

### Authentication Flow
1. Load LeetGPU Vector Addition challenge page
2. Click Leaderboard button (triggers auth requirement)
3. Handle GitHub OAuth authentication
4. Click Leaderboard button again (accesses dropdown interface)
5. Navigate framework and GPU selections
6. Extract fastest runtime from leaderboard

## 📊 Statistics

- **Total Combinations**: 25
- **Successful Selections**: 25 (100% success rate)
- **Valid Timing Data**: 21 (84% - some newer GPUs don't have data for all frameworks)
- **Frameworks Tested**: CUDA, TRITON, PYTORCH, MOJO, TINYGRAD
- **GPUs Tested**: NVIDIA TESLA T4, A100-80GB, H100, H200, B200

## 🚀 Usage

To run the scraper:

```bash
python final_25_combinations_scraper.py
```

**Requirements:**
- GitHub account for OAuth authentication
- Chrome browser (managed automatically via webdriver-manager)
- Required Python packages (selenium, webdriver-manager)

## 📝 Development Process

The project evolved through multiple iterations:
1. Basic page scraping (failed - no dropdown access)
2. Authentication handling (successful login)
3. Dropdown structure discovery (key breakthrough)
4. Final implementation with complete navigation

The breakthrough came from analyzing HTML diffs before/after clicking dropdown buttons, revealing the React-based structure that wasn't using standard `@role='option'` selectors. 