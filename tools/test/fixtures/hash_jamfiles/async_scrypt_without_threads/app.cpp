// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// async_scrypt in a build without threads stops with spec 11.5's text, which names scrypt (ruling
// R70): natively, where every build has threads, the developer's WEBCPP_HASH_NO_THREADS removes
// them; on wasip2 and wasip3 there are none.

#include <webcpp/hash/async.hpp>
#include <webcpp/hash/scrypt.hpp>

#include <webcpp/asio/io_context.hpp>

#include <boost/system/error_code.hpp>

#include <array>
#include <cstdint>

int main() {
    webcpp::asio::io_context context;
    std::array<std::uint8_t, 64> output{};
    webcpp::hash::async_scrypt(
        context.get_executor(), output, {}, {},
        webcpp::hash::scrypt_parameters{.cost = 16, .block_size = 1, .parallelism = 1},
        [](boost::system::error_code /*code*/) {});
    return 0;
}
