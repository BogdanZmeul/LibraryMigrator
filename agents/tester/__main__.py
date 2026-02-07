"""
Entry point for running Tester agent from command line
"""
import sys
from .tester import Tester


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "test-project"

    print(f"Testing Tester agent with repo: {repo_path}")
    tester = Tester(repo_path)
    result = tester.run_tests()

    print(f"\n{'=' * 60}")
    print(f"Final Result: {result}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()