// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

#ifdef WEBCPP_TEST_BOOST_FIRST
#include <boost/asio.hpp>
#include <boost/beast.hpp>
#include <boost/cobalt.hpp>
#endif

#include <webcpp/asio.hpp>
#include <webcpp/beast.hpp>
#include <webcpp/beast/tcp_stream.hpp>
#include <webcpp/beast/websocket.hpp>
#include <webcpp/cobalt.hpp>

#include <boost/asio.hpp>
#include <boost/beast.hpp>
#include <boost/cobalt.hpp>
#include <type_traits>

static_assert(std::is_same_v<webcpp::asio::io_context, boost::asio::io_context>);
static_assert(std::is_same_v<webcpp::asio::steady_timer, boost::asio::steady_timer>);
static_assert(std::is_same_v<webcpp::asio::ip::tcp::socket, boost::asio::ip::tcp::socket>);
static_assert(std::is_same_v<webcpp::asio::ip::udp::socket, boost::asio::ip::udp::socket>);
static_assert(std::is_same_v<webcpp::asio::io_context::executor_type,
                             boost::asio::io_context::executor_type>);
static_assert(std::is_same_v<webcpp::cobalt::task<int>, boost::cobalt::task<int>>);
static_assert(std::is_same_v<webcpp::cobalt::promise<int>, boost::cobalt::promise<int>>);
static_assert(std::is_same_v<webcpp::cobalt::generator<int>, boost::cobalt::generator<int>>);
static_assert(std::is_same_v<decltype(webcpp::cobalt::use_op), decltype(boost::cobalt::use_op)>);
static_assert(std::is_same_v<webcpp::beast::tcp_stream, boost::beast::tcp_stream>);
static_assert(std::is_same_v<webcpp::beast::http::request<webcpp::beast::http::string_body>,
                             boost::beast::http::request<boost::beast::http::string_body>>);
static_assert(std::is_same_v<webcpp::beast::websocket::stream<webcpp::beast::tcp_stream>,
                             boost::beast::websocket::stream<boost::beast::tcp_stream>>);

// This is a compile-only consumer. It must not accidentally link Cobalt's runner.
