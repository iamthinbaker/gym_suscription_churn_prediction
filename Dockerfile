FROM odoo:19.0

USER root
COPY pyproject.toml /tmp/pkg/pyproject.toml
RUN apt-get update && apt-get install -y --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv --system-site-packages
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir setuptools \
    && pip install --no-cache-dir --no-build-isolation --ignore-installed '/tmp/pkg[scripts,dev]'
USER odoo
