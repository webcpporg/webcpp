// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A user's program over /webcpp/crypto//openssl. Until Task 12 writes the backend's header it
// prints the define and calls OpenSSL_version_num() alone; Task 12 Step 3 gives it the seal.

#include <openssl/crypto.h>

#include <iostream>

int main() {
#if defined(WEBCPP_CRYPTO_HAS_OPENSSL)
    std::cout << "HAS_OPENSSL=" << WEBCPP_CRYPTO_HAS_OPENSSL << '\n';
#endif
    return OpenSSL_version_num() >= 0x30000000UL ? 0 : 1;
}
