// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// erase_secret writes the buffer it erases: a program that hands it a const string stops at the
// call, with a message that names the ranges it takes, and with that error alone.

#include <webcpp/secure/erase_secret.hpp>

#include <string>

namespace {

void forget(std::string const& password) {
    webcpp::secure::erase_secret(password);
}

}  // namespace

int main() {
    forget("correct horse battery staple");
    return 0;
}
