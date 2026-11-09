"""Run every ROS regression except the explicitly separate native Nav2 diagnostic."""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
suite = unittest.TestSuite()
loader = unittest.TestLoader()
for path in sorted((root / 'tests_ros').glob('test_*.py')):
    if path.name != 'test_nav2_costmap.py':
        suite.addTests(loader.discover(str(path.parent), pattern=path.name))
if suite.countTestCases() == 0:
    raise SystemExit('No required ROS tests discovered')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
