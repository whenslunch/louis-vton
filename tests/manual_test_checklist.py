"""
Manual Test Script for Virtual Try-On Extension
================================================

Run this script to perform manual verification of all features.
It will guide you through each test case and record results.

Usage:
    python tests/manual_test_checklist.py
"""

import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")


def print_test(test_id, description):
    print(f"{Colors.BLUE}[{test_id}]{Colors.END} {description}")


def get_result():
    while True:
        result = input(f"  Result [{Colors.GREEN}P{Colors.END}ass / {Colors.RED}F{Colors.END}ail / {Colors.YELLOW}S{Colors.END}kip]: ").strip().upper()
        if result in ['P', 'F', 'S']:
            return result
        print("  Please enter P, F, or S")


def run_manual_tests():
    """Run the manual test checklist."""
    print_header("Virtual Try-On Manual Test Checklist")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Tester: Manual")
    print()
    
    results = []
    
    # =========================================
    # PREREQUISITES
    # =========================================
    print_header("Prerequisites")
    
    prereqs = [
        ("PRE-1", "ComfyUI is running at http://127.0.0.1:8188"),
        ("PRE-2", "API server is running at http://localhost:8000"),
        ("PRE-3", "Extension is loaded in Chrome (chrome://extensions)"),
        ("PRE-4", "Have test images ready (reference photo, product pages)"),
    ]
    
    for test_id, desc in prereqs:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
        if result == 'F':
            print(f"\n{Colors.RED}Please fix prerequisites before continuing.{Colors.END}")
            return results
    
    # =========================================
    # EXTENSION UI TESTS
    # =========================================
    print_header("Extension UI Tests")
    
    ui_tests = [
        ("UI-1", "Open popup on H&M product page → Shows garment images"),
        ("UI-2", "Open popup on Aritzia product page → Shows garment images"),
        ("UI-3", "Open popup on Zara product page → Shows garment images"),
        ("UI-4", "Open popup on Gap product page → Shows garment images"),
        ("UI-5", "Click refresh button → Re-scrapes and updates images"),
        ("UI-6", "Extension icon shows dress emoji with yellow background"),
    ]
    
    for test_id, desc in ui_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # PHOTO UPLOAD TESTS
    # =========================================
    print_header("Photo Upload Tests")
    
    upload_tests = [
        ("UP-1", "Click upload area → File picker opens"),
        ("UP-2", "Select photo → Preview shows in upload area"),
        ("UP-3", "Click X button → Photo is removed"),
        ("UP-4", "Upload photo, close popup, reopen → Photo is still there"),
        ("UP-5", "Upload photo, navigate to different product, reopen → Photo persists"),
    ]
    
    for test_id, desc in upload_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # GENERATION TESTS
    # =========================================
    print_header("Generation Tests")
    
    gen_tests = [
        ("GEN-1", "Generate button disabled until garment + photo selected"),
        ("GEN-2", "Select garment + upload photo → Generate button enables"),
        ("GEN-3", "Click Generate → Loading screen appears"),
        ("GEN-4", "Wait for completion → Result screen appears"),
        ("GEN-5", "Result image shows person wearing the selected garment"),
    ]
    
    for test_id, desc in gen_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # PERSISTENCE TESTS
    # =========================================
    print_header("Persistence Tests")
    
    persist_tests = [
        ("PER-1", "Start generation, close popup → Reopening shows 'in progress'"),
        ("PER-2", "Wait for generation to complete while popup closed"),
        ("PER-3", "Reopen popup → Result is displayed"),
    ]
    
    for test_id, desc in persist_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # RESULT SCREEN TESTS
    # =========================================
    print_header("Result Screen Tests")
    
    result_tests = [
        ("RES-1", "Download button → Saves PNG file to downloads"),
        ("RES-2", "Try Another button → Returns to selection screen"),
        ("RES-3", "Previous selections (photo) are preserved after Try Another"),
    ]
    
    for test_id, desc in result_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # PROMPT QUALITY TESTS
    # =========================================
    print_header("Prompt Quality Tests (Check server terminal)")
    
    prompt_tests = [
        ("PRM-1", "Extracted attributes show specific garment type (not 'outfit')"),
        ("PRM-2", "Extracted attributes include color when present in description"),
        ("PRM-3", "Prompt does not contain marketing phrases like 'Do you Santorini?'"),
        ("PRM-4", "Prompt mentions specific garment type (dress, blouse, etc.)"),
    ]
    
    for test_id, desc in prompt_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # ERROR HANDLING TESTS
    # =========================================
    print_header("Error Handling Tests")
    
    error_tests = [
        ("ERR-1", "Stop API server, try to generate → Error message shown"),
        ("ERR-2", "Open popup on non-product page → 'No images found' message"),
        ("ERR-3", "Vision extraction fails → Falls back gracefully (check logs)"),
    ]
    
    for test_id, desc in error_tests:
        print_test(test_id, desc)
        result = get_result()
        results.append((test_id, desc, result))
    
    # =========================================
    # SUMMARY
    # =========================================
    print_header("Test Summary")
    
    passed = sum(1 for _, _, r in results if r == 'P')
    failed = sum(1 for _, _, r in results if r == 'F')
    skipped = sum(1 for _, _, r in results if r == 'S')
    total = len(results)
    
    print(f"{Colors.GREEN}Passed:  {passed}/{total}{Colors.END}")
    print(f"{Colors.RED}Failed:  {failed}/{total}{Colors.END}")
    print(f"{Colors.YELLOW}Skipped: {skipped}/{total}{Colors.END}")
    print()
    
    if failed > 0:
        print(f"{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.END}")
        for test_id, desc, result in results:
            if result == 'F':
                print(f"  {Colors.RED}[{test_id}]{Colors.END} {desc}")
    
    # Save results
    results_file = Path("tests/manual_test_results.txt")
    with open(results_file, "w") as f:
        f.write(f"Manual Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Passed:  {passed}/{total}\n")
        f.write(f"Failed:  {failed}/{total}\n")
        f.write(f"Skipped: {skipped}/{total}\n\n")
        f.write("Details:\n")
        for test_id, desc, result in results:
            status = {"P": "PASS", "F": "FAIL", "S": "SKIP"}[result]
            f.write(f"[{status}] {test_id}: {desc}\n")
    
    print(f"\nResults saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    try:
        run_manual_tests()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted.{Colors.END}")
        sys.exit(1)
