// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

#include <webcpp/asio.hpp>
#include <webcpp/beast.hpp>

#include <boost/asio/buffer.hpp>
#include <boost/asio/post.hpp>
#include <chrono>
#include <cstdio>
#include <string_view>

namespace {

bool accepts_upstream_request(
    const boost::beast::http::request<boost::beast::http::string_body>& request) {
    return request.method() == boost::beast::http::verb::get && request.target() == "/probe";
}

}  // namespace

int main() {
    webcpp::asio::io_context context;
    webcpp::asio::steady_timer timer(context, std::chrono::seconds(10));
    int completions = 0;
    bool cancelled = false;
    timer.async_wait([&](boost::system::error_code error) {
        ++completions;
        cancelled = error == boost::asio::error::operation_aborted;
    });
    boost::asio::post(context, [&] {
        if (timer.cancel() != 1) {
            context.stop();
        }
    });
    context.run();  // lint-run: the consumer drives timer cancellation on the native context
    if (!cancelled || completions != 1) {
        return 1;
    }

    constexpr std::string_view wire = "GET /probe HTTP/1.1\r\nHost: example.invalid\r\n\r\n";
    webcpp::beast::http::request_parser<webcpp::beast::http::string_body> parser;
    boost::system::error_code error;
    const auto consumed = parser.put(boost::asio::buffer(wire), error);
    if (error || consumed != wire.size() || !parser.is_done() ||
        !accepts_upstream_request(parser.get())) {
        return 2;
    }
    std::puts("native consumer: Boost timer cancellation and HTTP interoperability passed");
}
