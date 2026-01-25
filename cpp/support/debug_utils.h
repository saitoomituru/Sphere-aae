/*!
 *  Copyright (c) 2023-2025 by Contributors
 * \file support/debug_utils.h
 * \brief Tools for debug purposes.
 */
#ifndef SPHERE_AAE_SUPPORT_DEBUG_UTILS_H_
#define SPHERE_AAE_SUPPORT_DEBUG_UTILS_H_

#include "../tokenizers/tokenizers.h"

namespace sphere_aae {
namespace llm {

/*! \brief A registry for debug information. */
class DebugRegistry {
 public:
  static DebugRegistry* Global() {
    static DebugRegistry reg;
    return &reg;
  }

  // Tokenizer information, helpful for converting token id to token string in debugging
  Tokenizer tokenizer;
};

/*! \brief Register the tokenizer to the global tokenizer registry. */
inline void DebugRegisterTokenizer(const Tokenizer& tokenizer) {
  DebugRegistry::Global()->tokenizer = tokenizer;
}

/*! \brief Get the registered tokenizer from the global tokenizer registry. */
inline Tokenizer DebugGetTokenizer() { return DebugRegistry::Global()->tokenizer; }

}  // namespace llm
}  // namespace sphere_aae

#endif  // SPHERE_AAE_SUPPORT_DEBUG_UTILS_H_
