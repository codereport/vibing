#!/usr/bin/env python3
"""
Quick script to save the results from the previous thrust:: search run
Since the original search completed successfully but failed to save due to path issues.
"""

import json
import os
from datetime import datetime

# Results from the user's previous run
results_data = {
    "search_timestamp": "2025-08-20T12:48:21",  # Approximate time from the output
    "keyword": "thrust::",
    "extensions": [".cu", ".h", ".cpp", ".hpp", ".cuh"],
    "results_by_extension": {
        ".cu": 700,
        ".h": 404,
        ".cpp": 476,
        ".hpp": 554,
        ".cuh": 577,
    },
    "summary": {
        "total_unique_repositories": 2201,
        "total_repository_instances": 2711,
        "efficiency_per_request": 22.0,
        "pages_searched_per_extension": 10,
        "total_api_requests": 100,
        "runtime_minutes": 10,
    },
    "top_15_repositories": [
        "09jvilla/salary-predict",
        "0chonko/HPC-net-bench",
        "1053581017/FUEL2",
        "1180779/SpheresRaycasting",
        "13Karl/CUDA-Image-and-Video-codec",
        "19-hanhan/LSG",
        "1OngJ/LoL",
        "1hao-Liu/Libs-VSLAM",
        "1onlyadvance/AE",
        "2lian/Legged-Robot-Movability-Cuda",
        "565353780/chamfer-distance",
        "8-lines/CAD_Jupyter",
        "8fm/openw3",
        "8l/kalmar",
        "95616ARG/SyReNN_GPU",
    ],
}

# Save to data directory
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

timestamp = "20250820_124821"  # From the original error message
filename = os.path.join(data_dir, f"thrust_search_summary_{timestamp}.json")

with open(filename, "w") as f:
    json.dump(results_data, f, indent=2)

print(f"✅ Previous search results saved to: {filename}")
print(
    f"🎯 Found {results_data['summary']['total_unique_repositories']} unique repositories"
)
print(
    f"📈 Efficiency: {results_data['summary']['efficiency_per_request']} repos per API request"
)
