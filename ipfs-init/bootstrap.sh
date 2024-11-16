#!/bin/sh
set -ex
ipfs bootstrap rm all
ipfs bootstrap add "/dns/$HOSTNAME/tcp/4001/ipfs/$PRIVATE_PEER_ID"