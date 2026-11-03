// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)
#include <openssl/ssl.h>
#include <array>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/read.hpp>
#include <boost/asio/write.hpp>
#include <cstdio>
#include <cstdlib>
#include <string_view>
#include <webcpp/asio/io_context.hpp>
#include <webcpp/asio/ssl.hpp>
#ifdef WEBCPP_TEST_EMBEDDED_CA
#include <webcpp/asio/tls_client_context.hpp>
#endif

int main(int argc, char** argv) {
    if (argc != 6)
        return 2;
    const auto port = static_cast<unsigned short>(std::strtoul(argv[1], nullptr, 10));
    const char* hostname = argv[2];
    const bool reject = std::string_view(argv[4]) == "reject";
    const int version = std::string_view(argv[5]) == "1.2" ? TLS1_2_VERSION : TLS1_3_VERSION;
    webcpp::asio::io_context context;
#ifdef WEBCPP_TEST_EMBEDDED_CA
    auto prepared = std::string_view(argv[3]) == "@default"
                        ? webcpp::asio::make_tls_client_context()
                        : webcpp::asio::make_tls_client_context(argv[3]);
    if (!prepared) {
        std::fprintf(stderr, "CA preparation: %s\n", prepared.error().message().c_str());
        return 1;
    }
    auto tls = std::move(*prepared);
#else
    webcpp::asio::ssl::context tls(webcpp::asio::ssl::context::tls_client);
    boost::system::error_code error;
    tls.load_verify_file(argv[3], error);
    if (error) {
        std::fprintf(stderr, "CA load: %s\n", error.message().c_str());
        return 1;
    }
#endif
    if (!SSL_CTX_set_min_proto_version(tls.native_handle(), version) ||
        !SSL_CTX_set_max_proto_version(tls.native_handle(), version))
        return 1;
    webcpp::asio::ssl::stream<boost::asio::ip::tcp::socket> stream(context, tls);
#ifndef WEBCPP_TEST_EMBEDDED_CA
    stream.set_verify_mode(webcpp::asio::ssl::verify_peer);
#endif
    stream.set_verify_callback(webcpp::asio::ssl::host_name_verification(hostname));
    if (SSL_set_tlsext_host_name(stream.native_handle(), hostname) != 1)
        return 1;
    const std::array<char, 4> request{'p', 'i', 'n', 'g'};
    std::array<char, 4> response{};
    int result = 1;
    stream.next_layer().async_connect(
        {boost::asio::ip::address_v4::loopback(), port}, [&](boost::system::error_code ec) {
            if (ec) {
                std::fprintf(stderr, "connect: %s\n", ec.message().c_str());
                return;
            }
            stream.async_handshake(
                webcpp::asio::ssl::stream_base::client,
                [&](boost::system::error_code handshake_ec) {
                    if (handshake_ec) {
                        if (reject && SSL_get_verify_result(stream.native_handle()) != X509_V_OK) {
                            std::printf("PASS certificate rejection: %s\n",
                                        handshake_ec.message().c_str());
                            result = 0;
                        } else {
                            std::fprintf(stderr, "handshake: %s\n", handshake_ec.message().c_str());
                        }
                        return;
                    }
                    if (reject) {
                        std::fprintf(stderr, "FAIL: invalid identity was accepted\n");
                        return;
                    }
                    boost::asio::async_write(
                        stream, boost::asio::buffer(request),
                        [&](boost::system::error_code write_ec, std::size_t bytes) {
                            if (write_ec || bytes != request.size())
                                return;
                            boost::asio::async_read(
                                stream, boost::asio::buffer(response),
                                [&](boost::system::error_code read_ec, std::size_t count) {
                                    if (read_ec || count != response.size() ||
                                        std::string_view(response.data(), count) != "pong")
                                        return;
                                    stream.async_shutdown(
                                        [&](boost::system::error_code shutdown_ec) {
                                            if (shutdown_ec) {
                                                std::fprintf(stderr, "shutdown: %s\n",
                                                             shutdown_ec.message().c_str());
                                                return;
                                            }
                                            std::printf(
                                                "PASS %s: verified handshake, async ping/pong, "
                                                "clean shutdown\n",
                                                SSL_get_version(stream.native_handle()));
                                            result = 0;
                                        });
                                });
                        });
                });
        });
    context.run();  // lint-run: the probe owns the application event loop
    return result;
}
