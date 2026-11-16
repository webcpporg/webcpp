// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Hashes "abc" with BLAKE3: the program reads the canary of /third_party//blake3, so that a
// library missing from the link, or built at another commit, fails to link with the
// canary's name (spec 5.4).

#include <webcpp/hash/blake3.hpp>

int main() {
    webcpp::hash::blake3 hasher;
    hasher.update("abc", 3);
    return hasher.result()[0] == 0x64 ? 0 : 1;
}
