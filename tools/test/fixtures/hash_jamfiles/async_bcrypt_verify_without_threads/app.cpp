// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// async_bcrypt_verify in a build without threads stops with spec 11.5's text, which names
// bcrypt_verify: natively, where every build has threads, the developer's WEBCPP_HASH_NO_THREADS
// removes them; on wasip2 and wasip3 there are none. No Botan is needed: the refusal precedes any
// engine.

#include <webcpp/hash/async.hpp>
#include <webcpp/hash/bcrypt.hpp>

#include <webcpp/asio/io_context.hpp>

#include <boost/system/error_code.hpp>

#include <array>
#include <cstdint>

int main() {
    webcpp::asio::io_context context;
    std::array<std::uint8_t, 16> const password{1};
    webcpp::hash::async_bcrypt_verify<webcpp::hash::backends::botan>(
        context.get_executor(), password, "$2b$04$......................",
        [](boost::system::error_code /*code*/, bool /*same*/) {});
    return 0;
}
