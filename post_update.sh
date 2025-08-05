#!/bin/bash

set -e

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

TMP_DIR=$(mktemp -d)
cmake -S "${SCRIPT_DIR}/../OpenCL-ICD-Loader" -B "${TMP_DIR}/OpenCL-ICD-Loader" -DOPENCL_ICD_LOADER_HEADERS_DIR="${SCRIPT_DIR}/../OpenCL-Headers" -G Ninja
cmake --build "${TMP_DIR}/OpenCL-ICD-Loader"
cmake -S "${SCRIPT_DIR}" -B "${TMP_DIR}/OpenCL-CTS" -G Ninja -DCL_INCLUDE_DIR="${SCRIPT_DIR}/../OpenCL-Headers" -DCL_LIB_DIR="${TMP_DIR}/OpenCL-ICD-Loader" -DOPENCL_LIBRARIES=OpenCL
cmake --build "${TMP_DIR}/OpenCL-CTS"
cmake --install "${TMP_DIR}/OpenCL-CTS" --prefix "${TMP_DIR}/install"
cp "${TMP_DIR}/OpenCL-CTS/test_conformance/spir/test_spir" "${TMP_DIR}/install/bin" # Manual install because CMake is not installing it by default

PATH="${PATH}":"${TMP_DIR}/install/bin" python3 "${SCRIPT_DIR}/android/generate_xml_files.py"

rm -rf "${TMP_DIR}"

pushd "${SCRIPT_DIR}/../rust/ninja-to-soong"
cargo run --release -- OpenCL-CTS --copy-to-aosp
popd
