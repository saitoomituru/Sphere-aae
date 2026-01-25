sphere\_aae.compiler\_pass package
==================================

.. automodule:: sphere_aae.compiler_pass
   :members:
   :undoc-members:
   :show-inheritance:

Submodules
----------

.. toctree::
   :maxdepth: 4

   sphere_aae.compiler_pass.attach_cuda_graph_alloc_init_func
   sphere_aae.compiler_pass.attach_embedding_allocator
   sphere_aae.compiler_pass.attach_logit_processor
   sphere_aae.compiler_pass.attach_sampler
   sphere_aae.compiler_pass.attach_softmax_with_temperature
   sphere_aae.compiler_pass.attach_spec_decode_aux_funcs
   sphere_aae.compiler_pass.attach_support_info
   sphere_aae.compiler_pass.blas_dispatch
   sphere_aae.compiler_pass.clean_up_tir_attrs
   sphere_aae.compiler_pass.dispatch_kv_cache_creation
   sphere_aae.compiler_pass.dispatch_triton_kernel
   sphere_aae.compiler_pass.estimate_memory_usage
   sphere_aae.compiler_pass.fuse_add_norm
   sphere_aae.compiler_pass.fuse_dequantize_matmul_ewise
   sphere_aae.compiler_pass.fuse_dequantize_take
   sphere_aae.compiler_pass.fuse_dequantize_transpose
   sphere_aae.compiler_pass.fuse_ft_dequantize_matmul_epilogue
   sphere_aae.compiler_pass.fuse_transpose_matmul
   sphere_aae.compiler_pass.lift_global_buffer_alloc
   sphere_aae.compiler_pass.low_batch_specialization
   sphere_aae.compiler_pass.pipeline
   sphere_aae.compiler_pass.pipeline_parallel_rewrite
   sphere_aae.compiler_pass.scatter_tuple_get_item
