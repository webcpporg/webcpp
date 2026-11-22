// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Aggregates two fixed key pairs' public keys with BIP 327's MuSig2 on MuSig2's default backend,
// signs a message in its two rounds, verifies the aggregate as one BIP 340 signature, and prints
// the backend that ran. The secrets are fixed: a real program draws its own. The nonces are drawn
// inside nonce_gen.
#include <webcpp/crypto/curves/secp256k1.hpp>
#include <webcpp/crypto/curves/secp256k1/musig.hpp>
#include <webcpp/crypto/signing.hpp>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <utility>

namespace {

std::array<std::uint8_t, 32> repeated(std::uint8_t value) {
    std::array<std::uint8_t, 32> bytes{};
    bytes.fill(value);
    return bytes;
}

namespace secp256k1 = webcpp::crypto::curves::secp256k1;
namespace musig = webcpp::crypto::curves::secp256k1::musig;

bool sign_and_verify(secp256k1::keypair const& first, secp256k1::keypair const& second) {
    auto const first_encoding = first.public_key();
    auto const second_encoding = second.public_key();
    if (!first_encoding || !second_encoding) {
        return false;
    }
    auto const first_key = secp256k1::parse_public_key(*first_encoding);
    auto const second_key = secp256k1::parse_public_key(*second_encoding);
    if (!first_key || !second_key) {
        return false;
    }
    std::array<secp256k1::public_key, 2> keys{*first_key, *second_key};
    std::ranges::sort(keys);
    alignas(std::max_align_t) std::array<std::byte, musig::workspace_size(2)> space{};
    auto const aggregate = musig::key_aggregate(keys, space);
    if (!aggregate) {
        return false;
    }
    auto const message = repeated(0x5a);
    auto first_nonce = musig::nonce_gen(first, *aggregate, message);
    auto second_nonce = musig::nonce_gen(second, *aggregate, message);
    if (!first_nonce || !second_nonce) {
        return false;
    }
    std::array<musig::public_nonce, 2> const nonces{first_nonce->public_part,
                                                    second_nonce->public_part};
    auto const nonce_sum = musig::nonce_aggregate(nonces, space);
    if (!nonce_sum) {
        return false;
    }
    auto const session = musig::nonce_process(*nonce_sum, message, *aggregate);
    if (!session) {
        return false;
    }
    auto const first_part =
        musig::partial_sign(first, std::move(first_nonce->secret_part), *aggregate, *session);
    auto const second_part =
        musig::partial_sign(second, std::move(second_nonce->secret_part), *aggregate, *session);
    if (!first_part || !second_part) {
        return false;
    }
    std::array<musig::partial_signature, 2> const parts{*first_part, *second_part};
    auto const signature = musig::partial_signature_aggregate(*session, parts, space);
    return signature && webcpp::crypto::verify(webcpp::crypto::schnorr, *signature, message,
                                               aggregate->xonly_public_key());
}

}  // namespace

int main() {
    namespace crypto = webcpp::crypto;
    auto const first = secp256k1::keypair::make(repeated(0x11));
    auto const second = secp256k1::keypair::make(repeated(0x22));
    bool const ok = first && second && sign_and_verify(*first, *second);
    auto const name = crypto::default_backend_t<crypto::families::secp256k1_musig>::name;
    std::printf("musig %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}
