// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Ends with 3 through exit_status inside a timer's handler; main's later exit_status(0) does not
// replace it.

#include <webcpp/test/exit_status.hpp>

#include <boost/asio/io_context.hpp>
#include <boost/asio/steady_timer.hpp>

#include <chrono>

int main() {
    boost::asio::io_context io;
    boost::asio::steady_timer timer(io, std::chrono::milliseconds(10));
    timer.async_wait([](boost::system::error_code const&) { (void)webcpp::test::exit_status(3); });
    io.run();  // lint-run: the test's event loop
    return webcpp::test::exit_status(0);
}
