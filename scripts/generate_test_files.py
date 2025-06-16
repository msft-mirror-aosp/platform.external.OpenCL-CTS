import json
import os
from xml.dom import minidom
from xml.etree import ElementTree


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_JSON_PATH = os.path.join(SCRIPT_DIR, 'tests.json')
TEST_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "test_conformance", "opencl_conformance_tests_full.csv")
TEST_XML_PATH = os.path.join(SCRIPT_DIR, "test_opencl_cts.xml")
DATA_PATH="/data/nativetest64/unrestricted"


def create_subelement_with_attribs(element, tag, attribs):
  subelement = ElementTree.SubElement(element, tag)

  for key, value in attribs.items():
    subelement.attrib[key] = value

  return subelement


def generate_push_file_rules(configuration, tests):
  create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.tradefed.targetprep.RootTargetPreparer" })

  tester_pusher = create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.compatibility.common.tradefed.targetprep.FilePusher" })
  create_subelement_with_attribs(tester_pusher, 'option',
      { 'name': "cleanup", 'value': "true" })
  create_subelement_with_attribs(tester_pusher, 'option',
      { 'name': "push-file", 'key': 'opencl_cts', 'value': "{}/opencl_cts".format(DATA_PATH) })

  test_pusher = create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.compatibility.common.tradefed.targetprep.FilePusher" })
  create_subelement_with_attribs(test_pusher, 'option',
      { 'name': "cleanup", 'value': "true" })
  create_subelement_with_attribs(test_pusher, 'option',
      { 'name': "append-bitness", 'value': "true" })

  for binary_name, _ in sorted(tests.items()):
    create_subelement_with_attribs(test_pusher, 'option',
        {
          'name': "push-file",
          'key': binary_name,
          'value': "{}/{}".format(DATA_PATH, binary_name),
        })


def generate_test_rules(configuration, tests):
  for binary_name, test in sorted(tests.items()):

    test_rule = create_subelement_with_attribs(configuration, 'test',
        { 'class': "com.android.tradefed.testtype.binary.ExecutableTargetTest" })

    create_subelement_with_attribs(test_rule, 'option',
        { 'name': "per-binary-timeout", 'value': test.get('timeout', "30m") })
    create_subelement_with_attribs(test_rule, 'option',
        { 'name': "test-command-line",
          'key' : test['test_name'],
          'value': "{}/opencl_cts/*/opencl_cts {} {}/{}".format(DATA_PATH, test['test_name'], DATA_PATH, binary_name) })

    for arg in test.get('arguments', []):
      create_subelement_with_attribs(test_rule, 'option',
          { 'name': "python-options", 'value': arg })


def main():
  configuration = ElementTree.Element('configuration')
  configuration.attrib['description'] = "Config to run OpenCL CTS"

  logcat = ElementTree.SubElement(configuration, 'option')
  logcat.attrib['name'] = "logcat-on-failure"
  logcat.attrib['value'] = "false"

  json_tests = dict()
  with open(TEST_JSON_PATH, "r") as f:
    for json_test in json.load(f):
      json_tests[json_test.get('test_name')] = json_test

  tests = dict()
  with open(TEST_CSV_PATH, newline='') as csvfile:
    for line in csvfile.readlines():
      if line.startswith("#") or line == "\n" or line.startswith("OpenCL-GL"):
        continue
      binary = line.split(',')[-1].strip().split(' ')[0].split('/')[-1]
      test_name = binary.removeprefix("test_")
      json_test = json_tests.get(test_name, {'test_name': test_name})
      if json_test.get('manual_only', False):
        continue
      tests["OpenCL-CTS-" + binary] = json_test

  generate_push_file_rules(configuration, tests)
  generate_test_rules(configuration, tests)

  stringified_configuration = ElementTree.tostring(configuration, 'utf-8')
  reparsed_configuration = minidom.parseString(stringified_configuration)
  with open(TEST_XML_PATH, 'w') as f:
    f.write(reparsed_configuration.toprettyxml(indent=" "*4))


if __name__ == '__main__':
  main()
