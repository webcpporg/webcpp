// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// async_hkdf over an hmac WebCrypto has no HKDF over stops (spec 11.2): the cheap functions have
// an asynchronous form only for the algorithms the browser has.

#include <webcpp/hash/async.hpp>
#include <webcpp/hash/hmac.hpp>

#include <webcpp/asio/io_context.hpp>

#include <boost/system/error_code.hpp>

#include <array>
#include <cstdint>

int main() {
    webcpp::asio::io_context context;
    std::array<std::uint8_t, 32> output{};
    webcpp::hash::async_hkdf<webcpp::hash::hmac_sha3_256>(
        context.get_executor(), output, {}, {}, {}, [](boost::system::error_code /*code*/) {});
    return 0;
}
