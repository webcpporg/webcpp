// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)
#include <openssl/ssl.h>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <string_view>
#include <webcpp/asio/buffer.hpp>
#include <webcpp/asio/io_context.hpp>
#include <webcpp/asio/ip/address_v4.hpp>
#include <webcpp/asio/ip/tcp.hpp>
#include <webcpp/asio/read.hpp>
#include <webcpp/asio/ssl.hpp>
#include <webcpp/asio/write.hpp>
#ifdef WEBCPP_TEST_EMBEDDED_CA
#include <webcpp/asio/tls_client_context.hpp>
#endif

namespace {

using tls_stream = webcpp::asio::ssl::stream<webcpp::asio::ip::tcp::socket>;

bool verify_handshake(tls_stream& stream, boost::system::error_code error, bool reject,
                      int& result) {
    if (error) {
        if (reject && SSL_get_verify_result(stream.native_handle()) != X509_V_OK) {
            static_cast<void>(
                std::printf("PASS certificate rejection: %s\n", error.message().c_str()));
            result = 0;
        } else {
            static_cast<void>(std::fprintf(stderr, "handshake: %s\n", error.message().c_str()));
        }
        return false;
    }
    if (reject) {
        static_cast<void>(std::fprintf(stderr, "FAIL: invalid identity was accepted\n"));
        return false;
    }
    return true;
}

void exchange(tls_stream& stream, const std::array<char, 4>& request, std::array<char, 4>& response,
              int& result) {
    webcpp::asio::async_write(
        stream, webcpp::asio::buffer(request),
        [&](boost::system::error_code write_ec, std::size_t bytes) {
            if (write_ec || bytes != request.size()) {
                return;
            }
            webcpp::asio::async_read(
                stream, webcpp::asio::buffer(response),
                [&](boost::system::error_code read_ec, std::size_t count) {
                    if (read_ec || count != response.size() ||
                        std::string_view(response.data(), count) != "pong") {
                        return;
                    }
                    stream.async_shutdown([&](boost::system::error_code shutdown_ec) {
                        if (shutdown_ec) {
                            static_cast<void>(std::fprintf(stderr, "shutdown: %s\n",
                                                           shutdown_ec.message().c_str()));
                            return;
                        }
                        static_cast<void>(std::printf(
                            "PASS %s: verified handshake, async ping/pong, clean shutdown\n",
                            SSL_get_version(stream.native_handle())));
                        result = 0;
                    });
                });
        });
}

}  // namespace

int main(int argc, char* const* argv) {
    if (argc != 6) {
        return 2;
    }
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
        const auto message = prepared.error().message();
        static_cast<void>(std::fprintf(stderr, "CA preparation: %s\n", message.c_str()));
        return 1;
    }
    auto tls = std::move(*prepared);
#else
    webcpp::asio::ssl::context tls(webcpp::asio::ssl::context::tls_client);
    boost::system::error_code error;
    // Boost's deprecated return duplicates the error output checked below.
    // NOLINTNEXTLINE(bugprone-unused-return-value)
    static_cast<void>(tls.load_verify_file(argv[3], error));
    if (error) {
        static_cast<void>(std::fprintf(stderr, "CA load: %s\n", error.message().c_str()));
        return 1;
    }
#endif
    if (SSL_CTX_set_min_proto_version(tls.native_handle(), version) != 1 ||
        SSL_CTX_set_max_proto_version(tls.native_handle(), version) != 1) {
        return 1;
    }
    tls_stream stream(context, tls);
#ifndef WEBCPP_TEST_EMBEDDED_CA
    stream.set_verify_mode(webcpp::asio::ssl::verify_peer);
#endif
    stream.set_verify_callback(webcpp::asio::ssl::host_name_verification(hostname));
    if (SSL_set_tlsext_host_name(stream.native_handle(), hostname) != 1) {
        return 1;
    }
    const std::array<char, 4> request{'p', 'i', 'n', 'g'};
    std::array<char, 4> response{};
    int result = 1;
    stream.next_layer().async_connect(
        {webcpp::asio::ip::address_v4::loopback(), port}, [&](boost::system::error_code ec) {
            if (ec) {
                static_cast<void>(std::fprintf(stderr, "connect: %s\n", ec.message().c_str()));
                return;
            }
            stream.async_handshake(
                webcpp::asio::ssl::stream_base::client,
                [&](boost::system::error_code handshake_ec) {
                    if (!verify_handshake(stream, handshake_ec, reject, result)) {
                        return;
                    }
                    exchange(stream, request, response, result);
                });
        });
    context.run();  // lint-run: the probe owns the application event loop
    return result;
}
