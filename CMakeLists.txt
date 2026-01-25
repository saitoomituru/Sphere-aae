cmake_minimum_required(VERSION 3.18)
project(sphere_aae C CXX)

include(CheckCXXCompilerFlag)
if(MSVC)
  set(CMAKE_CXX_FLAGS "/fp:fast ${CMAKE_CXX_FLAGS}")
else()
  set(CMAKE_CXX_FLAGS "-ffast-math ${CMAKE_CXX_FLAGS}")
endif()

if(EXISTS ${CMAKE_BINARY_DIR}/config.cmake)
  include(${CMAKE_BINARY_DIR}/config.cmake)
else()
  if(EXISTS ${CMAKE_SOURCE_DIR}/config.cmake)
    include(${CMAKE_SOURCE_DIR}/config.cmake)
  endif()
endif()

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE
      RelWithDebInfo
      CACHE STRING "Build type" FORCE)
  message(STATUS "Setting default build type to " ${CMAKE_BUILD_TYPE})
endif(NOT CMAKE_BUILD_TYPE)

option(SPHERE_AAE_HIDE_PRIVATE_SYMBOLS "Hide private symbols" ON)
option(SPHERE_AAE_BUILD_PYTHON_MODULE "Build Python module with scikit-build-core"
       OFF)

if(SPHERE_AAE_INSTALL_STATIC_LIB)
  set(BUILD_STATIC_RUNTIME ON)
endif()

set(SPHERE_AAE_VISIBILITY_FLAG "")
if(SPHERE_AAE_HIDE_PRIVATE_SYMBOLS)
  set(HIDE_PRIVATE_SYMBOLS ON)
  if(NOT MSVC)
    set(SPHERE_AAE_VISIBILITY_FLAG "-fvisibility=hidden")
  endif()
  message(STATUS "Hide private symbols")
endif()

option(BUILD_CPP_TEST "Build cpp unittests" OFF)

set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# tvm runtime config: minimize runtime components
set(USE_RPC OFF)
set(USE_MICRO OFF)
set(USE_GRAPH_EXECUTOR OFF)
set(USE_GRAPH_EXECUTOR_DEBUG OFF)
set(USE_AOT_EXECUTOR OFF)
set(USE_PROFILER OFF)
set(USE_GTEST OFF)
set(USE_LIBBACKTRACE OFF)
set(BUILD_DUMMY_LIBTVM ON)
if(NOT DEFINED TVM_SOURCE_DIR)
  if(DEFINED ENV{TVM_SOURCE_DIR})
    set(TVM_SOURCE_DIR "$ENV{TVM_SOURCE_DIR}")
  else()
    set(TVM_SOURCE_DIR 3rdparty/tvm)
  endif(DEFINED ENV{TVM_SOURCE_DIR})
endif(NOT DEFINED TVM_SOURCE_DIR)
message(STATUS "TVM_SOURCE_DIR: ${TVM_SOURCE_DIR}")
add_subdirectory(${TVM_SOURCE_DIR} tvm EXCLUDE_FROM_ALL)

set(SPHERE_AAE_RUNTIME_LINKER_LIB "")
set(TOKENZIER_CPP_PATH 3rdparty/tokenizers-cpp)
add_subdirectory(${TOKENZIER_CPP_PATH} tokenizers EXCLUDE_FROM_ALL)

set(XGRAMMAR_PATH 3rdparty/xgrammar)
tvm_file_glob(GLOB_RECURSE SPHERE_AAE_SRCS cpp/*.cc)
tvm_file_glob(GLOB_RECURSE XGRAMMAR_SRCS ${XGRAMMAR_PATH}/cpp/*.cc)
list(FILTER XGRAMMAR_SRCS EXCLUDE REGEX "${XGRAMMAR_PATH}/cpp/pybind/.*\\.cc")
list(APPEND SPHERE_AAE_SRCS ${XGRAMMAR_SRCS})
add_library(sphere_aae_objs OBJECT ${SPHERE_AAE_SRCS})

set(SPHERE_AAE_INCLUDES
    ${TVM_SOURCE_DIR}/include ${TVM_SOURCE_DIR}/3rdparty/dlpack/include
    ${TVM_SOURCE_DIR}/3rdparty/dmlc-core/include
    ${TVM_SOURCE_DIR}/3rdparty/picojson)

set(SPHERE_AAE_COMPILE_DEFS ${SPHERE_AAE_COMPILE_DEFS}
                         DMLC_USE_LOGGING_LIBRARY=<tvm/runtime/logging.h>)
set(SPHERE_AAE_COMPILE_DEFS ${SPHERE_AAE_COMPILE_DEFS} __STDC_FORMAT_MACROS=1)
set(SPHERE_AAE_COMPILE_DEFS ${SPHERE_AAE_COMPILE_DEFS} PICOJSON_USE_INT64)
set(SPHERE_AAE_COMPILE_DEFS ${SPHERE_AAE_COMPILE_DEFS} XGRAMMAR_ENABLE_LOG_DEBUG=0)

target_compile_definitions(sphere_aae_objs PRIVATE ${SPHERE_AAE_COMPILE_DEFS})
target_compile_definitions(sphere_aae_objs PRIVATE -DSPHERE_AAE_EXPORTS)
target_include_directories(sphere_aae_objs PRIVATE ${SPHERE_AAE_INCLUDES})
target_include_directories(sphere_aae_objs PRIVATE 3rdparty/stb)
target_include_directories(sphere_aae_objs PRIVATE ${TOKENZIER_CPP_PATH}/include)
target_include_directories(sphere_aae_objs PRIVATE ${XGRAMMAR_PATH}/include)
target_link_libraries(sphere_aae_objs PRIVATE tvm_ffi_header)

add_library(sphere_aae SHARED $<TARGET_OBJECTS:sphere_aae_objs>)
add_library(sphere_aae_static STATIC $<TARGET_OBJECTS:sphere_aae_objs>)
add_dependencies(sphere_aae_static tokenizers_cpp sentencepiece-static
                 tokenizers_c tvm_runtime)
set_target_properties(sphere_aae_static PROPERTIES OUTPUT_NAME sphere_aae)

target_link_libraries(sphere_aae PUBLIC tvm_runtime)
target_link_libraries(sphere_aae PRIVATE tokenizers_cpp)

find_library(FLASH_ATTN_LIBRARY flash_attn
             HINTS ${TVM_SOURCE_DIR}/*/3rdparty/libflash_attn/src)

if(FLASH_ATTN_LIBRARY STREQUAL "FLASH_ATTN_LIBRARY-NOTFOUND")
  message(
    WARNING
      "Cannot find libflash_attn. The model must not have been built with --use-flash-attn-mqa option."
  )
else()
  target_link_libraries(sphere_aae PUBLIC -Wl,--no-as-needed ${FLASH_ATTN_LIBRARY})
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
  target_compile_definitions(sphere_aae PRIVATE "TVM_LOG_DEBUG")
  target_compile_definitions(sphere_aae_objs PRIVATE "TVM_LOG_DEBUG")
  target_compile_definitions(sphere_aae_static PRIVATE "TVM_LOG_DEBUG")
endif()

if(BUILD_CPP_TEST)
  message(STATUS "Building cpp unittests")
  add_subdirectory(3rdparty/googletest)
  file(GLOB_RECURSE SPHERE_AAE_TEST_SRCS
       ${PROJECT_SOURCE_DIR}/tests/cpp/*unittest.cc)
  add_executable(sphere_aae_cpp_tests ${SPHERE_AAE_TEST_SRCS})
  target_include_directories(sphere_aae_cpp_tests PRIVATE ${SPHERE_AAE_INCLUDES})
  target_include_directories(sphere_aae_cpp_tests
                             PRIVATE ${PROJECT_SOURCE_DIR}/cpp)
  target_include_directories(
    sphere_aae_cpp_tests PRIVATE ${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR})
  target_link_libraries(sphere_aae_cpp_tests PUBLIC sphere_aae gtest gtest_main)
endif(BUILD_CPP_TEST)

if(CMAKE_SYSTEM_NAME STREQUAL "Android")
  target_link_libraries(sphere_aae PRIVATE log)
  target_link_libraries(tokenizers_cpp PRIVATE log)
endif()

add_library(sphere_aae_module SHARED $<TARGET_OBJECTS:sphere_aae_objs>)
target_link_libraries(sphere_aae_module PUBLIC tvm)
target_link_libraries(sphere_aae_module PRIVATE tokenizers_cpp)

set_property(
  TARGET sphere_aae_module
  APPEND
  PROPERTY LINK_OPTIONS "${SPHERE_AAE_VISIBILITY_FLAG}")
set_property(
  TARGET sphere_aae
  APPEND
  PROPERTY LINK_OPTIONS "${SPHERE_AAE_VISIBILITY_FLAG}")

find_program(CARGO_EXECUTABLE cargo)

if(NOT CARGO_EXECUTABLE)
  message(FATAL_ERROR "Cargo is not found! Please install cargo.")
endif()

# when this option is on, we install all static lib deps into lib
if(SPHERE_AAE_INSTALL_STATIC_LIB)
  install(TARGETS sphere_aae_static tokenizers_cpp sentencepiece-static tvm_runtime
          LIBRARY DESTINATION lib${LIB_SUFFIX})
  # tokenizers need special handling as it builds from rust
  if(MSVC)
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/tokenizers/libtokenizers_c.lib
            DESTINATION lib${LIB_SUFFIX})
  else()
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/tokenizers/libtokenizers_c.a
            DESTINATION lib${LIB_SUFFIX})
  endif()
else()
  install(
    TARGETS tvm_runtime
            sphere_aae
            sphere_aae_module
            sphere_aae_static
            tokenizers_cpp
            sentencepiece-static
            RUNTIME_DEPENDENCY_SET
            tokenizers_c
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib${LIB_SUFFIX})
endif()

# Python package installation configuration This section ensures that all
# necessary files are installed for the Python wheel
if(SPHERE_AAE_BUILD_PYTHON_MODULE)
  message(STATUS "Configuring Python package installation")

  # Set RPATH for sphere_aae and sphere_aae_module to find other libraries relatively
  if(APPLE)
    # macOS uses @loader_path
    set_target_properties(sphere_aae PROPERTIES INSTALL_RPATH "@loader_path")
    set_target_properties(sphere_aae_module PROPERTIES INSTALL_RPATH
                                                    "@loader_path")
  elseif(LINUX)
    # Linux uses $ORIGIN
    set_target_properties(sphere_aae PROPERTIES INSTALL_RPATH "\$ORIGIN")
    set_target_properties(sphere_aae_module PROPERTIES INSTALL_RPATH "\$ORIGIN")
  endif()

  # Install compiled shared libraries
  install(TARGETS sphere_aae DESTINATION ".")
  install(TARGETS sphere_aae_module DESTINATION ".")
  install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/cpp/" DESTINATION "cpp/")
  install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/web/" DESTINATION "web/")
  install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/README.md"
                "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE"
                "${CMAKE_CURRENT_SOURCE_DIR}/NOTICE" DESTINATION ".")

  message(STATUS "Python package installation configured")
endif()
