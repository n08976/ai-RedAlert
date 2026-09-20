# ai-RedAlert toolkit image — Kali rolling + curated offensive toolset.
#
# We install a curated package set rather than the full kali-linux-headless metapackage:
# everything the lab needs (recon, exploitation, wifi, cracking) without the multi-GB
# tail of tools we never touch. Add more with `apt-get install` inside the container or
# by extending this list.
FROM kalilinux/kali-rolling

LABEL org.opencontainers.image.title="ai-RedAlert" \
      org.opencontainers.image.description="Portable offensive-security lab toolkit (authorized use only)" \
      org.opencontainers.image.source="https://github.com/n08976/ai-RedAlert" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    REDALERT_HOME=/opt/redalert \
    REDALERT_SCOPE=/opt/redalert/scope/scope.yaml \
    REDALERT_ENGAGEMENTS_DIR=/opt/redalert/engagements \
    PYTHONPATH=/opt/redalert/lib \
    PATH=/opt/redalert/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
      # base / shell
      bash sudo curl wget git ca-certificates iproute2 iputils-ping dnsutils \
      less vim tmux jq openssh-client \
      # python
      python3 python3-yaml python3-requests \
      # recon / enumeration
      nmap masscan gobuster nikto enum4linux-ng netexec smbclient \
      # exploitation
      metasploit-framework exploitdb \
      # credential attacks
      hydra medusa responder \
      # hash / password cracking
      hashcat john \
      # wifi
      aircrack-ng hcxtools hcxdumptool \
      # wordlists
      wordlists seclists \
    && rm -rf /var/lib/apt/lists/*

# SecLists / rockyou live under /usr/share; expose a stable path.
RUN [ -f /usr/share/wordlists/rockyou.txt.gz ] && gunzip -k /usr/share/wordlists/rockyou.txt.gz || true

WORKDIR /opt/redalert
COPY . /opt/redalert
RUN chmod +x /opt/redalert/bin/* /opt/redalert/docker/entrypoint.sh 2>/dev/null || true

ENTRYPOINT ["/opt/redalert/docker/entrypoint.sh"]
CMD ["bash"]
