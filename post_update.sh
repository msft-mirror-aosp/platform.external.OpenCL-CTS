#!/bin/bash

set -e

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

help="
OpenCL-CTS post_update depends on 'ninja-to-soong' (https://github.com/rjodinchr/ninja-to-soong).
Please set 'N2S_DIR' to 'ninja-to-soong' to run this script.

Example:
$ N2S_DIR=<path/to/ninja-to-soong> ./tools/external_updater update external/OpenCL-CTS
"
[[ -z "${N2S_DIR}" ]] && echo "$help" && exit -1

python3 "${SCRIPT_DIR}/scripts/generate_test_files.py"

pushd "${N2S_DIR}"
rm -rf "${SCRIPT_DIR}/cmake_generated"
cargo run --release -- --aosp-path $(realpath "${SCRIPT_DIR}/../..") OpenCL-CTS --copy-to-aosp
popd
