// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

#include <webcpp/asio/ssl.hpp>
#include <webcpp/beast/core.hpp>
#include <webcpp/trystero/native/backend.hpp>

#include <openssl/crypto.h>
#include <boost/asio/io_context.hpp>

#include <cstdio>

int main() {
    if (OpenSSL_version_num() != OPENSSL_VERSION_NUMBER) {
        static_cast<void>(std::fprintf(stderr,
                                       "OpenSSL headers and implementation differ: %s / %s\n",
                                       OPENSSL_VERSION_TEXT, OpenSSL_version(OPENSSL_VERSION)));
        return 1;
    }
    boost::asio::io_context context;
    boost::asio::ssl::context tls(boost::asio::ssl::context::tls_client);
    const boost::beast::tcp_stream stream(context);
    const webcpp::trystero::native::backend backend(context.get_executor());
    rtc::PeerConnection peer(rtc::Configuration{});
    const auto channel = peer.createDataChannel("combined-provider");
    peer.close();
    if (!channel || tls.native_handle() == nullptr) {
        return 2;
    }
    std::puts("Asio, Beast and Trystero share the pinned OpenSSL provider");
}
