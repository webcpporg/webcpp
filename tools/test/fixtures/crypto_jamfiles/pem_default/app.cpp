// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Reads RFC 8410's Ed25519 public key in PEM (section 10.1) on PEM's default backend, armours its
// DER again, checks that the text is the same, and prints the backend that ran.
#include <webcpp/crypto/pem.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <string_view>

int main() {
    namespace pem = webcpp::crypto::pem;
    constexpr std::string_view text =
        "-----BEGIN PUBLIC KEY-----\n"
        "MCowBQYDK2VwAyEAGb9ECWmEzf6FQbrBZ9w7lshQhqowtrbLDFw4rXAxZuE=\n"
        "-----END PUBLIC KEY-----\n";
    std::array<std::uint8_t, 44> der{};
    auto const read = pem::unarmour(pem::public_key_label, text, der);
    std::array<char, pem::armoured_size(pem::public_key_label.size(), der.size())> again{};
    auto const written = pem::armour(pem::public_key_label, der, again);
    bool const ok =
        read && *read == der.size() && written && std::string_view(again.data(), *written) == text;
    auto const name = pem::algorithm<>::backend_type::name;
    std::printf("pem %s backend=%.*s\n", ok ? "ok" : "FAILED", static_cast<int>(name.size()),
                name.data());
    return ok ? 0 : 1;
}
