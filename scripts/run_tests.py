#!/usr/bin/env python3
"""
Test runner script for MCP UI Explorer.
Provides an easy way to run different types of tests during development.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for MCP UI Explorer")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "performance", "all"],
        default="unit",
        help="Type of tests to run (default: unit)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks"
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting before tests"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies first"
    )
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"📁 Working directory: {project_root}")
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        success &= run_command(
            ["pip", "install", "-e", ".[test]"],
            "Installing test dependencies"
        )
        if not success:
            return 1
    
    # Run linting if requested
    if args.lint:
        lint_commands = [
            (["black", "--check", "src/", "tests/"], "Black formatting check"),
            (["isort", "--check-only", "src/", "tests/"], "Import sorting check"),
            (["flake8", "src/", "tests/"], "Flake8 linting"),
        ]
        
        for cmd, desc in lint_commands:
            success &= run_command(cmd, desc)
            if not success and args.fast:
                return 1
    
    # Build pytest command
    pytest_cmd = ["pytest"]
    
    # Add test type
    if args.type == "unit":
        pytest_cmd.append("tests/unit/")
    elif args.type == "integration":
        pytest_cmd.append("tests/integration/")
    elif args.type == "performance":
        pytest_cmd.append("tests/performance/")
        if args.benchmark:
            pytest_cmd.append("--benchmark-only")
    elif args.type == "all":
        pytest_cmd.append("tests/")
    
    # Add options
    if args.verbose:
        pytest_cmd.append("-v")
    
    if args.fast:
        pytest_cmd.extend(["-x", "--ff"])
    
    if args.coverage and args.type != "performance":
        pytest_cmd.extend([
            "--cov=src/mcp_ui_explorer",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Run tests
    test_description = f"Running {args.type} tests"
    if args.coverage:
        test_description += " with coverage"
    
    success &= run_command(pytest_cmd, test_description)
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("🎉 All tests completed successfully!")
        if args.coverage and args.type != "performance":
            print("📊 Coverage report generated in htmlcov/")
        if args.type == "performance" and args.benchmark:
            print("📈 Benchmark results available")
    else:
        print("💥 Some tests failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 