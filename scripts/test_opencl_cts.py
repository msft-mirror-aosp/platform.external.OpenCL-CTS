#!/usr/bin/env python3

import unittest
import os
from xml.etree import ElementTree
import subprocess
from functools import partial
import re
import sys

VERBOSE = True
TEST_CONFIG = os.path.join(os.path.dirname(__file__), "test_opencl_cts.xml")


def extract_tests_from_xml(xmlfile):
  """ Extracts tests from AndroidTest.xml compatible file

      param: xmlfile str containing path to AndroidTest.xml compatible xml file
  """
  tree = ElementTree.parse(xmlfile)
  root = tree.getroot()
  return [(o.attrib["key"], o.attrib["value"])
          for o in root.findall("./target_preparer/option")
          if o.attrib["name"] == "push-file"]


def run_command(command):
  serial_number = os.environ.get("ANDROID_SERIAL", "")
  if not serial_number:
    raise "$ANDROID_SERIAL is empty, device must be specified"
  full_command = ["adb", "-s", serial_number, "shell"] + command
  if VERBOSE:
    print("+" + " ".join(full_command))
  ret = subprocess.run(
      full_command, capture_output=True, universal_newlines=True)
  if VERBOSE:
    print(ret.stdout)
    print(ret.stderr, file=sys.stderr)
  return ret.returncode, ret.stdout, ret.stderr


class OpenCLTest(unittest.TestCase):

  def __init__(self, test_name, binary_path, args):
    self._test_name = test_name
    self._binary_path = binary_path
    self._args = args

    self._command = list(map(str.strip, [self._binary_path] + self._args))
    self.test_func_name = f"test_{self._test_name}"

    setattr(self, self.test_func_name, self.genericTest)
    super().__init__(methodName=self.test_func_name)

  def genericTest(self):
    retcode, output, oerror = run_command(self._command)
    self.assertFalse(retcode, "Test exited with non-zero status")

    # TODO(b/158646251): Update upstream to exit with proper error code
    statline_regex = re.compile("^passed \d+ of \d+ tests.")
    passed = total = None
    for line in reversed(output.split("\n")):
      if statline_regex.match(line.strip().lower()):
        _, passed, _, total, *_ = line.strip().split()
        passed = int(passed)
        total = int(total)

    self.assertTrue(passed is not None, "Couldn't find status line")
    self.assertTrue(total is not None, "Couldn't find status line")
    self.assertEqual(passed, total, "{} subtests failed".format(total - passed))


ANDROID_RUNNER_REQUIRED_VERBOSITY = 2


def main():
  """main entrypoint for test runner"""

  runner = unittest.TextTestRunner(
      stream=sys.stderr, verbosity=ANDROID_RUNNER_REQUIRED_VERBOSITY)
  suite = unittest.TestSuite()
  for test, test_path in extract_tests_from_xml(TEST_CONFIG):
    print(f"Found test: {test}")
    suite.addTest(OpenCLTest(test, test_path, []))
  runner.run(suite)


if __name__ == "__main__":
  main()
