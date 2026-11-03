# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

# This external project hook leaves every upstream CMake input unchanged.
# Preserve /Zi databases outside the disposable build tree. Give each
# dependency a separate file so concurrent compilers cannot overwrite it.
function(webcpp_libdatachannel_symbols)
  foreach(library IN ITEMS datachannel juice usrsctp srtp2)
    set_target_properties(${library} PROPERTIES
      COMPILE_PDB_NAME "webcpp-${library}"
      COMPILE_PDB_OUTPUT_DIRECTORY "${WEBCPP_SYMBOL_DIRECTORY}")
  endforeach()
endfunction()
cmake_language(DEFER CALL webcpp_libdatachannel_symbols)
