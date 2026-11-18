// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// backends::webcrypto given a thread_pool's executor stops the build (ruling R73): WebCrypto's
// promise settles in the JavaScript event loop, to which only an io_context's run returns.

#include <webcpp/hash/async.hpp>

#include <webcpp/asio/thread_pool.hpp>

#include <boost/system/error_code.hpp>

#include <array>
#include <cstdint>

int main() {
    webcpp::asio::thread_pool pool(0);
    std::array<std::uint8_t, 32> output{};
    webcpp::hash::async_digest<webcpp::hash::digests::sha2_256, webcpp::hash::backends::webcrypto>(
        pool.get_executor(), output, {}, [](boost::system::error_code /*code*/) {});
    pool.join();
    return 0;
}
