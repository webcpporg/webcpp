// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Initialises libsodium through the backend's header, which reads libsodium's canary: the program
// names another commit than the library was built for, so that a library built other than by
// webcpp's third_party/Jamfile fails to link.
#include <webcpp/crypto/backends/sodium.hpp>

int main() {
    return webcpp::crypto::detail::sodium_ready() ? 0 : 1;
}
