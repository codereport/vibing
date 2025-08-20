#!/usr/bin/env python3
"""
Simple analysis of GitHub star distribution for Thrust repositories
Provides statistical analysis without heavy dependencies
"""

import json
import math
from collections import Counter
from datetime import datetime


class SimpleStarAnalyzer:
    """Simple analyzer for star distribution without heavy dependencies"""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self.repositories = []
        self.star_counts = []

    def load_data(self):
        """Load repository data from JSON file"""
        print(f"📖 Loading repository data from {self.data_file}")

        with open(self.data_file, "r") as f:
            data = json.load(f)

        self.repositories = data.get("repositories", [])
        # Filter out repositories with negative star counts (not found repos)
        valid_repos = [repo for repo in self.repositories if repo.get("stars", 0) >= 0]
        self.star_counts = [repo["stars"] for repo in valid_repos]

        print(f"✅ Loaded {len(valid_repos)} valid repositories")
        print(
            f"⚠️  Filtered out {len(self.repositories) - len(valid_repos)} repositories with missing data"
        )

    def calculate_statistics(self):
        """Calculate descriptive statistics for star counts"""
        n = len(self.star_counts)
        total = sum(self.star_counts)
        sorted_stars = sorted(self.star_counts)

        # Basic statistics
        stats = {
            "total_repos": n,
            "total_stars": total,
            "mean": total / n if n > 0 else 0,
            "median": self._median(sorted_stars),
            "std": self._std(self.star_counts),
            "min": min(self.star_counts) if self.star_counts else 0,
            "max": max(self.star_counts) if self.star_counts else 0,
            "q25": self._percentile(sorted_stars, 25),
            "q75": self._percentile(sorted_stars, 75),
        }

        # Star count categories
        stats["zero_stars"] = sum(1 for s in self.star_counts if s == 0)
        stats["low_stars"] = sum(1 for s in self.star_counts if 1 <= s <= 10)
        stats["medium_stars"] = sum(1 for s in self.star_counts if 11 <= s <= 100)
        stats["high_stars"] = sum(1 for s in self.star_counts if 101 <= s <= 1000)
        stats["very_high_stars"] = sum(1 for s in self.star_counts if s > 1000)

        # Additional insights
        stats["median_nonzero"] = self._median([s for s in sorted_stars if s > 0])
        stats["geometric_mean"] = self._geometric_mean(
            [s for s in self.star_counts if s > 0]
        )

        return stats

    def _median(self, sorted_list):
        """Calculate median of a sorted list"""
        if not sorted_list:
            return 0
        n = len(sorted_list)
        if n % 2 == 0:
            return (sorted_list[n // 2 - 1] + sorted_list[n // 2]) / 2
        else:
            return sorted_list[n // 2]

    def _percentile(self, sorted_list, p):
        """Calculate percentile of a sorted list"""
        if not sorted_list:
            return 0
        n = len(sorted_list)
        k = (n - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        return sorted_list[int(f)] * (c - k) + sorted_list[int(c)] * (k - f)

    def _std(self, values):
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _geometric_mean(self, values):
        """Calculate geometric mean (for positive values only)"""
        if not values:
            return 0
        # Use logarithms to avoid overflow
        log_sum = sum(math.log(val) for val in values if val > 0)
        return math.exp(log_sum / len(values))

    def print_statistics(self, stats):
        """Print detailed statistics"""
        print("\n" + "=" * 70)
        print("📊 GITHUB STAR COUNT DISTRIBUTION ANALYSIS")
        print("=" * 70)

        print(f"📈 Basic Statistics:")
        print(f"   Total Repositories: {stats['total_repos']:,}")
        print(f"   Total Stars: {stats['total_stars']:,}")
        print(f"   Mean Stars: {stats['mean']:.1f}")
        print(f"   Median Stars: {stats['median']:.1f}")
        print(f"   Standard Deviation: {stats['std']:.1f}")
        print(f"   Min Stars: {stats['min']:,}")
        print(f"   Max Stars: {stats['max']:,}")

        print(f"\n📊 Percentiles:")
        print(f"   25th Percentile: {stats['q25']:.1f}")
        print(f"   50th Percentile (Median): {stats['median']:.1f}")
        print(f"   75th Percentile: {stats['q75']:.1f}")

        if stats["median_nonzero"] > 0:
            print(f"   Median (excluding zero): {stats['median_nonzero']:.1f}")
        if stats["geometric_mean"] > 0:
            print(f"   Geometric Mean (positive only): {stats['geometric_mean']:.1f}")

        print(f"\n🏷️  Star Count Categories:")
        print(
            f"   Zero stars (0): {stats['zero_stars']:,} repos ({stats['zero_stars']/stats['total_repos']*100:.1f}%)"
        )
        print(
            f"   Low stars (1-10): {stats['low_stars']:,} repos ({stats['low_stars']/stats['total_repos']*100:.1f}%)"
        )
        print(
            f"   Medium stars (11-100): {stats['medium_stars']:,} repos ({stats['medium_stars']/stats['total_repos']*100:.1f}%)"
        )
        print(
            f"   High stars (101-1000): {stats['high_stars']:,} repos ({stats['high_stars']/stats['total_repos']*100:.1f}%)"
        )
        print(
            f"   Very high stars (1000+): {stats['very_high_stars']:,} repos ({stats['very_high_stars']/stats['total_repos']*100:.1f}%)"
        )

    def create_text_histogram(self):
        """Create a simple text-based histogram"""
        print(f"\n📊 STAR COUNT DISTRIBUTION HISTOGRAM (Text Version)")
        print("-" * 70)

        # Define bins
        bins = [
            0,
            1,
            5,
            10,
            25,
            50,
            100,
            250,
            500,
            1000,
            2500,
            5000,
            10000,
            float("inf"),
        ]
        bin_labels = [
            "0",
            "1-4",
            "5-9",
            "10-24",
            "25-49",
            "50-99",
            "100-249",
            "250-499",
            "500-999",
            "1K-2.5K",
            "2.5K-5K",
            "5K-10K",
            "10K+",
        ]

        # Count repositories in each bin
        bin_counts = [0] * (len(bins) - 1)
        for stars in self.star_counts:
            for i in range(len(bins) - 1):
                if bins[i] <= stars < bins[i + 1]:
                    bin_counts[i] += 1
                    break

        # Find max count for scaling
        max_count = max(bin_counts) if bin_counts else 1
        max_bar_length = 50

        # Print histogram
        print(f"{'Range':>10} {'Count':>6} {'%':>6} {'Distribution':>12}")
        print("-" * 70)

        for i, (label, count) in enumerate(zip(bin_labels, bin_counts)):
            percentage = (
                (count / len(self.star_counts)) * 100 if self.star_counts else 0
            )
            bar_length = (
                int((count / max_count) * max_bar_length) if max_count > 0 else 0
            )
            bar = "█" * bar_length

            print(f"{label:>10} {count:>6} {percentage:>5.1f}% {bar}")

    def analyze_top_repositories(self, top_n=20):
        """Analyze top repositories by star count"""
        print(f"\n🏆 TOP {top_n} REPOSITORIES BY STARS")
        print("-" * 70)

        # Sort repositories by stars
        top_repos = sorted(
            self.repositories, key=lambda x: x.get("stars", 0), reverse=True
        )[:top_n]

        print(f"{'Rank':>4} {'Stars':>8} {'Repository':>35} {'Language':>12}")
        print("-" * 70)

        for i, repo in enumerate(top_repos, 1):
            stars = repo.get("stars", 0)
            name = repo.get("name", "Unknown")[:35]
            language = repo.get("language", "Unknown")[:12]
            print(f"{i:>4} {stars:>8,} {name:>35} {language:>12}")

    def analyze_detailed_ranges(self):
        """Provide detailed analysis of star ranges"""
        print(f"\n🔍 DETAILED STAR RANGE ANALYSIS")
        print("-" * 50)

        ranges = [
            (0, 0, "exactly 0 stars"),
            (1, 1, "exactly 1 star"),
            (2, 5, "2-5 stars"),
            (6, 10, "6-10 stars"),
            (11, 25, "11-25 stars"),
            (26, 50, "26-50 stars"),
            (51, 100, "51-100 stars"),
            (101, 250, "101-250 stars"),
            (251, 500, "251-500 stars"),
            (501, 1000, "501-1000 stars"),
            (1001, 2500, "1001-2500 stars"),
            (2501, 5000, "2501-5000 stars"),
            (5001, 10000, "5001-10000 stars"),
            (10001, float("inf"), "10000+ stars"),
        ]

        total_repos = len(self.star_counts)
        cumulative = 0

        print(f"{'Range':>15} {'Count':>7} {'%':>7} {'Cumulative %':>12}")
        print("-" * 50)

        for min_stars, max_stars, label in ranges:
            if max_stars == float("inf"):
                count = sum(1 for s in self.star_counts if s >= min_stars)
            else:
                count = sum(1 for s in self.star_counts if min_stars <= s <= max_stars)

            percentage = (count / total_repos) * 100 if total_repos > 0 else 0
            cumulative += percentage

            if count > 0:  # Only show ranges with repositories
                print(
                    f"{label:>15}: {count:>6} ({percentage:>5.1f}%) (cum: {cumulative:>5.1f}%)"
                )

    def power_law_analysis(self, stats):
        """Simple power-law/Pareto analysis"""
        print(f"\n⚡ POWER LAW / PARETO ANALYSIS")
        print("-" * 50)

        # 80/20 rule analysis
        sorted_stars = sorted(self.star_counts, reverse=True)
        total_stars = sum(sorted_stars)

        # Find how many repos account for 80% of stars
        cumulative_stars = 0
        repos_for_80_percent = 0

        for i, stars in enumerate(sorted_stars):
            cumulative_stars += stars
            if cumulative_stars >= 0.8 * total_stars:
                repos_for_80_percent = i + 1
                break

        print(f"📊 Pareto Analysis (80/20 Rule):")
        print(
            f"   Top {repos_for_80_percent} repositories ({repos_for_80_percent/len(self.star_counts)*100:.1f}%)"
        )
        print(
            f"   Account for {cumulative_stars:,} stars ({cumulative_stars/total_stars*100:.1f}% of total)"
        )

        # Top percentiles
        for pct in [1, 5, 10, 25]:
            n_repos = max(1, int(len(sorted_stars) * pct / 100))
            top_stars = sum(sorted_stars[:n_repos])
            print(
                f"   Top {pct}% ({n_repos} repos): {top_stars:,} stars ({top_stars/total_stars*100:.1f}% of total)"
            )


def main():
    """Main function to run the analysis"""
    analyzer = SimpleStarAnalyzer("thrust_repos_with_stars_20250819_143818.json")

    try:
        # Load data
        analyzer.load_data()

        # Calculate statistics
        stats = analyzer.calculate_statistics()

        # Print statistics
        analyzer.print_statistics(stats)

        # Create text histogram
        analyzer.create_text_histogram()

        # Top repositories
        analyzer.analyze_top_repositories(20)

        # Detailed range analysis
        analyzer.analyze_detailed_ranges()

        # Power law analysis
        analyzer.power_law_analysis(stats)

        print(f"\n✅ Analysis completed!")
        print(
            f"💡 For graphical visualization, install matplotlib and run analyze_star_distribution.py"
        )

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
