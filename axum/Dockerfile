FROM rust:1.86-bookworm AS builder

WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/axum-api /usr/local/bin/axum-api

EXPOSE 8001
CMD ["/usr/local/bin/axum-api"]
