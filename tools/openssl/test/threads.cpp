// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <mutex>
#include <thread>

int main() {
    std::array<std::thread, 4> workers;
    std::array<bool, 4> passed{};
    std::array<EVP_RAND_CTX*, 4> contexts{};
    std::mutex mutex;
    std::condition_variable ready;
    std::size_t arrived = 0;
    bool release = false;
    for (std::size_t i = 0; i < workers.size(); ++i) {
        workers[i] = std::thread([&, i] {
            contexts[i] = RAND_get0_private(nullptr);
            {
                std::unique_lock lock(mutex);
                ++arrived;
                ready.notify_all();
                ready.wait(lock, [&] { return release; });
            }
            if (contexts[i] == nullptr) {
                return;
            }
            std::array<unsigned char, 32> buffer{};
            for (int round = 0; round < 16; ++round) {
                if (RAND_priv_bytes(buffer.data(), buffer.size()) != 1) {
                    return;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            EVP_PKEY* key = EVP_PKEY_Q_keygen(nullptr, nullptr, "EC", "prime256v1");
            passed[i] = key != nullptr;
            EVP_PKEY_free(key);
        });
    }
    bool distinct = true;
    {
        std::unique_lock lock(mutex);
        ready.wait(lock, [&] { return arrived == workers.size(); });
        // All workers retain their contexts until comparison is complete.
        for (std::size_t i = 0; i < contexts.size(); ++i) {
            distinct = distinct && contexts[i] != nullptr;
            for (std::size_t j = 0; j < i; ++j) {
                distinct = distinct && contexts[i] != contexts[j];
            }
        }
        release = true;
    }
    ready.notify_all();
    for (auto& worker : workers) {
        worker.join();
    }
    if (!distinct) {
        return 1;
    }
    for (std::size_t i = 0; i < workers.size(); ++i) {
        if (!passed[i]) {
            return 1;
        }
    }
    std::puts("PASS 4 threads: distinct private DRBG contexts, 64 random requests, 4 EC keys");
}
