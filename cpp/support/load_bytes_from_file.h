/*!
 * Copyright (c) 2023-2025 by Contributors
 * \file support/load_bytes_from_file.h
 * \brief Utility methods to load from files.
 */
#ifndef SPHERE_AAE_SUPPORT_LOAD_BYTES_FROM_FILE_H_
#define SPHERE_AAE_SUPPORT_LOAD_BYTES_FROM_FILE_H_

#include <tvm/runtime/logging.h>

#include <fstream>
#include <string>

namespace sphere_aae {
namespace llm {

inline std::string LoadBytesFromFile(const std::string& path) {
  std::ifstream fs(path, std::ios::in | std::ios::binary);
  ICHECK(!fs.fail()) << "Cannot open " << path;
  std::string data;
  fs.seekg(0, std::ios::end);
  size_t size = static_cast<size_t>(fs.tellg());
  fs.seekg(0, std::ios::beg);
  data.resize(size);
  fs.read(data.data(), size);
  return data;
}

}  // namespace llm
}  // namespace sphere_aae

#endif  // SPHERE_AAE_SUPPORT_LOAD_BYTES_FROM_FILE_H_
