#!/usr/bin/env python3
"""
Analyze the scraped results and show unique top posts
"""

import csv
from collections import defaultdict


def analyze_results():
    print("🎨 Wigglypaint Top Upvoted Posts with GIFs - Analysis Results\n")

    # Read the results
    posts = []
    with open("wigglypaint_top_comments.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        posts = list(reader)

    # Group by post_id to remove duplicates
    unique_posts = {}
    for post in posts:
        post_id = post["Post_ID"]
        if post_id not in unique_posts:
            unique_posts[post_id] = post

    # Sort by upvotes
    sorted_posts = sorted(
        unique_posts.values(), key=lambda x: int(x["Upvotes"]), reverse=True
    )

    print(f"📊 **SUMMARY**")
    print(f"Total unique posts with images: {len(sorted_posts)}")
    print(f"Highest upvote count: {sorted_posts[0]['Upvotes']}")
    print(
        f"Users with most upvoted posts: {len(set(p['Author'] for p in sorted_posts[:20]))}"
    )

    print(f"\n🏆 **TOP 15 MOST UPVOTED POSTS WITH GIFS:**\n")

    for i, post in enumerate(sorted_posts[:15], 1):
        upvotes = post["Upvotes"]
        downvotes = post["Downvotes"]
        author = post["Author"]
        content = (
            post["Content"][:50] + "..."
            if len(post["Content"]) > 50
            else post["Content"]
        )
        image_url = post["Image_URLs"]
        gif_filename = image_url.split("/")[-1] if image_url else "N/A"

        print(f"{i:2d}. **{author}** (+{upvotes}/-{downvotes})")
        print(f"    Content: {content}")
        print(f"    GIF: {gif_filename}")
        print(f"    URL: {image_url}")
        print()

    # Show top authors
    author_counts = defaultdict(int)
    author_upvotes = defaultdict(int)

    for post in sorted_posts:
        author = post["Author"]
        author_counts[author] += 1
        author_upvotes[author] += int(post["Upvotes"])

    print(f"👥 **TOP AUTHORS BY TOTAL UPVOTES:**\n")
    top_authors = sorted(author_upvotes.items(), key=lambda x: x[1], reverse=True)

    for i, (author, total_upvotes) in enumerate(top_authors[:10], 1):
        post_count = author_counts[author]
        avg_upvotes = total_upvotes / post_count
        print(
            f"{i:2d}. {author}: {total_upvotes} total upvotes ({post_count} posts, {avg_upvotes:.1f} avg)"
        )

    print(f"\n📈 **UPVOTE DISTRIBUTION:**")
    upvote_ranges = defaultdict(int)
    for post in sorted_posts:
        upvotes = int(post["Upvotes"])
        if upvotes >= 8:
            upvote_ranges["8+ upvotes"] += 1
        elif upvotes >= 6:
            upvote_ranges["6-7 upvotes"] += 1
        elif upvotes >= 4:
            upvote_ranges["4-5 upvotes"] += 1
        elif upvotes >= 2:
            upvote_ranges["2-3 upvotes"] += 1
        else:
            upvote_ranges["0-1 upvotes"] += 1

    for range_name, count in upvote_ranges.items():
        percentage = (count / len(sorted_posts)) * 100
        print(f"  {range_name}: {count} posts ({percentage:.1f}%)")


if __name__ == "__main__":
    analyze_results()
