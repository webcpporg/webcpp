/* Copyright (c) 2026 WebCpp.org
 *
 * Distributed under the Boost Software License, Version 1.0. (See
 * accompanying file LICENSE_1_0.txt or copy at
 * https://www.boost.org/LICENSE_1_0.txt)
 *
 * BLAKE3's c/main.c sets g_cpu_features and reads get_cpu_features(), which
 * blake3_dispatch.c defines under BLAKE3_TESTING only on x86 (upstream runs its
 * C test on x86 alone). Off x86 the dispatcher reads no CPU features: it calls
 * NEON when built with BLAKE3_USE_NEON=1, else the portable code. So there the
 * two are defined here, as the dispatcher would: no feature to choose, one run
 * of each case. On x86 this file defines nothing and BLAKE3's own are linked. */
#include "blake3_impl.h"

#if !defined(IS_X86)
enum cpu_feature { UNDEFINED = 1 << 30 };

enum cpu_feature g_cpu_features = UNDEFINED;

enum cpu_feature get_cpu_features(void) {
    return (enum cpu_feature)0;
}
#else
/* ISO C wants a declaration in every translation unit. */
typedef int webcpp_blake3_c_suite_on_x86;
#endif
