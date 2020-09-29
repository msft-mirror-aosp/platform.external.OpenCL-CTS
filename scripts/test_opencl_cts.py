#!/usr/bin/env python3

import unittest
import os
import shlex
import subprocess
import sys

ANDROID_RUNNER_REQUIRED_VERBOSITY = 2


def run_command(command):
  serial_number = os.environ.get("ANDROID_SERIAL", "")
  if not serial_number:
    raise "$ANDROID_SERIAL is empty, device must be specified"
  full_command = ["adb", "-s", serial_number, "shell"] + command
  ret = subprocess.run(
      full_command, capture_output=True, universal_newlines=True)
  return ret.returncode, ret.stdout, ret.stderr


def get_subtests(binary_path):
  retcode, output, _ = run_command(shlex.split(f'{binary_path} --help'))

  test_name_line = "Test names"
  index = output.find(test_name_line)
  if index == -1:
    return []

  test_names_output = output[index:]
  test_names = []
  # Skip the first line which starts with "Test names"
  for test_name in test_names_output.splitlines()[1:]:
    if not test_name.startswith((" ", "\t")):
      break
    test_names.append(test_name.strip())

  return test_names


class OpenCLTest(unittest.TestCase):

  def __init__(self, test_name, binary_path, args):

    self._test_name = test_name
    self._binary_path = binary_path
    self._args = args

    self._command = list(
        map(str.strip, [self._binary_path, self._test_name] + self._args))
    self.test_func_name = self._test_name

    setattr(self, self.test_func_name, self.genericTest)
    super().__init__(methodName=self.test_func_name)

  def genericTest(self):
    retcode, output, oerror = run_command(self._command)

    # TODO(layog): CTS currently return non-zero return code if the
    # implementation is missing for some API even if the API is not supported by
    # the version reported by the driver. Need to patch upstream.
    missing_line = f"ERROR: Test '{self._test_name}' is missing implementation"
    if missing_line in output or missing_line in oerror:
      self.skipTest(f"{self._test_name} API not available in the driver")

    self.assertFalse(retcode, "Test exited with non-zero status")

    # TODO(b/158646251): Update upstream to exit with proper error code
    passed_line = "PASSED test."
    self.assertTrue(passed_line in output)


def main():
  """main entrypoint for test runner"""
  _, test_name, binary_path, *args = sys.argv

  # HACK: Name hack to report the actual test name
  OpenCLTest.__name__ = test_name
  OpenCLTest.__qualname__ = test_name

  suite = unittest.TestSuite()
  subtests = get_subtests(binary_path)
  for subtest in subtests:
    suite.addTest(OpenCLTest(subtest, binary_path, args))

  runner = unittest.TextTestRunner(
      stream=sys.stderr, verbosity=ANDROID_RUNNER_REQUIRED_VERBOSITY)
  runner.run(suite)


if __name__ == "__main__":
  main()
