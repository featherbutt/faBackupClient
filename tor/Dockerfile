FROM alpine:latest

EXPOSE 9050/tcp
EXPOSE 9050/udp
EXPOSE 9051/tcp
EXPOSE 9051/udp


RUN apk add --no-cache tor
CMD tor -f /etc/tor/torrc