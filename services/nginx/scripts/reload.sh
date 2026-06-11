#!/bin/sh
set -e

/scripts/render_upstream.sh
nginx -t
nginx -s reload