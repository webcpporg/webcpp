// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Pays a BIP 352 silent payments recipient (its scan and spend keys) from one fixed input on
// silent payments' default backend, scans the output with the recipient's scan key pair, checks
// that the payment is found as the output created, and prints the backend that ran. The secrets
// are fixed: a real program draws its own.
#include <webcpp/crypto/curves/secp256k1.hpp>
#include <webcpp/crypto/curves/secp256k1/silent_payments.hpp>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace {

std::array<std::uint8_t, 32> repeated(std::uint8_t value) {
    std::array<std::uint8_t, 32> bytes{};
    bytes.fill(value);
    return bytes;
}

namespace secp256k1 = webcpp::crypto::curves::secp256k1;
namespace silent_payments = webcpp::crypto::curves::secp256k1::silent_payments;

bool pay_and_scan(secp256k1::keypair const& scan_pair, secp256k1::keypair const& spend_pair,
                  secp256k1::keypair const& donor) {
    auto const scan_key = scan_pair.public_key();
    auto const spend_key = spend_pair.public_key();
    auto const donor_key = donor.public_key();
    if (!scan_key || !spend_key || !donor_key) {
        return false;
    }
    std::array<silent_payments::recipient, 1> const recipients{
        silent_payments::recipient{.scan_key = *scan_key, .spend_key = *spend_key}};
    std::array<std::uint8_t, silent_payments::outpoint_size> smallest_outpoint{};
    smallest_outpoint.fill(0x01);
    std::array<secp256k1::keypair const*, 1> const plain_inputs{&donor};
    std::array<std::array<std::uint8_t, 32>, 1> outputs{};
    alignas(std::max_align_t) std::array<std::byte, silent_payments::send_workspace_size(1, 0, 1)>
        send_space{};
    if (!silent_payments::create_outputs(recipients, smallest_outpoint, {}, plain_inputs, outputs,
                                         send_space)) {
        return false;
    }
    std::array<secp256k1::public_key, 1> const input_keys{*donor_key};
    alignas(std::max_align_t) std::array<std::byte, silent_payments::summary_workspace_size(0, 1)>
        summary_space{};
    auto const summary =
        silent_payments::make_prevouts_summary(smallest_outpoint, {}, input_keys, summary_space);
    if (!summary) {
        return false;
    }
    std::array<silent_payments::found_output, 1> found{};
    alignas(std::max_align_t) std::array<std::byte, silent_payments::scan_workspace_size(1)>
        scan_space{};
    auto const count =
        silent_payments::scan_outputs(scan_pair, *spend_key, *summary, outputs, found, scan_space);
    return count && *count == 1 && found[0].output_key == outputs[0];
}

}  // namespace

int main() {
    namespace crypto = webcpp::crypto;
    auto const scan_pair = secp256k1::keypair::from_secret(repeated(0x51));
    auto const spend_pair = secp256k1::keypair::from_secret(repeated(0x52));
    auto const donor = secp256k1::keypair::from_secret(repeated(0x53));
    bool const ok =
        scan_pair && spend_pair && donor && pay_and_scan(*scan_pair, *spend_pair, *donor);
    auto const name = crypto::default_backend_t<crypto::families::secp256k1_silent_payments>::name;
    std::printf("silent payments %s backend=%.*s\n", ok ? "ok" : "FAILED",
                static_cast<int>(name.size()), name.data());
    return ok ? 0 : 1;
}
