/*!
 *  Copyright (c) 2023-2025 by Contributors
 * \file serve/engine_actions/action.cc
 */

#include "action.h"

namespace sphere_aae {
namespace llm {
namespace serve {

TVM_FFI_STATIC_INIT_BLOCK() { EngineActionObj::RegisterReflection(); }

}  // namespace serve
}  // namespace llm
}  // namespace sphere_aae
