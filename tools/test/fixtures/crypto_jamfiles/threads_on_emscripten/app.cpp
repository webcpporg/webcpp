// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A program for Emscripten built with -pthread (b2's threading=multi) has threads:
// WEBCPP_CRYPTO_HAS_THREADS is defined, and the heavy operations' async_ variants exist.
#include <webcpp/crypto/config.hpp>

#include <iostream>

#ifndef __EMSCRIPTEN_PTHREADS__
#error "the fixture's Jamfile builds this program with threading=multi, which is -pthread"
#endif
#ifndef WEBCPP_CRYPTO_HAS_THREADS
#error "WEBCPP_CRYPTO_HAS_THREADS is not defined with -pthread on Emscripten"
#endif

int main() {
    std::cout << "webcpp::crypto has threads\n";
}
