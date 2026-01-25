"""FFI APIs for sphere_aae"""

import tvm_ffi

# Exports functions registered via TVM_FFI_REGISTER_GLOBAL with the "sphere_aae" prefix.
# e.g. TVM_FFI_REGISTER_GLOBAL("sphere_aae.Tokenizer")
tvm_ffi.init_ffi_api("sphere_aae.tokenizers", __name__)  # pylint: disable=protected-access
