import json
import os
import re
import shutil
import subprocess
from xml.dom import minidom
from xml.etree import ElementTree


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_JSON = 'tests.json'
TEST_JSON_PATH = os.path.join(SCRIPT_DIR, TEST_JSON)


def write_one_cc_test(test_details, f):
  stringified_sources = map(lambda s: f'"{s}"', test_details['srcs'])
  stringified_data = map(lambda s: f'"{s}"', test_details.get('data', []))
  stringified_cflags = map(lambda s: f'"{s}"', test_details.get('cflags', []))

  default = "ocl-test-defaults"
  if test_details.get('image_type', False):
    default = "ocl-test-image-defaults"

  rtti = test_details.get('rtti', False)

  cc_test_string = """
cc_test {{
    name: "{}",
    srcs: [ {} ],
    data: [ {} ],
    cflags: [ {} ],
    defaults: [ "{}" ],
    rtti: {},
    gtest: false
}}

""".format(test_details['binary_name'],
           ", ".join(stringified_sources),
           ", ".join(stringified_data),
           ", ".join(stringified_cflags),
           default,
           (str(rtti)).lower())

  empty_field_regex = re.compile("^\s*\w+: \[\s*\],?$")
  cc_test_string = '\n'.join([line for line in cc_test_string.split('\n')
                                   if not empty_field_regex.match(line)])
  f.write(cc_test_string)
  return test_details['binary_name']

# replace ALL_TEST_MODULES with list of
def process_tail(tail, test_targets) -> str:
  lines = [f'":{target}",' for target in test_targets]
  replacement = "\n".join(lines)
  return tail.replace("ALL_TEST_MODULES", replacement)

# Return value indicates whether the output should be formatted with bpfmt
def generate_android_bp() -> bool:
  android_bp_head_path = os.path.join(SCRIPT_DIR, 'android_bp_head')
  android_bp_tail_path = os.path.join(SCRIPT_DIR, 'android_bp_tail')

  with open('Android.bp', 'w') as android_bp:
    with open(android_bp_head_path, 'r') as android_bp_head:
      android_bp.write(android_bp_head.read())

    with open(TEST_JSON_PATH) as f:
      tests = json.load(f)

    test_targets = []
    for test in tests:
      test_targets.append(write_one_cc_test(test, android_bp))

    with open(android_bp_tail_path, 'r') as android_bp_tail:
      android_bp.write(process_tail(android_bp_tail.read(), test_targets))

  if shutil.which('bpfmt') is not None:
    subprocess.run(['bpfmt', '-w', 'Android.bp'])
    return True

  return False


def create_subelement_with_attribs(element, tag, attribs):
  subelement = ElementTree.SubElement(element, tag)

  for key, value in attribs.items():
    subelement.attrib[key] = value

  return subelement


def generate_push_file_rules(configuration):
  create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.tradefed.targetprep.RootTargetPreparer" })

  tester_pusher = create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.compatibility.common.tradefed.targetprep.FilePusher" })
  create_subelement_with_attribs(tester_pusher, 'option',
      { 'name': "cleanup", 'value': "true" })
  create_subelement_with_attribs(tester_pusher, 'option',
      { 'name': "push-file", 'key': 'opencl_cts', 'value': "/data/nativetest64/unrestricted/opencl_cts" })

  test_pusher = create_subelement_with_attribs(configuration, 'target_preparer',
      { 'class': "com.android.compatibility.common.tradefed.targetprep.FilePusher" })
  create_subelement_with_attribs(test_pusher, 'option',
      { 'name': "cleanup", 'value': "true" })
  create_subelement_with_attribs(test_pusher, 'option',
      { 'name': "append-bitness", 'value': "true" })

  with open(TEST_JSON_PATH, "r") as f:
    tests = json.load(f)

  for test in tests:
    if test.get('manual_only', False):
      continue

    create_subelement_with_attribs(test_pusher, 'option',
        {
          'name': "push-file",
          'key': test['binary_name'],
          'value': "/data/nativetest64/unrestricted/{}".format(test['binary_name'])
        })


def generate_test_rules(configuration):
  with open(TEST_JSON_PATH, "r") as f:
    tests = json.load(f)

  for test in tests:
    if test.get('manual_only', False):
      continue

    test_rule = create_subelement_with_attribs(configuration, 'test',
        { 'class': "com.android.tradefed.testtype.binary.ExecutableTargetTest" })

    create_subelement_with_attribs(test_rule, 'option',
        { 'name': "per-binary-timeout", 'value': test.get('timeout', "30m") })
    create_subelement_with_attribs(test_rule, 'option',
        { 'name': "test-command-line",
          'key' : test['test_name'],
          'value': "/data/nativetest64/unrestricted/opencl_cts/*/opencl_cts {} /data/nativetest64/unrestricted/{}".format(test['test_name'], test['binary_name']) })

    for arg in test.get('arguments', []):
      create_subelement_with_attribs(test_rule, 'option',
          { 'name': "python-options", 'value': arg })


def generate_test_xml():
  configuration = ElementTree.Element('configuration')
  configuration.attrib['description'] = "Config to run OpenCL CTS"

  logcat = ElementTree.SubElement(configuration, 'option')
  logcat.attrib['name'] = "logcat-on-failure"
  logcat.attrib['value'] = "false"

  generate_push_file_rules(configuration)
  generate_test_rules(configuration)

  stringified_configuration = ElementTree.tostring(configuration, 'utf-8')
  reparsed_configuration = minidom.parseString(stringified_configuration)
  with open('test_opencl_cts.xml', 'w') as f:
    f.write(reparsed_configuration.toprettyxml(indent=" "*4))


def main():
  android_bp_formatted = generate_android_bp()
  generate_test_xml()

  print("Don't forget to move -")
  print("    Android.bp -> {ANDROID_ROOT}/external/OpenCL-CTS/Android.bp")
  print("    test_opencl_cts.xml -> {ANDROID_ROOT}/external/OpenCL-CTS/scripts/test_opencl_cts.xml")
  if not android_bp_formatted:
    print("then run the blueprint autoformatter:")
    print("    bpfmt -w {ANDROID_ROOT}/external/OpenCL-CTS/Android.bp")


if __name__ == '__main__':
  main()
