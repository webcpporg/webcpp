// Copyright (c) 2026 WebCpp.org
//
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// https://www.boost.org/LICENSE_1_0.txt)
#include <errno.h>
#include <openssl/core_names.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <stdio.h>
#include <string.h>

/* Linker wrapping observes the real libc entry point without replacing its
 * successful output. The failure mode is selected before OpenSSL starts. */
static unsigned entropy_calls;
static size_t entropy_bytes;
static int fail_entropy;
int __real_getentropy(void* buffer, size_t length);

int __wrap_getentropy(void* buffer, size_t length) {
    ++entropy_calls;
    entropy_bytes += length;
    if (fail_entropy) {
        errno = EIO;
        return -1;
    }
    return __real_getentropy(buffer, length);
}

static int failed(const char* step) {
    fprintf(stderr, "FAIL: %s\n", step);
    ERR_print_errors_fp(stderr);
    return 1;
}

int main(int argc, char** argv) {
    unsigned char public_random[32], private_random[32], public_key[128];
    unsigned char signature[256];
    size_t public_length = sizeof(public_key), signature_length = sizeof(signature);
    const unsigned char message[] = "WASIp3 locally built OpenSSL probe";
    fail_entropy = argc == 2 && strcmp(argv[1], "fail-entropy") == 0;
    if (!OPENSSL_init_crypto(OPENSSL_INIT_NO_LOAD_CONFIG, NULL))
        return failed("initialization");
    int random_ok = RAND_bytes(public_random, sizeof(public_random));
    int private_ok = RAND_priv_bytes(private_random, sizeof(private_random));
    EVP_PKEY* key = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "prime256v1");
    if (fail_entropy) {
        int passed = random_ok == 0 && private_ok == 0 && key == NULL && entropy_calls > 0;
        EVP_PKEY_free(key);
        if (!passed)
            return failed("entropy failure must prevent random output and key generation");
        printf("PASS fail-closed: RAND_bytes=0 RAND_priv_bytes=0 key=NULL entropy_calls=%u\n",
               entropy_calls);
        ERR_clear_error();
        return 0;
    }
    if (random_ok != 1 || private_ok != 1 || key == NULL || entropy_calls == 0)
        return failed("random generation and EC P-256 key generation");
    if (memcmp(public_random, private_random, sizeof(public_random)) == 0)
        return failed("public and private DRBG smoke check");
    unsigned calls_before_reseed = entropy_calls;
    if (EVP_RAND_reseed(RAND_get0_primary(NULL), 1, NULL, 0, NULL, 0) != 1 ||
        entropy_calls <= calls_before_reseed)
        return failed("explicit reseed must request new host randomness");
    if (EVP_PKEY_get_octet_string_param(key, OSSL_PKEY_PARAM_PUB_KEY, public_key,
                                        sizeof(public_key), &public_length) != 1)
        return failed("public key export");
    EVP_MD_CTX* sign = EVP_MD_CTX_new();
    EVP_MD_CTX* verify = EVP_MD_CTX_new();
    if (!sign || !verify || EVP_DigestSignInit(sign, NULL, EVP_sha256(), NULL, key) != 1 ||
        EVP_DigestSign(sign, signature, &signature_length, message, sizeof(message)) != 1 ||
        EVP_DigestVerifyInit(verify, NULL, EVP_sha256(), NULL, key) != 1 ||
        EVP_DigestVerify(verify, signature, signature_length, message, sizeof(message)) != 1)
        return failed("ECDSA signing and verification");
    signature[signature_length - 1] ^= 1;
    if (EVP_DigestVerify(verify, signature, signature_length, message, sizeof(message)) == 1)
        return failed("modified signature must be rejected");
    printf(
        "PASS random, reseed, EC P-256, ECDSA, tamper rejection: entropy_calls=%u "
        "entropy_bytes=%zu\n",
        entropy_calls, entropy_bytes);
    printf("PUBLIC_KEY=");
    for (size_t i = 0; i < public_length; ++i)
        printf("%02x", public_key[i]);
    printf("\n");
    EVP_MD_CTX_free(sign);
    EVP_MD_CTX_free(verify);
    EVP_PKEY_free(key);
    OPENSSL_cleanup();
    return 0;
}
