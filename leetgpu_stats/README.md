# LeetGPU Performance Analytics Dashboard

This directory contains the complete LeetGPU scraping project that successfully collected runtime data for all 36 challenges across 5 frameworks and 5 GPUs.

## 🎯 Project Overview

A comprehensive analytics dashboard that visualizes GPU performance data from LeetGPU challenges. The project includes:

- **Web scraping infrastructure** for collecting runtime data from LeetGPU leaderboards
- **Interactive dashboard** with dual analysis modes (single-challenge and comprehensive)
- **Performance analytics** across 36 challenges, 5 frameworks, and 5 GPUs

## 🏆 Final Results

Successfully collected **1,800 runtime combinations** (36 challenges × 5 frameworks × 5 GPUs) with comprehensive performance analytics.

### Key Findings
- **CUDA** consistently performs best across most GPU architectures
- **NVIDIA H100/H200** show excellent performance across all frameworks
- **Significant performance variation** between challenges and frameworks
- **900+ valid timing measurements** collected from live leaderboards

## 📂 Project Structure

```
leetgpu_stats/
├── index.html                                    # Main dashboard (dual-mode analytics)
├── all_challenges_results_20250707_045604.json  # Complete dataset (1.4MB)
├── run_all_challenges_sequential.py             # Working scraper for all challenges
└── README.md                                    # This file
```

## 🚀 Quick Start

1. **View Dashboard**: Open `index.html` in your browser
2. **Collect New Data**: Run `python run_all_challenges_sequential.py`
3. **Requirements**: GitHub account for OAuth authentication

## 📊 Dashboard Features

### Single-Challenge Mode
- **Challenge selector** with all 36 challenges
- **Performance heatmap** showing framework vs GPU performance
- **Detailed timing charts** with color-coded performance levels
- **Interactive hover tooltips** with precise timing data

### Comprehensive Mode  
- **Framework performance summaries** across all challenges
- **Win/success rate analysis** by GPU type
- **Average performance rankings** with statistical insights
- **Cross-challenge comparison** charts

## 🔧 Technical Implementation

### Authentication & Scraping
- **GitHub OAuth integration** for leaderboard access
- **React dropdown navigation** using `cursor-pointer` class selectors
- **Selenium WebDriver** with Chrome automation
- **Sequential challenge processing** to avoid rate limiting

### Dashboard Technology
- **Vanilla JavaScript** with Chart.js for visualizations
- **Responsive design** with glassmorphism UI effects
- **Real-time data loading** from JSON dataset
- **Tab-based navigation** between analysis modes

### Data Structure
- **1,800 total combinations** across 36 challenges
- **900+ successful measurements** with timing data
- **JSON format** for fast dashboard loading
- **Framework/GPU performance matrix** for each challenge

## 🎨 Visual Design

The dashboard features a modern blue-themed design with:
- **Gradient backgrounds** (#0f1419 → #1e3a8a → #1e40af)
- **Glassmorphism effects** with backdrop blur
- **Color-coded performance** (green=fast, red=slow)
- **Smooth hover animations** and transitions

## 📈 Performance Analytics

### Framework Rankings (Overall)
1. **CUDA** - Best performance across most challenges
2. **TRITON** - Strong performance on newer GPUs
3. **PYTORCH** - Consistent mid-range performance
4. **MOJO** - Limited GPU support but competitive
5. **TINYGRAD** - Experimental framework with higher latency

### GPU Performance Tiers
- **Tier 1**: NVIDIA H100, H200, B200 (Latest generation)
- **Tier 2**: NVIDIA A100-80GB (Data center GPU)
- **Tier 3**: NVIDIA TESLA T4 (Older generation)

## 🔬 Research Applications

This dataset enables research into:
- **Framework optimization** across different GPU architectures
- **Challenge complexity analysis** and performance scaling
- **GPU performance evolution** across generations
- **Cross-platform performance** comparisons

## 🚀 Usage

### View Dashboard
```bash
# Option 1: Open directly in browser
open index.html

# Option 2: Serve locally
python -m http.server 8000
# Then visit: http://localhost:8000
```

### Collect New Data
```bash
python run_all_challenges_sequential.py
```

**Note**: Scraping requires manual GitHub authentication when prompted.

## 📝 Development History

This project evolved through multiple phases:
1. **Single-challenge scraping** (Vector Addition only)
2. **Multi-challenge expansion** (All 36 challenges)
3. **Dashboard development** (Interactive visualizations)
4. **Unified analytics** (Comprehensive performance analysis)

The breakthrough came from solving React-based dropdown navigation and implementing robust authentication handling for the LeetGPU platform. 