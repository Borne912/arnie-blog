#!/bin/sh
set -eu
case " ${RENEWED_DOMAINS:-} " in
  *" stats.stile.cc "*)
    /usr/sbin/nginx -t
    /bin/systemctl reload nginx
    ;;
esac
