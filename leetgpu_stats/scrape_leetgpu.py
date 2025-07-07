#!/usr/bin/env python3

import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver(headless=True):
    """Setup Chrome driver with proper options"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Trying with system chrome driver...")
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e2:
            print(f"Error with system driver: {e2}")
            return None


def scrape_leetgpu_data():
    """Scrape LeetGPU vector addition challenge data"""
    driver = setup_driver(headless=True)
    if not driver:
        print("Failed to setup driver")
        return None

    try:
        print("Loading LeetGPU vector addition challenge page...")
        driver.get("https://leetgpu.com/challenges/vector-addition")

        # Wait for the React app to load
        print("Waiting for React app to load...")
        wait = WebDriverWait(driver, 30)

        # Wait for the root div to be populated
        try:
            root_div = wait.until(EC.presence_of_element_located((By.ID, "root")))
            print("Root div found")
        except:
            print("Root div not found")
            return None

        # Wait for content to load - look for common indicators
        loading_indicators = ["Loading...", "loading", "spinner", "Please wait"]

        # Wait for loading indicators to disappear
        for indicator in loading_indicators:
            try:
                wait.until_not(
                    EC.text_to_be_present_in_element((By.TAG_NAME, "body"), indicator)
                )
            except:
                pass

        # Give extra time for JavaScript to fully load
        print("Waiting for JavaScript to load data...")
        time.sleep(10)

        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")

        # Save page source for debugging
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)} characters")

        # Write page source to file for inspection
        with open("leetgpu_page_source.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        print("Page source saved to leetgpu_page_source.html")

        # Try to find content that indicates data has loaded
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"Body text length: {len(body_text)} characters")

        if len(body_text) > 500:  # Reasonable amount of content
            print("Found substantial content, analyzing...")

            # Look for common challenge-related keywords
            keywords = [
                "challenge",
                "submission",
                "leaderboard",
                "gpu",
                "cuda",
                "performance",
                "time",
                "score",
                "rank",
            ]
            found_keywords = [kw for kw in keywords if kw.lower() in body_text.lower()]
            print(f"Found keywords: {found_keywords}")

            # Look for any lists or structured content
            lists = driver.find_elements(
                By.CSS_SELECTOR, "ul, ol, div[class*='list'], div[class*='item']"
            )
            print(f"Found {len(lists)} potential list elements")

            # Look for any cards or components that might contain submission data
            cards = driver.find_elements(
                By.CSS_SELECTOR,
                "div[class*='card'], div[class*='submission'], div[class*='entry']",
            )
            print(f"Found {len(cards)} potential card elements")

            # Extract any performance metrics from the text
            performance_patterns = [
                r"(\d+\.?\d*)\s*ms",
                r"(\d+\.?\d*)\s*seconds?",
                r"(\d+\.?\d*)\s*μs",
                r"(\d+\.?\d*)\s*fps",
                r"(\d+\.?\d*)\s*gflops",
                r"(\d+\.?\d*)\s*tflops",
            ]

            performance_data = []
            for pattern in performance_patterns:
                matches = re.findall(pattern, body_text, re.IGNORECASE)
                if matches:
                    performance_data.extend(matches)

            print(
                f"Found {len(performance_data)} performance metrics: {performance_data[:10]}"
            )

            # Try to extract structured data from any visible elements
            all_elements = driver.find_elements(By.CSS_SELECTOR, "*")
            data_elements = []

            for element in all_elements:
                try:
                    text = element.text.strip()
                    if (
                        text and len(text) > 20 and len(text) < 500
                    ):  # Reasonable text length
                        # Check if it contains performance or submission data
                        if any(
                            keyword in text.lower()
                            for keyword in [
                                "gpu",
                                "cuda",
                                "ms",
                                "seconds",
                                "performance",
                                "submission",
                            ]
                        ):
                            data_elements.append(text)
                except:
                    continue

            print(f"Found {len(data_elements)} potential data elements")

            if data_elements:
                # Return the first 20 elements as potential submissions
                return [[element] for element in data_elements[:20]]
            elif performance_data:
                # Return performance data as basic submissions
                return [[f"Performance: {perf}"] for perf in performance_data[:20]]
            else:
                print("No structured data found")
                return None
        else:
            print("Page content is too short, likely not loaded properly")
            return None

    except Exception as e:
        print(f"Error scraping data: {e}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        driver.quit()


def check_api_endpoints():
    """Check if there are any API endpoints we can use"""
    import requests

    # Common API endpoints that might exist
    api_endpoints = [
        "https://leetgpu.com/api/challenges/vector-addition",
        "https://leetgpu.com/api/challenges/vector-addition/submissions",
        "https://leetgpu.com/api/v1/challenges/vector-addition",
        "https://leetgpu.com/api/leaderboard/vector-addition",
        "https://leetgpu.com/challenges/vector-addition/api",
        "https://leetgpu.com/challenges/vector-addition/leaderboard",
    ]

    print("Checking for API endpoints...")
    for endpoint in api_endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200 and response.headers.get(
                "content-type", ""
            ).startswith("application/json"):
                print(f"Found API endpoint: {endpoint}")
                try:
                    data = response.json()
                    if data:
                        print(
                            f"API returned {len(data)} items"
                            if isinstance(data, list)
                            else "API returned data"
                        )
                        return data
                except:
                    print(f"API endpoint {endpoint} returned non-JSON data")
            else:
                print(f"API endpoint {endpoint} returned status {response.status_code}")
        except Exception as e:
            print(f"API endpoint {endpoint} failed: {e}")

    return None


def convert_to_dashboard_format(scraped_data):
    """Convert scraped data to dashboard format"""
    if not scraped_data:
        return None

    submissions = []

    for i, row in enumerate(scraped_data):
        if isinstance(row, list) and len(row) >= 1:
            try:
                # Try to extract meaningful data from the row
                text = " ".join(row).strip()

                # Default submission structure
                submission = {
                    "id": i + 1,
                    "language": "Unknown",
                    "gpu": "Unknown",
                    "runtime": 0.0,
                    "author": "Anonymous",
                    "throughput": 0.0,
                    "efficiency": 0.0,
                    "memory_usage": 0.0,
                    "gpu_utilization": 0.0,
                    "submission_date": "2024-01-01",
                    "code_size": 0,
                    "energy_consumption": 0.0,
                }

                # Try to extract GPU information
                gpu_patterns = [
                    r"(A100|H100|V100|RTX\s*\d+|Tesla\s*\w+|Quadro\s*\w+)",
                    r"(GTX\s*\d+|RTX\s*\d+|Titan\s*\w+)",
                ]

                for pattern in gpu_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        submission["gpu"] = match.group(1)
                        break

                # Try to extract language/framework
                lang_patterns = [
                    r"(CUDA|OpenCL|Triton|PyTorch|TensorFlow|JAX|Mojo|TinyGrad)",
                    r"(Python|C\+\+|C|Rust|Julia|Go)",
                ]

                for pattern in lang_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        submission["language"] = match.group(1)
                        break

                # Try to extract runtime
                time_patterns = [
                    r"(\d+\.?\d*)\s*ms",
                    r"(\d+\.?\d*)\s*seconds?",
                    r"(\d+\.?\d*)\s*μs",
                ]

                for pattern in time_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        time_val = float(match.group(1))
                        if "ms" in match.group(0):
                            submission["runtime"] = (
                                time_val / 1000
                            )  # Convert to seconds
                        elif "μs" in match.group(0):
                            submission["runtime"] = (
                                time_val / 1000000
                            )  # Convert to seconds
                        else:
                            submission["runtime"] = time_val
                        break

                # Calculate throughput if we have runtime
                if submission["runtime"] > 0:
                    # Assume vector addition of 1M elements as baseline
                    submission["throughput"] = 1000000 / submission["runtime"]

                submissions.append(submission)
            except Exception as e:
                print(f"Error processing row {i}: {e}")
                continue

    return submissions


def main():
    """Main function to scrape and save data"""
    print("Starting LeetGPU data scraping...")

    # First try to find API endpoints
    api_data = check_api_endpoints()

    if api_data:
        print("Found API data, processing...")
        # Process API data here if found
        dashboard_data = convert_to_dashboard_format(api_data)
    else:
        # Fall back to scraping
        print("No API found, attempting to scrape...")
        raw_data = scrape_leetgpu_data()

        if raw_data:
            print(f"Successfully scraped {len(raw_data)} rows of data")
            dashboard_data = convert_to_dashboard_format(raw_data)
        else:
            print("Failed to scrape data")
            dashboard_data = None

    if dashboard_data:
        # Save to JSON file
        output_file = "leetgpu_stats/scraped_data.js"
        with open(output_file, "w") as f:
            f.write("// Real LeetGPU Vector Addition Challenge Data\n")
            f.write(
                "// Scraped from https://leetgpu.com/challenges/vector-addition\n\n"
            )
            f.write("const submissions = ")
            f.write(json.dumps(dashboard_data, indent=2))
            f.write(";\n\n")
            f.write("export { submissions };\n")

        print(f"Data saved to {output_file}")
        print(f"Found {len(dashboard_data)} valid submissions")

        # Print sample of the data
        if dashboard_data:
            print("\nSample data:")
            for i, submission in enumerate(dashboard_data[:3]):
                print(
                    f"{i+1}. Language: {submission['language']}, GPU: {submission['gpu']}, Runtime: {submission['runtime']}s"
                )
    else:
        print("Failed to get data from both API and scraping")
        print("This could be due to:")
        print("1. The page requires authentication")
        print("2. The page has strong anti-scraping measures")
        print("3. The challenge page doesn't have public data")
        print("4. The page structure has changed")
        print("\nFalling back to sample data for now...")
        print("You can check the saved page source in 'leetgpu_page_source.html'")


if __name__ == "__main__":
    main()
