.. _FAQ:

Frequently Asked Questions
==========================

This is a list of Frequently Asked Questions (FAQ) about the Sphere-aae. Feel free to suggest new entries!

... How can I customize the temperature, and repetition penalty of models?
   Please check our :ref:`configure-sphere-aae-chat-json` tutorial.

... What's the quantization algorithm Sphere-aae using?
   Please check our :doc:`/compilation/configure_quantization` tutorial.

... Why do I encounter an error ``free(): invalid pointer, Aborted (core dumped)`` at the end of model compilation?
   This happens if you compiled TVM from source and didn't hide LLVM symbols in cmake configurations.
   Please follow our instructions in :ref:`Building TVM from Source  <tvm-build-from-source>` tutorial to compile TVM which hides LLVM symbols, or use our pre-built Sphere-aae :doc:`pip wheels <../install/sphere_aae>`.
