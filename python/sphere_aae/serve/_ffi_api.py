"""FFI APIs for sphere_aae.serve"""

import tvm_ffi

# Exports functions registered via TVM_FFI_REGISTER_GLOBAL with the "sphere_aae.serve" prefix.
# e.g. TVM_FFI_REGISTER_GLOBAL("sphere_aae.serve.TextData")
tvm_ffi.init_ffi_api("sphere_aae.serve", __name__)  # pylint: disable=protected-access
