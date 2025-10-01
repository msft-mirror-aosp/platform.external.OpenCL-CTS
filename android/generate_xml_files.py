import os
import subprocess
from xml.dom import minidom
from xml.etree import ElementTree


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "test_conformance", "opencl_conformance_tests_full.csv")
DATA_PATH="/data/nativetest64/unrestricted/OpenCL-CTS"

def get_all_tests():
  def get_args(split):
    if len(split) > 1:
      return split[1].removesuffix(" all")
    else:
      return ''

  def get_subtests(executable):
    process = subprocess.run(executable + " --list | sort",
                             shell=True, check=True, capture_output=True, text=True)
    subtests = []
    for subtest in process.stdout.splitlines():
      subtest = subtest.strip()
      if subtest == "":
        continue
      subtests.append(subtest)
    return subtests

  all_tests = dict()
  with open(TEST_CSV_PATH, newline='') as csvfile:
    for line in csvfile.readlines():
      if (line.startswith("#") or
          line == "\n" or
          line.startswith("OpenCL-GL") or
          line.startswith("CL_DEVICE_TYPE_CPU")):
        continue
      executable_and_args = line.split(',')[-1].strip().split(' ', 1)
      executable = executable_and_args[0].rsplit("/", 1)[1]
      args = get_args(executable_and_args)
      subtests = get_subtests(executable)
      if all_tests.get(executable) is None:
        all_tests[executable] = []
      all_tests[executable].append(dict(args=args, subtests=subtests, path=executable_and_args[0]))
  return all_tests

timeouts = {
  'OpenCL-CTS-test_allocations' : 10,
  'OpenCL-CTS-test_basic': {
    'astype': 10,
    'async_copy_global_to_local': 10,
    'async_copy_global_to_local2D': 10,
    'async_copy_global_to_local3D': 10,
    'async_copy_local_to_global': 10,
    'async_copy_local_to_global2D': 10,
    'async_copy_local_to_global3D': 10,
    'async_strided_copy_global_to_local': 10,
    'async_strided_copy_local_to_global': 10,
    'enqueue_map_buffer': 3,
    'enqueue_map_image': 2,
    'hiloeo': 10,
    'imagedim_non_pow2': 20,
    'imagedim_pow2': 20,
    'prefetch': 2,
    'progvar_prog_scope_init': 2,
    'vector_creation': 20,
    'vector_swizzle': 5,
    'vload_constant': 2,
    'vload_global': 2,
    'vload_local': 2,
    'vload_private': 2,
    'vstore_global': 2,
    'vstore_local': 2,
    'vstore_private': 2,
  },
  'OpenCL-CTS-test_bruteforce': {
    'pown': 300,
    'powr': 300,
    'reciprocal': 300,
    'remainder': 300,
    'remquo': 300,
    'rint': 300,
    'rootn': 300,
    'round': 300,
    'rsqrt': 300,
  },
  'OpenCL-CTS-test_buffers': 2,
  'OpenCL-CTS-test_c11_atomics': 10,
  'OpenCL-CTS-test_cl_copy_images': 60,
  'OpenCL-CTS-test_cl_fill_images': 30,
  'OpenCL-CTS-test_cl_get_info': {
      '2Darray': 2,
      '3D': 2,
  },
  'OpenCL-CTS-test_cl_read_write_images': 10,
  'OpenCL-CTS-test_image_streams': 10,
  'OpenCL-CTS-test_integer_ops': 20,
  'OpenCL-CTS-test_kernel_image_methods': 10,
  'OpenCL-CTS-test_multiples': {
    'context_multiple_contexts_same_device': 20,
  },
  'OpenCL-CTS-test_relationals': {
    'shuffle_array_cast': 10,
    'shuffle_built_in': 10,
    'shuffle_built_in_dual_input': 10,
    'shuffle_copy': 10,
    'shuffle_function_call': 10,
  },
  'OpenCL-CTS-test_samplerless_reads': 10,
  'OpenCL-CTS-test_vectors': {
    'vec_align_array': 20,
    'vec_align_packed_struct': 30,
    'vec_align_packed_struct_arr': 20,
    'vec_align_struct': 30,
    'vec_align_struct_arr': 20,
  }
}

def generate_xml(binary, tests, timeout):
  def create_subelement_with_attribs(element, tag, attribs):
    subelement = ElementTree.SubElement(element, tag)
    for key, value in attribs.items():
      subelement.attrib[key] = value
    return subelement

  def generate_push_file_rules(configuration, tests):
    create_subelement_with_attribs(
      configuration, 'target_preparer',
      { 'class': "com.android.tradefed.targetprep.RootTargetPreparer" })
    test_pusher = create_subelement_with_attribs(
      configuration, 'target_preparer',
      { 'class': "com.android.compatibility.common.tradefed.targetprep.FilePusher" })
    create_subelement_with_attribs(
      test_pusher, 'option', { 'name': "cleanup", 'value': "true" })
    for test in tests:
      create_subelement_with_attribs(
        test_pusher, 'option',
        {
          'name': "push-file",
          'key': test[0],
          'value': test[1],
        })

  def generate_test_rules(configuration, binary, tests, default_timeout):
    for test in tests:
      if type(timeouts.get(binary)) is dict:
        timeout = timeouts[binary].get(test[0], default_timeout)
      else:
        timeout = timeouts.get(binary, default_timeout)

      test_rule = create_subelement_with_attribs(
        configuration, 'test', { 'class': "com.android.tradefed.testtype.binary.ExecutableTargetTest" })
      create_subelement_with_attribs(
        test_rule, 'option', { 'name': "per-binary-timeout", 'value': "{}m".format(timeout) })
      create_subelement_with_attribs(
        test_rule, 'option', { 'name': "test-command-line", 'key' : test[0], 'value': test[1] })

  configuration = ElementTree.Element('configuration')
  configuration.attrib['description'] = "Config to run {}".format(binary)
  logcat = ElementTree.SubElement(configuration, 'option')
  logcat.attrib['name'] = "logcat-on-failure"
  logcat.attrib['value'] = "false"
  generate_push_file_rules(configuration, [(binary, DATA_PATH)])
  generate_test_rules(configuration, binary, tests, timeout)
  stringified_configuration = ElementTree.tostring(configuration, 'utf-8')
  reparsed_configuration = minidom.parseString(stringified_configuration)
  with open(os.path.join(SCRIPT_DIR, binary + ".xml"), 'w') as f:
    f.write(reparsed_configuration.toprettyxml(indent=" "*4))


def main():
  def clean_name(name):
    return name.replace(" ", "_").replace("*", "")
  all_tests = get_all_tests()
  cts_tests = []
  for key, vals in all_tests.items():
    binary = "OpenCL-CTS-" + key
    subtests = []
    for val in vals:
      args = val['args']
      if args and not args.startswith("--"):
        args = " " + args
      else:
        args = ""
      binary_path = DATA_PATH + "/*/" + binary
      prefix = ""
      folder = {
        'test_compiler': "test_conformance/compiler/",
        'test_spir': "test_conformance/spir/",
      }.get(key, None)
      if folder is not None:
        new_path = DATA_PATH + "/*/" + folder
        binary_path = new_path + binary
        prefix = "cp " + DATA_PATH + "/*/" + binary + " " + new_path + "; "
      suffix = {
        'test_spirv_new': " --spirv_binaries_path " + DATA_PATH + "/*/gensrcs/external/OpenCL-CTS/test_conformance/spirv_new/spirv_asm",
      }.get(key, "")
      cts_tests.append((clean_name(key + args).removeprefix("test_"), prefix + binary_path + args + suffix))
      for subtest in val['subtests']:
        subtest = " " + subtest
        if args != " full*":
          subtest = args + subtest
        subtests.append((clean_name(subtest).removeprefix("_"), "CL_WIMPY_MODE=1 " + prefix + binary_path + subtest + suffix))
    generate_xml(binary, subtests, 1)

  generate_xml("OpenCL-CTS", cts_tests, 180)

if __name__ == '__main__':
  main()
