// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// async_pbkdf2 on backends::webcrypto over an hmac WebCrypto lacks stops the build: WebCrypto's
// PBKDF2 is over SHA-1 and SHA-2 alone.

#include <webcpp/hash/async.hpp>
#include <webcpp/hash/hmac.hpp>

#include <webcpp/asio/io_context.hpp>

#include <boost/system/error_code.hpp>

#include <array>
#include <cstdint>

int main() {
    webcpp::asio::io_context context;
    std::array<std::uint8_t, 32> output{};
    webcpp::hash::async_pbkdf2<webcpp::hash::hmac_sha3_256, webcpp::hash::backends::webcrypto>(
        context.get_executor(), output, {}, {}, 1, [](boost::system::error_code /*code*/) {});
    return 0;
}
