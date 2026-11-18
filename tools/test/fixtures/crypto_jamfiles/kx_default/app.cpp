// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Makes libsodium's kx.exp client and server key pairs from their seeds on the default backend,
// computes each side's session keys from the other's public key, checks the client's transmit
// key against kx.exp's and the server's receive key, and prints the backend that ran. The seeds
// are libsodium's test's: a real program draws its key pair with generate().
#include <webcpp/crypto/curves/x25519/kx.hpp>
#include <webcpp/crypto/equal.hpp>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

int main() {
    namespace x25519 = webcpp::crypto::curves::x25519;
    std::array<std::uint8_t, 32> client_seed{};
    for (std::size_t i = 0; i < client_seed.size(); ++i) {
        client_seed[i] = static_cast<std::uint8_t>(i);
    }
    std::array<std::uint8_t, 32> server_seed = client_seed;
    server_seed[0] = 1;
    std::array<std::uint8_t, 32> const expected{
        0x62, 0xc8, 0xf4, 0xfa, 0x81, 0x80, 0x0a, 0xbd, 0x05, 0x77, 0xd9,
        0x99, 0x18, 0xd1, 0x29, 0xb6, 0x5d, 0xeb, 0x78, 0x9a, 0xf8, 0xc8,
        0x35, 0x1f, 0x39, 0x1f, 0xeb, 0x0c, 0xbf, 0x23, 0x86, 0x04,
    };
    auto const client = x25519::kx_keypair<>::make(client_seed);
    auto const server = x25519::kx_keypair<>::make(server_seed);
    bool ok = false;
    if (client && server) {
        auto const client_public = client->public_key();
        auto const server_public = server->public_key();
        if (client_public && server_public) {
            auto const client_keys = client->client_session_keys(*server_public);
            auto const server_keys = server->server_session_keys(*client_public);
            ok = client_keys && server_keys &&
                 webcpp::crypto::equal(client_keys->transmit.bytes(), expected) &&
                 webcpp::crypto::equal(server_keys->receive.bytes(), expected);
        }
    }
    auto const name = x25519::kx_keypair<>::backend_type::name;
    std::printf("kx %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}
