#!/usr/bin/env python3
"""
Fixed Wigglypaint Comment Scraper with correct cursor-based pagination
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import json
from urllib.parse import urljoin, urlparse, parse_qs
from collections import namedtuple
import csv
from typing import List, Optional
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

Comment = namedtuple(
    "Comment",
    [
        "author",
        "content",
        "upvotes",
        "downvotes",
        "timestamp",
        "has_image",
        "image_urls",
        "page_num",
        "post_id",
    ],
)


class FixedWigglypaintScraper:
    def __init__(self):
        self.base_url = "https://internet-janitor.itch.io/wigglypaint"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def extract_author_from_post(self, post_element) -> str:
        """Extract author from a community post."""
        # Look for profile links
        all_links = post_element.find_all("a")
        for link in all_links:
            href = link.get("href", "")
            if "/profile/" in href and link.get_text(strip=True):
                return link.get_text(strip=True)
        return "Anonymous"

    def extract_content_from_post(self, post_element) -> str:
        """Extract text content from a community post."""
        post_body = post_element.find("div", class_="post_body")
        if not post_body:
            return ""

        # Get text content while filtering out noise
        content_parts = []
        for text_node in post_body.find_all(string=True):
            text = text_node.strip()
            if (
                text
                and len(text) > 2
                and not re.match(r"^\([+-]?\d+\)$", text)
                and "Reply" not in text
                and "ago" not in text
                and text not in ["↑", "↓", "▲", "▼"]
            ):
                content_parts.append(text)

        return " ".join(content_parts).strip()

    def extract_images_from_post(self, post_element) -> List[str]:
        """Extract image URLs from a community post."""
        images = post_element.find_all("img")
        image_urls = []

        for img in images:
            src = img.get("src")
            if src and "itch.zone" in src:
                full_url = urljoin(self.base_url, src)
                if full_url not in image_urls:
                    image_urls.append(full_url)

        return image_urls

    def extract_votes_from_post(self, post_element) -> tuple:
        """Extract upvote and downvote counts from a community post."""
        upvotes = 0
        downvotes = 0

        # Look for vote spans within this specific post
        vote_spans = post_element.find_all("span", class_=["upvotes", "downvotes"])

        for span in vote_spans:
            vote_text = span.get_text(strip=True)
            vote_match = re.search(r"\(([+-]?\d+)\)", vote_text)

            if vote_match:
                count = int(vote_match.group(1))
                if "upvotes" in span.get("class", []):
                    upvotes = max(upvotes, count)
                elif "downvotes" in span.get("class", []):
                    downvotes = max(downvotes, abs(count))

        return upvotes, downvotes

    def extract_timestamp_from_post(self, post_element) -> str:
        """Extract timestamp from a community post."""
        time_patterns = [
            r"\d+\s+(minute|hour|day|week|month)s?\s+ago",
            r"\d+[mhd]\s+ago",
        ]

        post_text = post_element.get_text()
        for pattern in time_patterns:
            match = re.search(pattern, post_text, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""

    def parse_community_posts(self, soup, page_num: int) -> List[Comment]:
        """Parse community posts from the page."""
        comments = []

        # Find all community posts
        community_posts = soup.find_all("div", class_="community_post")

        logger.info(f"Found {len(community_posts)} community posts on page {page_num}")

        for post in community_posts:
            try:
                # Extract post ID
                post_id = post.get("id", "unknown")

                # Extract author
                author = self.extract_author_from_post(post)

                # Extract content
                content = self.extract_content_from_post(post)

                # Extract images
                image_urls = self.extract_images_from_post(post)

                # Extract votes
                upvotes, downvotes = self.extract_votes_from_post(post)

                # Extract timestamp
                timestamp = self.extract_timestamp_from_post(post)

                # Create comment object
                comment = Comment(
                    author=author,
                    content=content,
                    upvotes=upvotes,
                    downvotes=downvotes,
                    timestamp=timestamp,
                    has_image=len(image_urls) > 0,
                    image_urls=image_urls,
                    page_num=page_num,
                    post_id=post_id,
                )
                comments.append(comment)

            except Exception as e:
                logger.warning(f"Error parsing community post: {e}")
                continue

        return comments

    def find_next_page_url(self, soup) -> Optional[str]:
        """Find the URL for the next page using cursor-based pagination."""
        # Look for "Next page" link
        next_links = soup.find_all(
            "a", string=lambda text: text and "Next page" in text
        )

        for link in next_links:
            href = link.get("href")
            if href and "before=" in href:
                return href

        return None

    def scrape_all_comments_cursor(self, max_pages: int = 100) -> List[Comment]:
        """Scrape comments using cursor-based pagination."""
        logger.info(f"Starting cursor-based scraping (max {max_pages} pages)...")

        all_comments = []
        current_url = self.base_url
        page_num = 1

        while current_url and page_num <= max_pages:
            logger.info(f"Scraping page {page_num}: {current_url}")

            try:
                response = self.session.get(current_url, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                page_comments = self.parse_community_posts(soup, page_num)

                if not page_comments:
                    logger.info(f"No comments found on page {page_num}, stopping")
                    break

                all_comments.extend(page_comments)
                logger.info(
                    f"Page {page_num}: Found {len(page_comments)} comments (total: {len(all_comments)})"
                )

                # Find next page URL
                next_url = self.find_next_page_url(soup)

                if next_url:
                    # Convert relative URL to absolute if needed
                    if next_url.startswith("/"):
                        current_url = f"https://internet-janitor.itch.io{next_url}"
                    elif not next_url.startswith("http"):
                        current_url = urljoin(self.base_url, next_url)
                    else:
                        current_url = next_url

                    page_num += 1

                    # Rate limiting
                    time.sleep(1.5)
                else:
                    logger.info("No next page link found, reached end")
                    break

            except requests.RequestException as e:
                logger.error(f"Error fetching page {page_num}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing page {page_num}: {e}")
                break

        logger.info(
            f"Cursor-based scraping complete! Found {len(all_comments)} total comments across {page_num} pages"
        )
        return all_comments

    def get_top_upvoted_with_images(
        self, comments: List[Comment], limit: int = 50
    ) -> List[Comment]:
        """Get the most upvoted comments that have images."""
        image_comments = [c for c in comments if c.has_image]
        sorted_comments = sorted(
            image_comments,
            key=lambda x: (x.upvotes, -x.downvotes, len(x.image_urls)),
            reverse=True,
        )

        logger.info(f"Found {len(image_comments)} comments with images")
        logger.info(
            f"Returning top {min(limit, len(sorted_comments))} upvoted comments with images"
        )

        return sorted_comments[:limit]

    def save_results(self, comments: List[Comment], filename: str):
        """Save results to CSV."""
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "Author",
                    "Content",
                    "Upvotes",
                    "Downvotes",
                    "Timestamp",
                    "Has_Image",
                    "Image_Count",
                    "Image_URLs",
                    "Page_Number",
                    "Post_ID",
                ]
            )

            for comment in comments:
                writer.writerow(
                    [
                        comment.author,
                        (
                            comment.content[:500] + "..."
                            if len(comment.content) > 500
                            else comment.content
                        ),
                        comment.upvotes,
                        comment.downvotes,
                        comment.timestamp,
                        comment.has_image,
                        len(comment.image_urls),
                        ";".join(comment.image_urls),
                        comment.page_num,
                        comment.post_id,
                    ]
                )

        logger.info(f"Results saved to {filename}")

    def save_json_results(self, comments: List[Comment], filename: str):
        """Save results to JSON."""
        data = []
        for comment in comments:
            data.append(
                {
                    "author": comment.author,
                    "content": comment.content,
                    "upvotes": comment.upvotes,
                    "downvotes": comment.downvotes,
                    "timestamp": comment.timestamp,
                    "has_image": comment.has_image,
                    "image_urls": comment.image_urls,
                    "page_num": comment.page_num,
                    "post_id": comment.post_id,
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON results saved to {filename}")


def main():
    scraper = FixedWigglypaintScraper()

    # Test with a few pages first
    print("🔧 Testing fixed scraper with cursor-based pagination...")
    test_comments = scraper.scrape_all_comments_cursor(max_pages=5)

    if not test_comments:
        logger.error("No comments found. Check the scraper logic.")
        return

    # Remove duplicates by post_id
    unique_posts = {}
    for comment in test_comments:
        if comment.post_id not in unique_posts:
            unique_posts[comment.post_id] = comment

    # Statistics
    total_comments = len(test_comments)
    unique_count = len(unique_posts)
    comments_with_images = len([c for c in unique_posts.values() if c.has_image])

    print(f"\n✅ **FIXED SCRAPER TEST RESULTS:**")
    print(f"Total comments scraped: {total_comments}")
    print(f"Unique comments: {unique_count}")
    print(f"Comments with images: {comments_with_images}")
    print(f"Duplication ratio: {total_comments / unique_count:.1f}x (should be ~1.0)")

    if unique_count > 100:
        print("🎉 SUCCESS! Pagination is now working correctly!")

        # Get top upvoted with images
        top_comments = scraper.get_top_upvoted_with_images(
            list(unique_posts.values()), limit=20
        )

        print(f"\n🏆 **TOP 10 MOST UPVOTED POSTS WITH IMAGES:**")
        for i, comment in enumerate(top_comments[:10], 1):
            print(
                f"{i:2d}. {comment.author} (+{comment.upvotes}/-{comment.downvotes}): {comment.content[:60]}..."
            )
            if comment.image_urls:
                print(f"    Image: {comment.image_urls[0].split('/')[-1]}")

        # Save test results
        scraper.save_results(list(unique_posts.values()), "test_results.csv")
        scraper.save_results(top_comments, "top_comments.csv")

        print(f"\nTo run the FULL scrape with correct pagination, run:")
        print("python fixed_scraper.py --full")
    else:
        print("❌ Still issues with pagination. Need further investigation.")


if __name__ == "__main__":
    import sys

    if "--full" in sys.argv:
        scraper = FixedWigglypaintScraper()
        print("🚀 Running full scrape with corrected pagination...")
        all_comments = scraper.scrape_all_comments_cursor(max_pages=200)

        # Remove duplicates
        unique_posts = {}
        for comment in all_comments:
            if comment.post_id not in unique_posts:
                unique_posts[comment.post_id] = comment

        print(f"\n📊 **FINAL RESULTS:**")
        print(f"Total comments scraped: {len(all_comments)}")
        print(f"Unique comments: {len(unique_posts)}")
        print(
            f"Comments with images: {len([c for c in unique_posts.values() if c.has_image])}"
        )

        top_comments = scraper.get_top_upvoted_with_images(
            list(unique_posts.values()), limit=100
        )

        scraper.save_results(
            list(unique_posts.values()), "wigglypaint_all_comments.csv"
        )
        scraper.save_results(top_comments, "wigglypaint_top_comments.csv")
        scraper.save_json_results(top_comments, "wigglypaint_top_comments.json")

        print(f"🎉 Fixed scraping complete!")
    else:
        main()
