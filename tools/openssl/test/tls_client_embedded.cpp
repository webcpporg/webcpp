// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Keep a distinct translation unit so a joint B2 build cannot reuse the
// filesystem-CA client's object for the client that accepts certificate bytes.
#define WEBCPP_TEST_EMBEDDED_CA
#include "tls_client.cpp"  // NOLINT(bugprone-suspicious-include)
