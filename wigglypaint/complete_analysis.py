#!/usr/bin/env python3
"""
Complete analysis of all scraped community posts
"""

import csv
from collections import defaultdict, Counter


def complete_analysis():
    print("🎨 Complete Wigglypaint Community Posts Analysis\n")

    # Read all posts
    all_posts = []
    with open("wigglypaint_all_comments.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_posts = list(reader)

    print(f"📊 **OVERALL STATS**")
    print(f"Total posts scraped: {len(all_posts)}")

    # Remove duplicates by post_id
    unique_posts = {}
    for post in all_posts:
        post_id = post["Post_ID"]
        if post_id not in unique_posts:
            unique_posts[post_id] = post

    print(f"Total unique posts: {len(unique_posts)}")

    # Filter posts with images
    posts_with_images = [
        post for post in unique_posts.values() if post["Has_Image"] == "True"
    ]
    print(f"Unique posts with images: {len(posts_with_images)}")

    # Sort by upvotes
    sorted_posts = sorted(
        posts_with_images, key=lambda x: int(x["Upvotes"]), reverse=True
    )

    print(f"\n🏆 **TOP 20 MOST UPVOTED POSTS WITH GIFS (UNIQUE):**\n")

    for i, post in enumerate(sorted_posts[:20], 1):
        upvotes = post["Upvotes"]
        downvotes = post["Downvotes"]
        author = post["Author"]
        content = (
            post["Content"][:60] + "..."
            if len(post["Content"]) > 60
            else post["Content"]
        )
        image_count = post["Image_Count"]
        image_url = post["Image_URLs"]
        gif_name = image_url.split("/")[-1].split("?")[0] if image_url else "N/A"

        print(
            f"{i:2d}. **{author}** (+{upvotes}/-{downvotes}) - {image_count} image(s)"
        )
        print(f"    Content: {content}")
        print(f"    GIF: {gif_name}")
        print(f"    URL: {image_url}")
        print()

    # Upvote distribution
    print(f"📈 **UPVOTE DISTRIBUTION FOR POSTS WITH IMAGES:**")
    upvote_counts = [int(post["Upvotes"]) for post in posts_with_images]
    upvote_counter = Counter(upvotes for upvotes in upvote_counts)

    for upvotes in sorted(upvote_counter.keys(), reverse=True):
        count = upvote_counter[upvotes]
        percentage = (count / len(posts_with_images)) * 100
        if upvotes >= 1 or count > 10:  # Show significant counts
            print(f"  {upvotes} upvotes: {count} posts ({percentage:.1f}%)")

    # Top authors by unique posts
    print(f"\n👥 **TOP AUTHORS BY UNIQUE POSTS WITH IMAGES:**")
    author_posts = defaultdict(list)
    for post in posts_with_images:
        author_posts[post["Author"]].append(int(post["Upvotes"]))

    author_stats = []
    for author, upvotes_list in author_posts.items():
        total_posts = len(upvotes_list)
        total_upvotes = sum(upvotes_list)
        avg_upvotes = total_upvotes / total_posts
        max_upvotes = max(upvotes_list)
        author_stats.append(
            (author, total_posts, total_upvotes, avg_upvotes, max_upvotes)
        )

    # Sort by total upvotes
    author_stats.sort(key=lambda x: x[2], reverse=True)

    for i, (author, post_count, total_upvotes, avg_upvotes, max_upvotes) in enumerate(
        author_stats[:15], 1
    ):
        print(
            f"{i:2d}. {author}: {total_upvotes} total upvotes ({post_count} posts, {avg_upvotes:.1f} avg, {max_upvotes} max)"
        )

    # Image statistics
    print(f"\n🖼️  **IMAGE STATISTICS:**")
    total_images = sum(int(post["Image_Count"]) for post in posts_with_images)
    print(f"Total images in posts: {total_images}")
    print(f"Average images per post: {total_images / len(posts_with_images):.1f}")

    # Multi-image posts
    multi_image_posts = [
        post for post in posts_with_images if int(post["Image_Count"]) > 1
    ]
    print(f"Posts with multiple images: {len(multi_image_posts)}")

    if multi_image_posts:
        max_images = max(int(post["Image_Count"]) for post in multi_image_posts)
        print(f"Maximum images in a single post: {max_images}")

    # Show some high upvote posts with interesting content
    print(f"\n🎯 **NOTABLE HIGH-UPVOTE POSTS:**")
    notable_posts = [
        post
        for post in sorted_posts
        if int(post["Upvotes"]) >= 5 and len(post["Content"].strip()) > 0
    ]

    for i, post in enumerate(notable_posts[:10], 1):
        content = post["Content"].strip()
        if content:
            print(f"{i}. {post['Author']} (+{post['Upvotes']}): {content[:100]}...")


if __name__ == "__main__":
    complete_analysis()
