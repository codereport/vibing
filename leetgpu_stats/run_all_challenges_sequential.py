#!/usr/bin/env python3

import time
import json
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re


class SequentialAllChallengesScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.challenges = []
        self.all_results = []

        # Known working configuration
        self.frameworks = ["CUDA", "TRITON", "PYTORCH", "MOJO", "TINYGRAD"]
        self.gpus = [
            "NVIDIA TESLA T4",
            "NVIDIA A100-80GB",
            "NVIDIA H100",
            "NVIDIA H200",
            "NVIDIA B200",
        ]

    def setup_driver(self):
        """Setup Chrome driver with optimal settings"""
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 60)  # Increased timeout for 2FA
        return True

    def scrape_challenges_list(self):
        """Get list of all challenges from LeetGPU"""
        print("📋 Scraping challenges list from https://leetgpu.com/challenges")

        self.driver.get("https://leetgpu.com/challenges")
        self.wait.until(EC.presence_of_element_located((By.ID, "root")))
        time.sleep(10)  # Extra time for page to fully load

        try:
            challenge_links = []

            # Look for challenge links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if (
                    href
                    and "/challenges/" in href
                    and href != "https://leetgpu.com/challenges"
                ):
                    challenge_name = href.split("/challenges/")[-1]
                    if challenge_name and challenge_name not in [
                        c["name"] for c in challenge_links
                    ]:
                        title = (
                            link.text.strip()
                            or challenge_name.replace("-", " ").title()
                        )
                        challenge_links.append(
                            {"name": challenge_name, "url": href, "title": title}
                        )

            # Fallback to known challenges if needed
            if len(challenge_links) < 5:
                known_challenges = [
                    "vector-addition",
                    "matrix-multiplication",
                    "matrix-transpose",
                    "convolution-2d",
                    "reduce-sum",
                    "softmax",
                    "relu",
                    "sigmoid",
                    "elementwise-multiply",
                    "dot-product",
                    "cross-entropy",
                    "batch-normalization",
                    "layer-normalization",
                    "attention",
                ]
                for known in known_challenges:
                    url = f"https://leetgpu.com/challenges/{known}"
                    if known not in [c["name"] for c in challenge_links]:
                        challenge_links.append(
                            {
                                "name": known,
                                "url": url,
                                "title": known.replace("-", " ").title(),
                            }
                        )

            self.challenges = challenge_links
            print(f"✅ Found {len(self.challenges)} challenges to process")
            for i, challenge in enumerate(self.challenges, 1):
                print(f"  {i}. {challenge['title']} ({challenge['name']})")

            return len(self.challenges) > 0

        except Exception as e:
            print(f"❌ Error scraping challenges: {e}")
            # Use vector-addition as fallback
            self.challenges = [
                {
                    "name": "vector-addition",
                    "url": "https://leetgpu.com/challenges/vector-addition",
                    "title": "Vector Addition",
                }
            ]
            return True

    def authenticate_once(self):
        """Perform authentication once at the beginning"""
        print("🚀 Loading LeetGPU for authentication...")

        # Use first challenge for authentication
        if not self.challenges:
            print("❌ No challenges available for authentication")
            return False

        first_challenge_url = self.challenges[0]["url"]
        self.driver.get(first_challenge_url)

        self.wait.until(EC.presence_of_element_located((By.ID, "root")))
        time.sleep(10)  # Extra time for authentication page to load

        print("📋 Clicking Leaderboard (initial)...")
        try:
            leaderboard_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Leaderboard')]")
                )
            )
            self.driver.execute_script("arguments[0].click();", leaderboard_btn)
            time.sleep(8)  # Extra time for leaderboard to load
        except:
            print(
                "⚠️ Leaderboard button not found, checking if already authenticated..."
            )

        # Always force authentication check - don't assume it's complete
        print("🔐 Checking authentication status...")
        page_text = self.driver.find_element(By.TAG_NAME, "body").text

        # Look for signs that authentication is needed
        needs_auth = (
            "Sign In To Continue" in page_text
            or "Sign in with Github" in page_text
            or "Login" in page_text
            or "authenticate" in page_text.lower()
        )

        # Also check if we can see dropdown elements (sign of successful auth)
        has_dropdowns = False
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if button.is_displayed() and button.text:
                    text = button.text.strip()
                    if any(fw in text for fw in self.frameworks) or any(
                        gpu in text for gpu in ["NVIDIA", "Tesla", "T4"]
                    ):
                        has_dropdowns = True
                        break
        except:
            pass

        if needs_auth or not has_dropdowns:
            print("🔐 GitHub OAuth popup should have appeared automatically!")

            print("\n" + "=" * 70)
            print("🔑 GITHUB AUTHENTICATION - UNLIMITED TIME")
            print("   • GitHub OAuth popup appeared when you clicked Leaderboard")
            print("   • Enter your username/email and password")
            print("   • Complete 2FA (take as long as you need)")
            print("   • Wait for redirect back to LeetGPU")
            print("   • Look for the framework/GPU dropdown interface")
            print("   • NO TIME LIMITS - I'll wait forever!")
            print("=" * 70)

            # Wait indefinitely - no timeouts
            while True:
                response = input(
                    "Are you back on LeetGPU leaderboard with dropdowns? (y/n): "
                ).lower()
                if response == "y":
                    print("✅ Verifying authentication...")

                    # Verify authentication by checking for dropdowns
                    time.sleep(3)  # Brief pause to let page settle
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    auth_verified = False

                    for button in buttons:
                        if button.is_displayed() and button.text:
                            text = button.text.strip()
                            if any(fw in text for fw in self.frameworks) or any(
                                gpu in text for gpu in ["NVIDIA", "Tesla", "T4"]
                            ):
                                auth_verified = True
                                break

                    if auth_verified:
                        print("✅ Authentication verified! Dropdowns found.")
                        break
                    else:
                        print("❌ Authentication not complete - no dropdowns found.")
                        print("Please wait for the page to fully load and try again.")
                        continue

                elif response == "n":
                    print("⏳ Take your time - I'll keep waiting...")
                    continue
                else:
                    print("Please enter 'y' when ready or 'n' to keep waiting...")
        else:
            print("✅ Authentication already complete - dropdowns detected!")

        print("✅ Authentication complete!")
        return True

    def run_single_challenge(self, challenge):
        """Run 25 combinations for a single challenge using the working approach"""
        print(f"\n🎯 Processing challenge: {challenge['title']}")
        print(f"   URL: {challenge['url']}")

        # Navigate to challenge
        self.driver.get(challenge["url"])
        self.wait.until(EC.presence_of_element_located((By.ID, "root")))
        time.sleep(10)  # Extra time for challenge page to fully load

        # Click leaderboard
        try:
            leaderboard_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Leaderboard')]")
                )
            )
            self.driver.execute_script("arguments[0].click();", leaderboard_btn)
            time.sleep(8)  # Extra time for leaderboard interface to load
        except:
            print("⚠️ Could not access leaderboard interface")
            return []

        # Run all 25 combinations
        challenge_results = []
        combination_count = 0

        for framework in self.frameworks:
            for gpu in self.gpus:
                combination_count += 1
                print(f"  ⏳ [{combination_count}/25] {framework} + {gpu}", end=" ")

                # Find dropdown buttons
                framework_button, gpu_button = self.find_dropdown_buttons()

                if not framework_button or not gpu_button:
                    print("❌ No buttons")
                    continue

                # Select framework and GPU
                framework_success = self.select_framework(framework_button, framework)
                framework_button, gpu_button = (
                    self.find_dropdown_buttons()
                )  # Re-find after selection
                gpu_success = self.select_gpu(gpu_button, gpu)

                # Extract runtime
                fastest_time, fastest_ms, total_timings = self.extract_current_runtime()

                result = {
                    "challenge_name": challenge["name"],
                    "challenge_title": challenge["title"],
                    "challenge_url": challenge["url"],
                    "combination_number": combination_count,
                    "framework": framework,
                    "gpu": gpu,
                    "fastest_time": fastest_time,
                    "fastest_ms": fastest_ms,
                    "total_timings_found": total_timings,
                    "framework_selected": framework_success,
                    "gpu_selected": gpu_success,
                    "timestamp": datetime.now().isoformat(),
                }

                challenge_results.append(result)
                self.all_results.append(result)

                if fastest_time:
                    print(f"⚡ {fastest_time}")
                else:
                    print("❌ No data")

        # Summary for this challenge
        valid_results = [r for r in challenge_results if r["fastest_ms"] is not None]
        if valid_results:
            fastest = min(valid_results, key=lambda x: x["fastest_ms"])
            print(
                f"  🏆 Challenge fastest: {fastest['framework']} on {fastest['gpu']} - {fastest['fastest_time']}"
            )
            print(f"  📊 Valid results: {len(valid_results)}/25")
        else:
            print(f"  ⚠️ No valid results for {challenge['name']}")

        return challenge_results

    def find_dropdown_buttons(self):
        """Find framework and GPU dropdown buttons"""
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            framework_button = None
            gpu_button = None

            for button in buttons:
                if button.is_displayed() and button.text:
                    text = button.text.strip()
                    if any(fw in text for fw in self.frameworks):
                        framework_button = button
                    elif any(
                        gpu in text
                        for gpu in [
                            "NVIDIA",
                            "Tesla",
                            "T4",
                            "RTX",
                            "A100",
                            "H100",
                            "H200",
                            "B200",
                        ]
                    ):
                        gpu_button = button

            return framework_button, gpu_button
        except Exception:
            return None, None

    def select_framework(self, framework_button, framework):
        """Select a specific framework from dropdown"""
        try:
            self.driver.execute_script("arguments[0].click();", framework_button)
            time.sleep(2)
            option_xpath = f"//div[contains(@class, 'cursor-pointer') and normalize-space(text())='{framework}']"
            option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            self.driver.execute_script("arguments[0].click();", option)
            time.sleep(3)
            return True
        except Exception:
            return False

    def select_gpu(self, gpu_button, gpu):
        """Select a specific GPU from dropdown"""
        try:
            self.driver.execute_script("arguments[0].click();", gpu_button)
            time.sleep(2)
            option_xpath = f"//div[contains(@class, 'cursor-pointer')]//span[contains(@class, 'truncate') and normalize-space(text())='{gpu}']"
            option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            self.driver.execute_script("arguments[0].click();", option)
            time.sleep(3)
            return True
        except Exception:
            return False

    def extract_current_runtime(self):
        """Extract the fastest runtime from current leaderboard"""
        try:
            time.sleep(3)
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            timing_patterns = [
                r"(\d+\.?\d*)\s*ms",
                r"(\d+\.?\d*)\s*μs",
                r"(\d+\.?\d*)\s*us",
            ]

            all_times = []
            for pattern in timing_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    try:
                        value = float(match)
                        unit = re.search(r"(ms|μs|us)", pattern, re.IGNORECASE).group(1)
                        all_times.append({"value": value, "unit": unit})
                    except:
                        continue

            if all_times:
                fastest_ms = float("inf")
                fastest_original = None

                for t in all_times:
                    if "ms" in t["unit"].lower():
                        ms_val = t["value"]
                    elif "μs" in t["unit"] or "us" in t["unit"]:
                        ms_val = t["value"] / 1000
                    else:
                        ms_val = t["value"]

                    if ms_val < fastest_ms:
                        fastest_ms = ms_val
                        fastest_original = f"{t['value']} {t['unit']}"

                return fastest_original, fastest_ms, len(all_times)

            return None, None, 0
        except Exception:
            return None, None, 0

    def save_results(self):
        """Save all results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save comprehensive JSON
        json_file = f"all_challenges_results_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(
                {
                    "collection_timestamp": datetime.now().isoformat(),
                    "total_challenges": len(self.challenges),
                    "total_combinations": len(self.all_results),
                    "challenges": self.challenges,
                    "results": self.all_results,
                },
                f,
                indent=2,
            )

        # Save CSV
        csv_file = f"all_challenges_results_{timestamp}.csv"
        if self.all_results:
            with open(csv_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.all_results[0].keys())
                writer.writeheader()
                writer.writerows(self.all_results)

        print(f"\n💾 Results saved:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")

        return json_file, csv_file

    def run(self):
        """Main execution method"""
        try:
            print("🚀 Sequential All Challenges LeetGPU Scraper")
            print("=" * 60)
            print("🎯 Will collect data for ALL challenges:")
            print("   • 36 challenges from LeetGPU")
            print("   • 25 combinations per challenge (5 frameworks × 5 GPUs)")
            print("   • Total: ~900 combinations")
            print("   • Uses proven single-challenge approach")
            print()
            print("⚠️  Requires GitHub authentication")
            print("⏰ Estimated time: 2-3 hours")
            print("=" * 60)

            if input("\nProceed with full collection? (y/n): ").lower() != "y":
                print("❌ Collection cancelled")
                return

            # Setup
            self.setup_driver()

            # Get challenges
            if not self.scrape_challenges_list():
                print("❌ Failed to get challenges list")
                return

            # Authenticate once
            if not self.authenticate_once():
                print("❌ Authentication failed")
                return

            # Process each challenge
            print(f"\n🚀 Starting collection of {len(self.challenges)} challenges...")

            for i, challenge in enumerate(self.challenges, 1):
                print(f"\n{'='*60}")
                print(f"📋 Challenge {i}/{len(self.challenges)}: {challenge['title']}")
                print(f"{'='*60}")

                challenge_results = self.run_single_challenge(challenge)

                # Save intermediate results
                if i % 5 == 0:  # Save every 5 challenges
                    self.save_results()
                    print(
                        f"💾 Intermediate save completed ({i}/{len(self.challenges)} challenges)"
                    )

            # Final save
            json_file, csv_file = self.save_results()

            # Final summary
            print(f"\n🎉 COLLECTION COMPLETE!")
            print(f"={'='*60}")
            print(f"📊 Total challenges processed: {len(self.challenges)}")
            print(f"📊 Total combinations collected: {len(self.all_results)}")

            valid_results = [r for r in self.all_results if r["fastest_ms"] is not None]
            print(f"📊 Valid results: {len(valid_results)}")
            print(
                f"📊 Success rate: {len(valid_results)/len(self.all_results)*100:.1f}%"
            )

            if valid_results:
                fastest = min(valid_results, key=lambda x: x["fastest_ms"])
                print(
                    f"🏆 Overall fastest: {fastest['challenge_title']} - {fastest['framework']} on {fastest['gpu']} - {fastest['fastest_time']}"
                )

            input("\nPress Enter to close browser...")

        finally:
            if self.driver:
                self.driver.quit()


def main():
    scraper = SequentialAllChallengesScraper()
    scraper.run()


if __name__ == "__main__":
    main()
