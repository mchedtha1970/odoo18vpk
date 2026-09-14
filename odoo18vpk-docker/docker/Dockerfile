FROM odoo:18.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-thai-tlwg \
        fonts-noto-core \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-extra.txt /tmp/requirements-extra.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-extra.txt \
    && rm -f /tmp/requirements-extra.txt

USER odoo
