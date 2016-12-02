#!/bin/bash
#Openssl Client used to find TLS fingerprint for Pandora (Pianobar)
#Chase Cromwell -2016
openssl s_client -connect tuner.pandora.com:443 < /dev/null 2> /dev/null | \
    openssl x509 -noout -fingerprint | tr -d ':' | cut -d'=' -f2
	