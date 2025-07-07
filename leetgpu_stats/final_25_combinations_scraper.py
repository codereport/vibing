#!/usr/bin/env python3

import time
import json
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import os


class Final25CombinationsScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.results = []

        # Discovered options from dropdown tests
        self.frameworks = ["CUDA", "TRITON", "PYTORCH", "MOJO", "TINYGRAD"]
        self.gpus = [
            "NVIDIA TESLA T4",
            "NVIDIA A100-80GB",
            "NVIDIA H100",
            "NVIDIA H200",
            "NVIDIA B200",
        ]

    def setup_driver(self):
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 30)
        return True

    def authenticate(self):
        print("🚀 Loading LeetGPU...")
        self.driver.get("https://leetgpu.com/challenges/vector-addition")

        self.wait.until(EC.presence_of_element_located((By.ID, "root")))
        time.sleep(5)

        print("📋 Clicking Leaderboard (initial)...")
        leaderboard_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Leaderboard')]")
            )
        )
        self.driver.execute_script("arguments[0].click();", leaderboard_btn)
        time.sleep(3)

        page_text = self.driver.find_element(By.TAG_NAME, "body").text

        if "Sign In To Continue" in page_text:
            print("🔐 GitHub authentication required...")
            github_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Sign in with Github')]")
                )
            )
            self.driver.execute_script("arguments[0].click();", github_btn)

            print("\n" + "=" * 50)
            print("🔑 Complete GitHub authentication in browser")
            print("Press Enter when back on LeetGPU...")
            print("=" * 50)
            input()
            time.sleep(3)

        print("✅ Authentication complete!")
        return True

    def access_leaderboard_interface(self):
        """Click leaderboard button after authentication to access dropdown interface"""
        print("📋 Accessing leaderboard interface with dropdowns...")

        try:
            leaderboard_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Leaderboard')]")
                )
            )
            self.driver.execute_script("arguments[0].click();", leaderboard_btn)
            time.sleep(5)

            print("✅ Leaderboard interface loaded")
            return True

        except Exception as e:
            print(f"❌ Error accessing leaderboard interface: {e}")
            return False

    def find_dropdown_buttons(self):
        """Find framework and GPU dropdown buttons"""
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")

            framework_button = None
            gpu_button = None

            for button in buttons:
                if button.is_displayed() and button.text:
                    text = button.text.strip()

                    # Check for framework button
                    if any(
                        fw in text
                        for fw in ["CUDA", "TRITON", "PYTORCH", "MOJO", "TINYGRAD"]
                    ):
                        framework_button = button
                        print(f"✅ Framework button: {text}")

                    # Check for GPU button
                    elif any(
                        gpu in text
                        for gpu in ["NVIDIA", "Tesla", "T4", "RTX", "A100", "H100"]
                    ):
                        gpu_button = button
                        print(f"✅ GPU button: {text}")

            return framework_button, gpu_button

        except Exception as e:
            print(f"❌ Error finding buttons: {e}")
            return None, None

    def select_framework(self, framework_button, framework):
        """Select a specific framework from dropdown"""
        try:
            print(f"🔧 Selecting framework: {framework}")

            # Click button to open dropdown
            self.driver.execute_script("arguments[0].click();", framework_button)
            time.sleep(2)

            # Look for framework option with exact text match
            # Framework options are direct text in divs with cursor-pointer class
            option_xpath = f"//div[contains(@class, 'cursor-pointer') and normalize-space(text())='{framework}']"

            try:
                option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath))
                )
                self.driver.execute_script("arguments[0].click();", option)
                time.sleep(3)  # Wait for leaderboard to update
                print(f"    ✅ Selected: {framework}")
                return True
            except Exception as e:
                print(f"    ❌ Could not select framework {framework}: {e}")
                # Try to close dropdown by clicking button again
                self.driver.execute_script("arguments[0].click();", framework_button)
                time.sleep(1)
                return False

        except Exception as e:
            print(f"❌ Error selecting framework: {e}")
            return False

    def select_gpu(self, gpu_button, gpu):
        """Select a specific GPU from dropdown"""
        try:
            print(f"🖥️  Selecting GPU: {gpu}")

            # Click button to open dropdown
            self.driver.execute_script("arguments[0].click();", gpu_button)
            time.sleep(2)

            # Look for GPU option - text is inside span with class="truncate"
            option_xpath = f"//div[contains(@class, 'cursor-pointer')]//span[contains(@class, 'truncate') and normalize-space(text())='{gpu}']"

            try:
                option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath))
                )
                self.driver.execute_script("arguments[0].click();", option)
                time.sleep(3)  # Wait for leaderboard to update
                print(f"    ✅ Selected: {gpu}")
                return True
            except Exception as e:
                print(f"    ❌ Could not select GPU {gpu}: {e}")
                # Try to close dropdown by clicking button again
                self.driver.execute_script("arguments[0].click();", gpu_button)
                time.sleep(1)
                return False

        except Exception as e:
            print(f"❌ Error selecting GPU: {e}")
            return False

    def extract_current_runtime(self):
        """Extract the fastest runtime from current leaderboard"""
        try:
            time.sleep(3)
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Look for timing patterns
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
                # Find fastest time
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

        except Exception as e:
            print(f"❌ Error extracting runtime: {e}")
            return None, None, 0

    def collect_all_25_combinations(self):
        """Collect runtime data for all 25 framework/GPU combinations"""
        print("\n" + "=" * 60)
        print("🚀 COLLECTING ALL 25 LEETGPU RUNTIME COMBINATIONS")
        print("=" * 60)
        print(f"📋 Frameworks: {self.frameworks}")
        print(f"🖥️  GPUs: {self.gpus}")
        print(
            f"📊 Total combinations: {len(self.frameworks)} × {len(self.gpus)} = {len(self.frameworks) * len(self.gpus)}"
        )
        print("=" * 60)

        combination_count = 0

        for framework in self.frameworks:
            for gpu in self.gpus:
                combination_count += 1
                print(
                    f"\n⏳ [{combination_count}/{len(self.frameworks) * len(self.gpus)}] Testing: {framework} + {gpu}"
                )

                # Find dropdown buttons
                framework_button, gpu_button = self.find_dropdown_buttons()

                if not framework_button or not gpu_button:
                    print("❌ Could not find dropdown buttons")
                    continue

                # Select framework
                framework_success = self.select_framework(framework_button, framework)

                # Re-find buttons as they may have changed after selection
                framework_button, gpu_button = self.find_dropdown_buttons()

                # Select GPU
                gpu_success = self.select_gpu(gpu_button, gpu)

                # Extract runtime
                fastest_time, fastest_ms, total_timings = self.extract_current_runtime()

                result = {
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

                self.results.append(result)

                if fastest_time:
                    print(f"    ⚡ Runtime: {fastest_time} ({fastest_ms:.6f} ms)")
                else:
                    print("    ❌ No runtime data found")

        print(f"\n✅ Collection complete! {len(self.results)} combinations collected")
        return True

    def save_and_display_results(self):
        """Save comprehensive results and display summary"""
        os.makedirs("leetgpu_stats", exist_ok=True)

        # Save to JSON
        with open("leetgpu_stats/final_25_combinations.json", "w") as f:
            json.dump(
                {
                    "collection_timestamp": datetime.now().isoformat(),
                    "total_combinations": len(self.results),
                    "frameworks_tested": self.frameworks,
                    "gpus_tested": self.gpus,
                    "results": self.results,
                },
                f,
                indent=2,
            )

        # Save to CSV
        with open("leetgpu_stats/final_25_combinations.csv", "w", newline="") as f:
            fieldnames = [
                "combination_number",
                "framework",
                "gpu",
                "fastest_time",
                "fastest_ms",
                "total_timings_found",
                "framework_selected",
                "gpu_selected",
                "timestamp",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

        # Display comprehensive results
        print("\n" + "=" * 80)
        print("🏆 ALL 25 LEETGPU VECTOR ADDITION RUNTIME COMBINATIONS")
        print("=" * 80)

        # Group by framework
        for framework in self.frameworks:
            framework_results = [r for r in self.results if r["framework"] == framework]
            print(f"\n🔧 {framework}:")
            print("-" * 50)

            for result in framework_results:
                status = (
                    "✅"
                    if result["framework_selected"] and result["gpu_selected"]
                    else "⚠️"
                )
                if result["fastest_time"]:
                    print(f"  {status} {result['gpu']}: {result['fastest_time']}")
                else:
                    print(f"  {status} {result['gpu']}: No data")

        # Overall fastest
        valid_results = [r for r in self.results if r["fastest_ms"] is not None]
        if valid_results:
            fastest = min(valid_results, key=lambda x: x["fastest_ms"])
            print(f"\n🥇 OVERALL FASTEST RUNTIME:")
            print(f"   {fastest['framework']} on {fastest['gpu']}")
            print(
                f"   Time: {fastest['fastest_time']} ({fastest['fastest_ms']:.6f} ms)"
            )

        # Summary statistics
        successful_selections = [
            r for r in self.results if r["framework_selected"] and r["gpu_selected"]
        ]
        print(f"\n📊 COLLECTION SUMMARY:")
        print(f"   Total combinations: {len(self.results)}")
        print(f"   Successful selections: {len(successful_selections)}")
        print(f"   Valid timing data: {len(valid_results)}")
        print(
            f"   Success rate: {len(successful_selections)/len(self.results)*100:.1f}%"
        )

        print("\n💾 Results saved to:")
        print("  • leetgpu_stats/final_25_combinations.json")
        print("  • leetgpu_stats/final_25_combinations.csv")
        print("=" * 80)

    def run(self):
        try:
            self.setup_driver()
            self.authenticate()
            self.access_leaderboard_interface()
            self.collect_all_25_combinations()
            self.save_and_display_results()

            input("\nPress Enter to close browser...")

        finally:
            if self.driver:
                self.driver.quit()


def main():
    print("🎯 Final 25 Combinations LeetGPU Scraper")
    print("=" * 50)
    print("🚀 Will collect ALL 25 runtime combinations:")
    print("   • 5 Frameworks: CUDA, TRITON, PYTORCH, MOJO, TINYGRAD")
    print("   • 5 GPUs: NVIDIA TESLA T4, A100-80GB, H100, H200, B200")
    print("   • Total: 25 combinations")
    print("\n🔧 Uses discovered dropdown structure:")
    print("   • Framework options: cursor-pointer class, direct text")
    print("   • GPU options: cursor-pointer class, span.truncate text")
    print("\n⚠️  Requires GitHub authentication")
    print("=" * 50)

    if input("\nProceed with final 25-combination collection? (y/n): ").lower() == "y":
        scraper = Final25CombinationsScraper()
        scraper.run()


if __name__ == "__main__":
    main()
