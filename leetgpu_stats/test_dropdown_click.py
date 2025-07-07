#!/usr/bin/env python3

import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os


class DropdownTestScraper:
    def __init__(self):
        self.driver = None
        self.wait = None

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

            print(f"🔍 Found {len(buttons)} total buttons:")

            for i, button in enumerate(buttons):
                if button.is_displayed() and button.text:
                    text = button.text.strip()
                    print(f"  Button {i+1}: '{text}'")

                    # Check for framework button
                    if any(
                        fw in text
                        for fw in ["CUDA", "Triton", "PyTorch", "Mojo", "TinyGrad"]
                    ):
                        framework_button = button
                        print(f"    ✅ Framework button: {text}")

                    # Check for GPU button
                    elif any(
                        gpu in text
                        for gpu in ["NVIDIA", "Tesla", "T4", "RTX", "A100", "H100"]
                    ):
                        gpu_button = button
                        print(f"    ✅ GPU button: {text}")

            return framework_button, gpu_button

        except Exception as e:
            print(f"❌ Error finding buttons: {e}")
            return None, None

    def save_page_state(self, step_name):
        """Save screenshot and HTML for analysis"""
        os.makedirs("dropdown_test", exist_ok=True)

        # Save screenshot
        screenshot_path = f"dropdown_test/{step_name}.png"
        self.driver.save_screenshot(screenshot_path)
        print(f"📸 Screenshot: {screenshot_path}")

        # Save HTML
        html_path = f"dropdown_test/{step_name}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"📄 HTML: {html_path}")

    def test_framework_dropdown(self, framework_button):
        """Test clicking framework dropdown and discover options"""
        print("\n🧪 TESTING FRAMEWORK DROPDOWN")
        print("=" * 40)

        try:
            print(f"📋 Current framework button text: '{framework_button.text}'")

            # Save state before clicking
            self.save_page_state("before_framework_click")

            print("🖱️  Clicking framework button...")
            self.driver.execute_script("arguments[0].click();", framework_button)
            time.sleep(3)

            # Save state after clicking
            self.save_page_state("after_framework_click")

            # Look for new elements that appeared
            print("🔍 Searching for dropdown options...")

            # Try different selectors
            selectors = [
                ("Role-based options", "//div[@role='option']"),
                ("List options", "//li[@role='option']"),
                ("Class-based options", "//div[contains(@class, 'option')]"),
                ("Menu items", "//div[contains(@class, 'menu')]//div"),
                ("Dropdown items", "//div[contains(@class, 'dropdown')]//div"),
                ("List items", "//ul//li"),
                ("Any clickable divs", "//div[@onclick or @role='button']"),
            ]

            all_options = []

            for selector_name, selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"  {selector_name}: Found {len(elements)} elements")

                    for i, elem in enumerate(elements):
                        if elem.is_displayed():
                            text = elem.text.strip()
                            if text and len(text) > 0:
                                print(f"    {i+1}. '{text}' (tag: {elem.tag_name})")
                                if text not in all_options:
                                    all_options.append(text)
                except Exception as e:
                    print(f"  {selector_name}: Error - {e}")

            print(f"\n📊 Total unique options found: {len(all_options)}")
            for i, option in enumerate(all_options):
                print(f"  {i+1}. {option}")

            # Close dropdown by clicking button again
            print("\n🔄 Closing dropdown...")
            self.driver.execute_script("arguments[0].click();", framework_button)
            time.sleep(2)

            return all_options

        except Exception as e:
            print(f"❌ Error testing framework dropdown: {e}")
            return []

    def test_gpu_dropdown(self, gpu_button):
        """Test clicking GPU dropdown and discover options"""
        print("\n🧪 TESTING GPU DROPDOWN")
        print("=" * 40)

        try:
            print(f"📋 Current GPU button text: '{gpu_button.text}'")

            # Save state before clicking
            self.save_page_state("before_gpu_click")

            print("🖱️  Clicking GPU button...")
            self.driver.execute_script("arguments[0].click();", gpu_button)
            time.sleep(3)

            # Save state after clicking
            self.save_page_state("after_gpu_click")

            # Look for new elements that appeared
            print("🔍 Searching for dropdown options...")

            selectors = [
                ("Role-based options", "//div[@role='option']"),
                ("List options", "//li[@role='option']"),
                ("Class-based options", "//div[contains(@class, 'option')]"),
                ("Menu items", "//div[contains(@class, 'menu')]//div"),
                ("Dropdown items", "//div[contains(@class, 'dropdown')]//div"),
                ("List items", "//ul//li"),
            ]

            all_options = []

            for selector_name, selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"  {selector_name}: Found {len(elements)} elements")

                    for i, elem in enumerate(elements):
                        if elem.is_displayed():
                            text = elem.text.strip()
                            if text and len(text) > 0:
                                print(f"    {i+1}. '{text}' (tag: {elem.tag_name})")
                                if text not in all_options:
                                    all_options.append(text)
                except Exception as e:
                    print(f"  {selector_name}: Error - {e}")

            print(f"\n📊 Total unique GPU options found: {len(all_options)}")
            for i, option in enumerate(all_options):
                print(f"  {i+1}. {option}")

            # Close dropdown by clicking button again
            print("\n🔄 Closing dropdown...")
            self.driver.execute_script("arguments[0].click();", gpu_button)
            time.sleep(2)

            return all_options

        except Exception as e:
            print(f"❌ Error testing GPU dropdown: {e}")
            return []

    def run_dropdown_tests(self):
        """Run comprehensive dropdown tests"""
        try:
            self.setup_driver()
            self.authenticate()
            self.access_leaderboard_interface()

            # Find dropdown buttons
            framework_button, gpu_button = self.find_dropdown_buttons()

            if not framework_button or not gpu_button:
                print("❌ Could not find dropdown buttons")
                return

            # Test framework dropdown
            framework_options = []
            if framework_button:
                framework_options = self.test_framework_dropdown(framework_button)

            # Test GPU dropdown
            gpu_options = []
            if gpu_button:
                gpu_options = self.test_gpu_dropdown(gpu_button)

            # Save results
            results = {
                "timestamp": datetime.now().isoformat(),
                "framework_options": framework_options,
                "gpu_options": gpu_options,
                "framework_button_text": (
                    framework_button.text if framework_button else None
                ),
                "gpu_button_text": gpu_button.text if gpu_button else None,
            }

            with open("dropdown_test/dropdown_test_results.json", "w") as f:
                json.dump(results, f, indent=2)

            print("\n" + "=" * 60)
            print("🧪 DROPDOWN TEST RESULTS")
            print("=" * 60)
            print(
                f"Framework button: '{framework_button.text if framework_button else 'None'}'"
            )
            print(f"Framework options found: {len(framework_options)}")
            for i, opt in enumerate(framework_options):
                print(f"  {i+1}. {opt}")

            print(f"\nGPU button: '{gpu_button.text if gpu_button else 'None'}'")
            print(f"GPU options found: {len(gpu_options)}")
            for i, opt in enumerate(gpu_options):
                print(f"  {i+1}. {opt}")

            print("\n💾 Test results saved to dropdown_test/")
            print("=" * 60)

            input("Press Enter to close browser...")

        finally:
            if self.driver:
                self.driver.quit()


def main():
    print("🧪 LeetGPU Dropdown Test Tool")
    print("=" * 40)
    print("This will test clicking the dropdown buttons")
    print("to discover all available framework and GPU options")
    print("=" * 40)

    if input("\nProceed with dropdown testing? (y/n): ").lower() == "y":
        tester = DropdownTestScraper()
        tester.run_dropdown_tests()


if __name__ == "__main__":
    main()
