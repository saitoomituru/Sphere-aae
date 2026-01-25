/*!
 *  Copyright (c) 2023-2025 by Contributors
 * \file json_ffi/image_utils.h
 * \brief The header of Image utils for JSON FFI Engine in Astro Agent Edge (AAE).
 */
#ifndef SPHERE_AAE_JSON_FFI_IMAGE_UTILS_H_
#define SPHERE_AAE_JSON_FFI_IMAGE_UTILS_H_

#include <tvm/runtime/tensor.h>

#include <optional>
#include <string>

#include "../support/result.h"

namespace sphere_aae {
namespace llm {
namespace json_ffi {

/*! \brief Load a base64 encoded image string into a CPU Tensor of shape {height, width, 3} */
Result<tvm::runtime::Tensor> LoadImageFromBase64(const std::string& base64_str);

/*! \brief Preprocess the CPU image for CLIP encoder and return an Tensor on the given device */
tvm::runtime::Tensor ClipPreprocessor(tvm::runtime::Tensor image_data, int target_size,
                                      DLDevice device);

}  // namespace json_ffi
}  // namespace llm
}  // namespace sphere_aae

#endif  // SPHERE_AAE_JSON_FFI_IMAGE_UTILS_H_
