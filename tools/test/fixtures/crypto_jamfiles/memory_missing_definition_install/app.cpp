// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Sets the memory option and installs OpenSSL's memory functions, but defines no
// webcpp::crypto::openssl_memory_resource(): the install odr-uses the adapter, which calls it,
// so the link fails naming the function (spec section 3.7).
#include <webcpp/crypto/backends/openssl.hpp>

int main() {
    return webcpp::crypto::backends::openssl::install_memory_functions() ? 0 : 1;
}
