/*!
 *  Copyright (c) 2023-2025 by Contributors
 * \file base.h
 */

#ifndef SPHERE_AAE_DLL
#ifdef _WIN32
#ifdef SPHERE_AAE_EXPORTS
#define SPHERE_AAE_DLL __declspec(dllexport)
#else
#define SPHERE_AAE_DLL __declspec(dllimport)
#endif
#else
#define SPHERE_AAE_DLL __attribute__((visibility("default")))
#endif
#endif
