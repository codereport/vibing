#!/usr/bin/env python3
"""
Analyze the distribution of GitHub star counts for Thrust repositories
Creates histograms and statistical analysis of the star count distribution
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import pandas as pd


class StarDistributionAnalyzer:
    """Analyzes and visualizes the distribution of GitHub star counts"""

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
        stats = {
            "total_repos": len(self.star_counts),
            "total_stars": sum(self.star_counts),
            "mean": np.mean(self.star_counts),
            "median": np.median(self.star_counts),
            "std": np.std(self.star_counts),
            "min": min(self.star_counts),
            "max": max(self.star_counts),
            "q25": np.percentile(self.star_counts, 25),
            "q75": np.percentile(self.star_counts, 75),
        }

        # Star count categories
        stats["zero_stars"] = sum(1 for s in self.star_counts if s == 0)
        stats["low_stars"] = sum(1 for s in self.star_counts if 1 <= s <= 10)
        stats["medium_stars"] = sum(1 for s in self.star_counts if 11 <= s <= 100)
        stats["high_stars"] = sum(1 for s in self.star_counts if 101 <= s <= 1000)
        stats["very_high_stars"] = sum(1 for s in self.star_counts if s > 1000)

        return stats

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

    def create_visualizations(self, stats):
        """Create histogram and distribution visualizations"""
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "GitHub Star Count Distribution Analysis - Thrust Repositories",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Overall distribution histogram
        ax1.hist(
            self.star_counts, bins=50, alpha=0.7, color="steelblue", edgecolor="black"
        )
        ax1.set_title("Distribution of All Star Counts")
        ax1.set_xlabel("Number of Stars")
        ax1.set_ylabel("Number of Repositories")
        ax1.grid(True, alpha=0.3)

        # Add mean and median lines
        ax1.axvline(
            stats["mean"],
            color="red",
            linestyle="--",
            label=f'Mean: {stats["mean"]:.0f}',
        )
        ax1.axvline(
            stats["median"],
            color="green",
            linestyle="--",
            label=f'Median: {stats["median"]:.0f}',
        )
        ax1.legend()

        # 2. Log scale distribution (for better visualization of long tail)
        star_counts_nonzero = [s for s in self.star_counts if s > 0]
        if star_counts_nonzero:
            ax2.hist(
                star_counts_nonzero,
                bins=50,
                alpha=0.7,
                color="orange",
                edgecolor="black",
            )
            ax2.set_yscale("log")
            ax2.set_title("Distribution (Log Scale, Excluding Zero Stars)")
            ax2.set_xlabel("Number of Stars")
            ax2.set_ylabel("Number of Repositories (Log Scale)")
            ax2.grid(True, alpha=0.3)

        # 3. Categories pie chart
        categories = [
            "Zero\n(0)",
            "Low\n(1-10)",
            "Medium\n(11-100)",
            "High\n(101-1000)",
            "Very High\n(1000+)",
        ]
        sizes = [
            stats["zero_stars"],
            stats["low_stars"],
            stats["medium_stars"],
            stats["high_stars"],
            stats["very_high_stars"],
        ]
        colors = ["lightgray", "lightblue", "gold", "lightgreen", "salmon"]

        wedges, texts, autotexts = ax3.pie(
            sizes, labels=categories, colors=colors, autopct="%1.1f%%", startangle=90
        )
        ax3.set_title("Repository Distribution by Star Categories")

        # 4. Top repositories bar chart
        # Get top 15 repositories by stars
        top_repos = sorted(
            self.repositories, key=lambda x: x.get("stars", 0), reverse=True
        )[:15]
        top_names = [
            repo["name"].split("/")[-1][:20] for repo in top_repos
        ]  # Truncate long names
        top_stars = [repo["stars"] for repo in top_repos]

        bars = ax4.barh(range(len(top_names)), top_stars, color="darkblue", alpha=0.7)
        ax4.set_yticks(range(len(top_names)))
        ax4.set_yticklabels(top_names, fontsize=8)
        ax4.set_xlabel("Number of Stars")
        ax4.set_title("Top 15 Repositories by Stars")
        ax4.grid(True, alpha=0.3, axis="x")

        # Add star count labels on bars
        for i, (bar, stars) in enumerate(zip(bars, top_stars)):
            ax4.text(
                bar.get_width() + max(top_stars) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{stars:,}",
                va="center",
                fontsize=8,
            )

        plt.tight_layout()

        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thrust_star_distribution_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"\n📊 Visualization saved to: {filename}")

        # Show the plot
        plt.show()

    def create_detailed_analysis(self, stats):
        """Create additional detailed analysis"""
        print(f"\n🔍 DETAILED ANALYSIS:")
        print("-" * 50)

        # Skewness analysis
        from scipy import stats as scipy_stats

        skewness = scipy_stats.skew(self.star_counts)
        kurtosis = scipy_stats.kurtosis(self.star_counts)

        print(f"📈 Distribution Shape:")
        print(f"   Skewness: {skewness:.2f} (Right-skewed: high-star repos are rare)")
        print(f"   Kurtosis: {kurtosis:.2f} (Heavy-tailed distribution)")

        # Power law analysis
        print(f"\n⚡ Repository Popularity Insights:")
        print(
            f"   📊 {stats['very_high_stars']} repositories (≥1000 stars) account for"
        )
        total_high_stars = sum(s for s in self.star_counts if s >= 1000)
        print(
            f"      {total_high_stars:,} stars ({total_high_stars/stats['total_stars']*100:.1f}% of all stars)"
        )

        # Most common star ranges
        ranges = [
            (0, 0, "exactly 0 stars"),
            (1, 5, "1-5 stars"),
            (6, 25, "6-25 stars"),
            (26, 100, "26-100 stars"),
            (101, 500, "101-500 stars"),
            (501, 2000, "501-2000 stars"),
            (2001, float("inf"), "2000+ stars"),
        ]

        print(f"\n📊 Star Range Distribution:")
        for min_stars, max_stars, label in ranges:
            if max_stars == float("inf"):
                count = sum(1 for s in self.star_counts if s >= min_stars)
            else:
                count = sum(1 for s in self.star_counts if min_stars <= s <= max_stars)
            percentage = count / len(self.star_counts) * 100
            print(f"   {label:15}: {count:4} repos ({percentage:5.1f}%)")


def main():
    """Main function to run the analysis"""
    analyzer = StarDistributionAnalyzer("thrust_repos_with_stars_20250819_143818.json")

    try:
        # Load data
        analyzer.load_data()

        # Calculate statistics
        stats = analyzer.calculate_statistics()

        # Print statistics
        analyzer.print_statistics(stats)

        # Create visualizations
        analyzer.create_visualizations(stats)

        # Detailed analysis
        analyzer.create_detailed_analysis(stats)

        print(f"\n✅ Analysis completed!")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
