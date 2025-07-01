# 🎨 Wigglypaint Community Post Scraper

This directory contains all files related to scraping and analyzing community posts from [Wigglypaint](https://internet-janitor.itch.io/wigglypaint) on itch.io.

## 🎉 Project Success Summary

**Major Discovery:** Fixed broken pagination revealed **2,977 unique community posts** instead of 51 duplicates!

- **Before Fix:** 51 duplicated posts (pagination broken)
- **After Fix:** 2,977 unique posts with 1,797 containing GIFs (60.4% creativity rate!)
- **Top Post:** "squid" with 27 upvotes - "i got REALLY bored"

## 📁 File Structure

### 🚀 Main Scripts
- `scraper.py` - **Main scraper** with cursor-based pagination
- `create_html.py` - Generates beautiful HTML page with top 10 posts
- `wigglypaint_top10.html` - **Final HTML page** with top 10 posts

### 📊 Final Data Files
- `wigglypaint_all_comments.csv` - All 2,977 unique community posts
- `wigglypaint_top_comments.csv` - Top 100 posts with GIFs
- `wigglypaint_top_comments.json` - Top 100 posts (JSON format)

### 🔧 Analysis Scripts
- `complete_analysis.py` - Comprehensive analysis of all posts
- `analyze_results.py` - Focused analysis of top upvoted posts

### 📈 Test Results
- `test_results.csv` - Test data from 5 pages (343 posts)
- `top_comments.csv` - Top posts from test run

## 🏆 Top 10 Most Upvoted Posts with GIFs

1. **squid** (+27 upvotes): "i got REALLY bored"
2. **BAPHY00** (+26 upvotes): Beautiful artwork
3. **leadenema** (+25 upvotes): "digging the new marker resizer!"
4. **lusushi** (+25 upvotes): Beautiful artwork
5. **OopfGroza** (+24 upvotes): Beautiful artwork
6. **bogglle** (+22 upvotes): "Bakas"
7. **Hellbabe69** (+22 upvotes): Beautiful artwork
8. **ryangatts** (+22 upvotes): Beautiful artwork
9. **allr** (+21 upvotes): "tbh creature surfing"
10. **Cas (YG)** (+21 upvotes): Beautiful artwork

## 🛠️ How to Use

### Run the Scraper
```bash
cd wigglypaint
python scraper.py --full
```

### Generate HTML Page
```bash
python create_html.py
```

### Run Analysis
```bash
python complete_analysis.py
```

## 🔍 Technical Details

**Pagination Issue Fixed:**
- **Problem:** itch.io uses cursor-based pagination (`?before=ID`), not page numbers (`?page=N`)
- **Solution:** Follow "Next page" links with cursor IDs instead of incrementing page numbers
- **Result:** Discovered 58x more content than broken pagination!

**Community Statistics:**
- **Total Posts:** 2,977 unique community posts
- **Posts with GIFs:** 1,797 (60.4% of all posts!)
- **Most Active Creators:** Tanukii (16 posts), Grimdar (15 posts), crowspace (17 posts)
- **Highest Engagement:** 27 upvotes maximum, 18 posts with 20+ upvotes

## 🎨 Community Insights

The Wigglypaint community is incredibly creative:
- **60.4% of posts contain artwork** - much higher than typical forums
- **Active artist community** with regular contributors
- **Positive engagement** - minimal downvotes, lots of appreciation
- **Diverse content** from simple doodles to complex animations 