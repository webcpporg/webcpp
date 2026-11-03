// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)

// Compile the checked private source copy with the consumer's configuration.
#define BOOST_COBALT_SOURCE 1
#define BOOST_COBALT_IO_SOURCE 1
// This wrapper intentionally compiles the verified upstream implementation.
// NOLINTNEXTLINE(bugprone-suspicious-include)
#include <libs/cobalt/src/io/acceptor.cpp>
