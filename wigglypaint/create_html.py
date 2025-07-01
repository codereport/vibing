#!/usr/bin/env python3
"""
Generate HTML page with the top 10 most upvoted Wigglypaint posts with GIFs
"""

import csv


def generate_html():
    # Read the corrected top results
    top_posts = []
    with open("wigglypaint_top_comments.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_posts = list(reader)

        # Filter and sort posts with images
        posts_with_images = [post for post in all_posts if post["Has_Image"] == "True"]
        sorted_posts = sorted(
            posts_with_images, key=lambda x: int(x["Upvotes"]), reverse=True
        )
        top_posts = sorted_posts[:10]

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 Wigglypaint Top 10 Community Posts with GIFs</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 15px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .header p {{
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 10px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            text-align: center;
            background: rgba(255, 255, 255, 0.8);
            padding: 15px 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #4ecdc4;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #666;
            margin-top: 5px;
        }}
        
        .posts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 40px;
        }}
        
        .post-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            position: relative;
        }}
        
        .post-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
        }}
        
        .rank-badge {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500);
            color: white;
            font-weight: bold;
            font-size: 1.1rem;
            padding: 8px 15px;
            border-radius: 25px;
            z-index: 10;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .image-container {{
            position: relative;
            width: 100%;
            height: 300px;
            overflow: hidden;
        }}
        
        .post-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        
        .post-card:hover .post-image {{
            transform: scale(1.05);
        }}
        
        .post-content {{
            padding: 25px;
        }}
        
        .post-author {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .post-text {{
            color: #666;
            margin: 15px 0;
            font-size: 1rem;
            line-height: 1.5;
        }}
        
        .vote-container {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-top: 20px;
        }}
        
        .upvotes {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        
        .downvotes {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(45deg, #ff6b6b, #ee5a52);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        }}
        
        .footer h3 {{
            color: #4ecdc4;
            margin-bottom: 15px;
        }}
        
        .footer p {{
            color: #666;
            margin-bottom: 10px;
        }}
        
        .celebration {{
            font-size: 2rem;
            margin: 20px 0;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}
            
            .stats {{
                gap: 15px;
            }}
            
            .stat {{
                padding: 10px 15px;
            }}
            
            .posts-grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Wigglypaint Community - Top 10 GIF Posts</h1>
            <p>Most upvoted community artwork with GIFs from internet-janitor.itch.io/wigglypaint</p>
            <p><strong>Fixed Data:</strong> Discovered 2,977 unique posts using correct pagination!</p>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">2,977</div>
                    <div class="stat-label">Total Posts</div>
                </div>
                <div class="stat">
                    <div class="stat-number">1,797</div>
                    <div class="stat-label">Posts with GIFs</div>
                </div>
                <div class="stat">
                    <div class="stat-number">60.4%</div>
                    <div class="stat-label">Contain Artwork</div>
                </div>
                <div class="stat">
                    <div class="stat-number">27</div>
                    <div class="stat-label">Highest Upvotes</div>
                </div>
            </div>
        </div>
        
        <div class="posts-grid">"""

    for i, post in enumerate(top_posts, 1):
        upvotes = post["Upvotes"]
        downvotes = post["Downvotes"]
        author = post["Author"]
        content = post["Content"]
        if not content.strip():
            content = "✨ Beautiful artwork shared with the community"
        elif len(content) > 120:
            content = content[:120] + "..."

        image_url = post["Image_URLs"]

        html_content += f"""
            <div class="post-card">
                <div class="rank-badge">#{i}</div>
                <div class="image-container">
                    <img src="{image_url}" alt="Community art by {author}" class="post-image" 
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 300 200%22><rect width=%22300%22 height=%22200%22 fill=%22%23f0f0f0%22/><text x=%22150%22 y=%22100%22 text-anchor=%22middle%22 fill=%22%23999%22 font-family=%22Arial%22 font-size=%2214%22>🎨 GIF Preview</text></svg>'">
                </div>
                <div class="post-content">
                    <div class="post-author">👨‍🎨 {author}</div>
                    <div class="post-text">"{content}"</div>
                    <div class="vote-container">
                        <div class="upvotes">
                            👍 {upvotes}
                        </div>
                        <div class="downvotes">
                            👎 {downvotes}
                        </div>
                    </div>
                </div>
            </div>"""

    html_content += f"""
        </div>
        
        <div class="footer">
            <div class="celebration">🎉 🎨 🎊</div>
            <h3>Amazing Discovery!</h3>
            <p><strong>Before fixing pagination:</strong> Only found 51 duplicate posts</p>
            <p><strong>After fixing pagination:</strong> Discovered 2,977 unique community posts!</p>
            <p><strong>Community creativity:</strong> 60.4% of posts contain beautiful GIF artwork</p>
            <p><strong>Top post:</strong> "squid" with 27 upvotes - "i got REALLY bored"</p>
            <br>
            <p>Data scraped from <a href="https://internet-janitor.itch.io/wigglypaint" style="color: #4ecdc4; text-decoration: none;">Wigglypaint on itch.io</a></p>
            <p>Scraping completed on {__import__('datetime').datetime.now().strftime('%B %d, %Y')}</p>
        </div>
    </div>
</body>
</html>"""

    # Save the HTML file
    with open("wigglypaint_top10.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ HTML page created: wigglypaint_top10.html")
    print("🎉 Shows the top 10 most upvoted posts with GIFs!")
    print("📊 Features 2,977 unique posts discovered")


if __name__ == "__main__":
    generate_html()
