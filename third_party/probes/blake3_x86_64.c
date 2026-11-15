/* Copyright (c) 2026 WebCpp.org
 *
 * Distributed under the Boost Software License, Version 1.0. (See
 * accompanying file LICENSE_1_0.txt or copy at
 * https://www.boost.org/LICENSE_1_0.txt)
 *
 * third_party/Jamfile's probe of the configured compiler: it compiles only for
 * x86-64, read from the macros that webcpp::hash's blake3.hpp and
 * src/canary_blake3.c read, so that the build of /third_party//blake3, its
 * canary and the header agree on the instruction set. */
#if !(defined(__x86_64__) || defined(_M_X64))
#error "not x86-64"
#endif

int webcpp_blake3_probe_x86_64(void);

int webcpp_blake3_probe_x86_64(void) {
    return 0;
}
