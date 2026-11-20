FROM docker.io/library/golang:1.24-alpine AS build
ENV CGO_ENABLED=0 GOMAXPROCS=2
RUN go install -p=2 github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z

FROM docker.io/library/alpine:3.23
COPY --from=build /go/bin/minio /usr/local/bin/minio
ENTRYPOINT ["/usr/local/bin/minio"]
