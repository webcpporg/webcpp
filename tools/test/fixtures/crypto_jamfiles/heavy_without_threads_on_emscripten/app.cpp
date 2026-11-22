// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// A heavy operation's async_ variant called in a build for Emscripten without -pthread.
#include <webcpp/crypto/detail/heavy.hpp>

#include <boost/system/result.hpp>

namespace {

boost::system::result<int> slow(int value) noexcept {
    return value + 1;
}

template <class Executor, class CompletionToken>
auto async_slow(Executor const& work, int value, CompletionToken&& token) {
    WEBCPP_CRYPTO_DETAIL_REQUIRE_THREADS("async_slow", "slow");
    return webcpp::crypto::detail::run_on_work(
        work, []() noexcept { return boost::system::result<void>(); },
        [value]() noexcept { return slow(value); }, token);
}

struct executor {};

struct token {};

}  // namespace

int main() {
    async_slow(executor{}, 41, token{});
    return *slow(0) == 1 ? 0 : 1;
}
