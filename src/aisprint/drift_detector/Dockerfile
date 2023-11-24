FROM python:3.8

RUN mkdir /opt/drift_detector

WORKDIR /opt/drift_detector

# Copy requirements files
COPY requirements.* /opt/drift_detector/

# Instal system requirements first
RUN touch requirements.sys && \
    apt update && \
    xargs apt install -y --no-install-recommends < requirements.sys  && \
    apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && rm -rf ~/.cache/

# Update pip and install python requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application 
COPY . /opt/drift_detector/
RUN chmod +x /opt/drift_detector/script.sh

CMD /opt/drift_detector/script.sh

