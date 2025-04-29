#!/usr/bin/env python
import subprocess
import sys
import os
import webbrowser

def run_tests():
    """Run test suite with coverage reporting."""
    print("Running DJ Online Studio test suite...")
    print("=" * 50)

    # Ensure we're in the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Generate test audio files
    print("\nGenerating test audio files...")
    try:
        from tests.generate_test_audio import generate_test_audio, generate_sweep
        generate_test_audio()
        generate_sweep()
        print("Test audio files generated successfully.")
    except Exception as e:
        print(f"Error generating test files: {e}")
        return False

    # Run pytest with coverage
    cmd = [
        'pytest',
        '--verbose',
        '--tb=short',
        '--cov=dj_online_studio',
        '--cov-report=term-missing',
        '--cov-report=html',
        '-v'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)

        if result.stderr:
            print("\nErrors/Warnings:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        # Open coverage report in browser if tests passed
        if result.returncode == 0:
            report_path = os.path.join(project_root, 'htmlcov', 'index.html')
            if os.path.exists(report_path):
                print("\nOpening coverage report in browser...")
                webbrowser.open(f'file://{report_path}')
            return True
        else:
            print("\nTests failed!")
            return False

    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
